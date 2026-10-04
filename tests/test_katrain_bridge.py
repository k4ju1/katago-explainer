"""KaTrain plugin bridge invariants, with source-shaped nodes and no GUI/GPU."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import Mock, patch

from explainer.board import vertex_to_point
from explainer.sgf import parse_sgf
from plugins.katrain.bridge import BackendUnavailable, BridgeError, KaTrainBridge, export_position


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
        return SimpleNamespace(game=game, board_gui=Mock())

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

    def test_analyze_posts_sgf_and_correct_actual_index_and_returns_on_worker(self):
        app, finished, observed = self.app(), threading.Event(), {}
        bridge = KaTrainBridge(app, {})
        result = {"selected_move": "D16", "branches": []}
        bridge._ensure_backend = Mock()
        bridge._request = Mock(side_effect=[{"game": {"id": "game"}}, {"job_id": "job"},
                                           {"status": "complete", "result": result}])
        def success(value):
            observed.update(result=value, thread=threading.current_thread())
            finished.set()
        self.assertTrue(bridge.analyze("actual", lambda *args: None, success, lambda error: finished.set()))
        self.assertTrue(finished.wait(2))
        imported_sgf = bridge._request.call_args_list[0].args[1]["sgf"]
        self.assertEqual(len(parse_sgf(imported_sgf).moves), 3)
        self.assertEqual(bridge._request.call_args_list[1].args[1], {"game_id": "game", "move_index": 2, "choice": "actual"})
        self.assertIsNot(observed["thread"], threading.current_thread())
        self.assertTrue(bridge.is_current(observed["result"]))

    def test_navigation_during_analysis_prevents_result_callback(self):
        app, finished, errors, results = self.app(), threading.Event(), [], []
        bridge = KaTrainBridge(app, {})
        bridge._ensure_backend = Mock()
        calls = [{"game": {"id": "game"}}, {"job_id": "job"}]
        def response(*args, **kwargs):
            if calls:
                return calls.pop(0)
            app.game.current_node = app.game.current_node.parent
            return {"status": "complete", "result": {}}
        bridge._request = response
        def failure(error):
            errors.append(error)
            finished.set()
        bridge.analyze("actual", lambda *args: None, results.append, failure)
        self.assertTrue(finished.wait(2))
        self.assertFalse(results)
        self.assertIn("position changed", errors[0]["en"])

    def test_other_app_port_is_not_started_or_killed(self):
        bridge = KaTrainBridge(self.app(), {})
        bridge._request = Mock(return_value={"application": "another-app", "api_version": 1})
        with patch("plugins.katrain.bridge.subprocess.Popen") as launch:
            with self.assertRaisesRegex(BridgeError, "another application"):
                bridge._ensure_backend()
            launch.assert_not_called()

    def test_backend_starts_hidden_with_project_config_and_validates_identity(self):
        with TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "explainer").mkdir()
            (project / "explainer" / "server.py").touch()
            python = project / "python.exe"
            python.touch()
            bridge = KaTrainBridge(self.app(), {"backend_url": "http://127.0.0.1:8799",
                                                "project_path": str(project), "python_path": str(python)})
            bridge._request = Mock(side_effect=[BackendUnavailable("offline"), {"application": "katago-explainer", "api_version": 1}])
            with patch("plugins.katrain.bridge.subprocess.Popen") as launch:
                bridge._ensure_backend()
                launch.assert_called_once()
                self.assertEqual(launch.call_args.args[0], [str(python), "-m", "explainer.server", "--port", "8799"])
                self.assertEqual(launch.call_args.kwargs["cwd"], str(project))
                self.assertIn("creationflags", launch.call_args.kwargs)
                self.assertTrue((project / "runs" / "plugin-backend.log").is_file())


if __name__ == "__main__":
    unittest.main()
