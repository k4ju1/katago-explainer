"""KaTrain plugin bridge invariants, with source-shaped nodes and no GUI/GPU."""
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import Mock, patch

from explainer.board import vertex_to_point
from explainer.sgf import parse_sgf
from plugins.katrain.bridge import (BridgeError, EngineUnavailable, KaTrainBridge, KaTrainEngineClient,
                                    export_position)


class Move:
    def __init__(self, player, vertex, size=19):
        self.player, self.vertex, self.size = player, vertex, size

    def sgf(self, size):
        point = vertex_to_point(self.vertex, size[0])
        return "" if point is None else chr(97 + point[0]) + chr(97 + point[1])


class Node:
    def __init__(self, parent=None, move=None, properties=None):
        self.parent, self.moves = parent, [move] if move else []
        self.properties = properties or {}
        self.placements, self.clear_placements, self.children = [], [], []
        if parent:
            parent.children.append(self)

    @property
    def root(self):
        return self.parent.root if self.parent else self

    @property
    def nodes_from_root(self):
        return (self.parent.nodes_from_root if self.parent else []) + [self]

    @property
    def board_size(self):
        size = self.root.get_property("SZ", 19)
        return size, size

    @property
    def komi(self):
        return self.root.get_property("KM", 7.5)

    @property
    def initial_player(self):
        return self.root.get_property("PL", "B")

    def get_property(self, name, default=None):
        return self.properties.get(name, [default])[0]


def game_with_branch():
    root = Node(properties={"SZ": [19], "KM": [6.5], "RU": ["Japanese"], "PB": ["A ] \\ name"]})
    first = Node(root, Move("B", "Q16"))
    second = Node(first, Move("W", "D4"))
    sibling = Node(second, Move("B", "Q4"))
    selected = Node(second, Move("B", "D16"))
    return SimpleNamespace(root=root, current_node=selected, rules="japanese", _lock=threading.RLock()), sibling


class ExportTests(unittest.TestCase):
    def test_actual_exports_full_selected_ancestry_without_sibling_or_mutation(self):
        game, sibling = game_with_branch()
        original_children = list(sibling.parent.children)
        original_node = game.current_node
        context = export_position(game, "actual")
        record = parse_sgf(context.sgf)
        self.assertEqual(record.moves, [["B", "Q16"], ["W", "D4"], ["B", "D16"]])
        self.assertEqual(context.move_index, 2)
        self.assertIs(context.base_node, original_node.parent)
        self.assertEqual(record.rules, "japanese")
        self.assertEqual(record.komi, 6.5)
        self.assertEqual(record.metadata["PB"], "A ] \\ name")
        self.assertIs(game.current_node, original_node)
        self.assertEqual(sibling.parent.children, original_children)

    def test_ai_uses_current_position_and_actual_follows_past_annotation(self):
        game, _ = game_with_branch()
        played_node = game.current_node
        annotation = Node(played_node)
        game.current_node = annotation
        actual = export_position(game, "last")
        ai = export_position(game, "ai")
        self.assertEqual(actual.move_index, 2)
        self.assertIs(actual.base_node, played_node.parent)
        self.assertEqual(ai.move_index, 3)
        self.assertIs(ai.base_node, annotation)

    def test_setup_initial_player_pass_and_komi_preserved(self):
        root = Node(properties={"SZ": [9], "KM": [.5], "PL": ["W"]})
        root.placements = [Move("B", "C7", 9), Move("B", "G3", 9)]
        passed = Node(root, Move("W", "pass", 9))
        game = SimpleNamespace(root=root, current_node=passed, rules="aga")
        record = parse_sgf(export_position(game, "actual").sgf)
        self.assertEqual(record.initial_stones, [["B", "C7"], ["B", "G3"]])
        self.assertEqual(record.initial_player, "W")
        self.assertEqual(record.moves, [["W", "pass"]])
        self.assertEqual(record.rules, "aga")
        self.assertEqual(record.komi, .5)

    def test_root_has_no_actual_move_and_edited_midgame_is_rejected(self):
        game, _ = game_with_branch()
        game.current_node = game.root
        with self.assertRaisesRegex(BridgeError, "No previous move"):
            export_position(game, "actual")
        self.assertEqual(export_position(game, "ai").move_index, 0)
        changed = Node(game.root)
        changed.placements = [Move("B", "A1")]
        game.current_node = changed
        with self.assertRaisesRegex(BridgeError, "Mid-game setup"):
            export_position(game, "ai")

    def test_custom_suicide_rules_and_clear_placements_rejected(self):
        game, _ = game_with_branch()
        game.rules = {"suicide": True}
        with self.assertRaisesRegex(BridgeError, "rules are not supported"):
            export_position(game, "ai")
        game.rules = "chinese"
        game.current_node.clear_placements = [Move("B", "A1")]
        with self.assertRaisesRegex(BridgeError, "removed stones"):
            export_position(game, "ai")


class BridgeTests(unittest.TestCase):
    def app(self):
        game, _ = game_with_branch()
        return SimpleNamespace(game=game, board_gui=Mock(), engine=None,
                               config=lambda key, default=None: "C:/models/kata-model.bin.gz")

    def test_snapshot_preview_does_not_change_native_tree_or_board(self):
        app = self.app()
        bridge = KaTrainBridge(app, {})
        bridge._contexts["test"] = export_position(app.game, "actual")
        expected = {"size": 19, "stones": []}
        result = {"_katrain_bridge_token": "test", "branches": [{"id": "selected", "steps": [{"ply": 0, "board": expected}]}]}
        node = app.game.current_node
        self.assertTrue(bridge.is_current(result))
        self.assertEqual(bridge.show_step(result, "selected", 0), expected)
        bridge.clear_preview()
        self.assertIs(app.game.current_node, node)
        app.board_gui.set_animating_pv.assert_not_called()
        app.game.root.properties["KM"] = [7.5]
        self.assertFalse(bridge.is_current(result))
        with self.assertRaisesRegex(BridgeError, "position changed"):
            bridge.show_step(result, "selected", 0)

    def test_analyze_runs_the_pipeline_on_katrains_engine_without_a_server(self):
        app, finished, observed = self.app(), threading.Event(), {}
        app.engine = FakeKaTrainEngine()
        bridge = KaTrainBridge(app, {})

        def success(value):
            observed.update(result=value, thread=threading.current_thread())
            finished.set()

        def failure(error):
            observed.update(error=error)
            finished.set()

        with patch("urllib.request.urlopen") as network, patch("subprocess.Popen") as process:
            self.assertTrue(bridge.analyze("actual", lambda *args: None, success, failure))
            self.assertTrue(finished.wait(5))
            network.assert_not_called()
            process.assert_not_called()
        self.assertNotIn("error", observed)
        result = observed["result"]
        self.assertEqual(result["selected_move"], "D16")
        self.assertEqual(result["move_index"], 2)
        self.assertEqual(result["cleanup"]["method"], "katrain_engine")
        self.assertEqual(result["engine"]["model"], "kata-model.bin.gz")
        self.assertIsNotNone(result["explanation"]["verdict"])
        self.assertIsNot(observed["thread"], threading.current_thread())
        self.assertTrue(bridge.is_current(result))
        root = app.engine.sent[0]
        self.assertEqual(root["moves"], [["B", "Q16"], ["W", "D4"]])
        self.assertEqual(root["rules"], "japanese")
        self.assertEqual(root["komi"], 6.5)
        self.assertEqual(root["overrideSettings"]["reportAnalysisWinratesAs"], "BLACK")
        self.assertEqual(root["priority"], 7 + 1000)
        self.assertNotIn("id", root)  # KaTrain numbers its own queries
        forced = [query["allowMoves"][0]["moves"] for query in app.engine.sent if "allowMoves" in query]
        self.assertIn(["D16"], forced)

    def test_navigation_during_analysis_prevents_result_callback(self):
        app, finished, errors, results = self.app(), threading.Event(), [], []
        app.engine = FakeKaTrainEngine()
        original = app.engine.send_query

        def navigate_then_send(query, callback, error_callback, **kwargs):
            if len(app.engine.sent) == 0:
                app.game.current_node = app.game.current_node.parent
            original(query, callback, error_callback, **kwargs)
        app.engine.send_query = navigate_then_send
        bridge = KaTrainBridge(app, {})

        def failure(error):
            errors.append(error)
            finished.set()
        bridge.analyze("actual", lambda *args: None, results.append, failure)
        self.assertTrue(finished.wait(5))
        self.assertFalse(results)
        self.assertIn("position changed", errors[0]["en"])

    def test_missing_or_stopped_engine_is_reported_without_starting_anything(self):
        for engine in (None, FakeKaTrainEngine(alive=False)):
            with self.subTest(engine=engine):
                app, finished, errors = self.app(), threading.Event(), []
                app.engine = engine
                bridge = KaTrainBridge(app, {})

                def failure(error):
                    errors.append(error)
                    finished.set()
                with patch("subprocess.Popen") as process:
                    bridge.analyze("ai", lambda *args: None, lambda result: finished.set(), failure)
                    self.assertTrue(finished.wait(5))
                    process.assert_not_called()
                self.assertIn("engine", errors[0]["en"])
                # A failed run must not leave the bridge locked.
                self.assertFalse(bridge._busy)


class FakeKaTrainEngine:
    """KaTrain's engine surface: queued queries, answers on its own reader thread."""

    def __init__(self, alive=True, answer=True):
        self.alive, self.answer = alive, answer
        self.base_priority = 7
        self.override_settings = {"reportAnalysisWinratesAs": "BLACK"}
        self.thread_lock = threading.RLock()
        self.queries, self.sent, self.terminated = {}, [], []

    def check_alive(self):
        return self.alive

    def terminate_query(self, query_id):
        self.terminated.append(query_id)

    def send_query(self, query, callback, error_callback, next_move=None, node=None):
        self.sent.append(dict(query))
        query_id = f"QUERY:{len(self.sent)}"
        self.queries[query_id] = (callback, error_callback, 0, next_move, node)
        if not self.answer:
            return
        to_play = query["initialPlayer"]
        for _ in query["moves"]:
            to_play = "W" if to_play == "B" else "B"
        allowed = query.get("allowMoves")
        occupied = {move for _, move in query["moves"]}
        moves = allowed[0]["moves"] if allowed else [m for m in ("D16", "Q4", "C3") if m not in occupied][:2]
        infos = [{"move": move, "order": rank, "winrate": .5 - .01 * rank, "scoreLead": .5 - rank,
                  "visits": query["maxVisits"], "pv": [move], "pvVisits": [query["maxVisits"]],
                  "ownership": [0.0] * 361} for rank, move in enumerate(moves)]
        analysis = {"id": query_id, "rootInfo": {"currentPlayer": to_play, "winrate": .5, "scoreLead": .5,
                                                 "visits": query["maxVisits"]}, "moveInfos": infos}

        def deliver():
            callback(dict(analysis, isDuringSearch=True), True)   # partial results are ignored
            callback(analysis, False)
        threading.Thread(target=deliver, daemon=True).start()


class EngineClientTests(unittest.TestCase):
    game = SimpleNamespace(initial_stones=[], initial_player="B", rules="chinese", komi=7.5, board_size=19)

    def test_answers_keep_request_order_and_unowned_searches_are_untouched(self):
        engine = FakeKaTrainEngine()
        client = KaTrainEngineClient(SimpleNamespace(engine=engine))
        answers = client.query_many(self.game, [
            {"moves": [], "visits": 100}, {"moves": [["B", "Q16"]], "visits": 50, "ownership": False},
            {"moves": [], "visits": 70, "forced_move": "Q4", "actor": "B"}])
        self.assertEqual([answer["rootInfo"]["visits"] for answer in answers], [100, 50, 70])
        self.assertFalse(engine.sent[1]["includeOwnership"])
        self.assertEqual(engine.sent[2]["allowMoves"], [{"player": "B", "moves": ["Q4"], "untilDepth": 1}])
        self.assertEqual(engine.terminated, [])
        self.assertEqual(client.query_many(self.game, []), [])

    def test_timeout_stops_only_this_clients_searches(self):
        engine = FakeKaTrainEngine(answer=False)
        engine.queries["QUERY:other"] = (lambda *args: None, None, 0, None, None)
        client = KaTrainEngineClient(SimpleNamespace(engine=engine), total_seconds=.05)
        with self.assertRaisesRegex(TimeoutError, "KaTrain"):
            client.query_many(self.game, [{"moves": [], "visits": 100}, {"moves": [], "visits": 100}])
        self.assertEqual(sorted(engine.terminated), ["QUERY:1", "QUERY:2"])

    def test_engine_error_and_missing_engine_are_explicit(self):
        engine = FakeKaTrainEngine(answer=False)
        send = engine.send_query

        def fail(query, callback, error_callback, **kwargs):
            send(query, callback, error_callback, **kwargs)
            error_callback({"error": "Illegal move"})
        engine.send_query = fail
        with self.assertRaisesRegex(ValueError, "Illegal move"):
            KaTrainEngineClient(SimpleNamespace(engine=engine)).query(self.game, [], 100)
        with self.assertRaises(EngineUnavailable):
            KaTrainEngineClient(SimpleNamespace(engine=None)).query(self.game, [], 100)


if __name__ == "__main__":
    unittest.main()
