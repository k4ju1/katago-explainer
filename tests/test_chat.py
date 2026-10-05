"""The language-model chat: request shapes, streaming, context and settings. No GUI, no network beyond localhost."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
from types import SimpleNamespace
import unittest

from plugins.katrain import chat_context as core
from plugins.katrain import llm


class Move:
    def __init__(self, player, vertex):
        self.player, self.vertex = player, vertex
        self.coords = (core.COLUMNS.index(vertex[0]), int(vertex[1:]) - 1)

    def gtp(self):
        return self.vertex


class Node:
    def __init__(self, parent=None, move=None):
        self.parent, self.moves = parent, [move] if move else []
        self.analysis_exists = False
        self.winrate = self.score = self.points_lost = None
        self.root_visits, self.candidate_moves = 0, []

    @property
    def nodes_from_root(self):
        nodes, node = [], self
        while node:
            nodes.append(node)
            node = node.parent
        return nodes[::-1]

    @property
    def next_player(self):
        played = sum(len(node.moves) for node in self.nodes_from_root)
        return "B" if played % 2 == 0 else "W"

    def get_property(self, _name, default=None):
        return default


def sample_game(analysed=True):
    root = Node()
    first = Node(root, Move("B", "Q16"))
    second = Node(first, Move("W", "D4"))
    if analysed:
        second.analysis_exists, second.winrate, second.score = True, 0.46, -0.8
        second.points_lost, second.root_visits = 1.2, 640
        second.candidate_moves = [
            {"move": "Q4", "winrate": 0.47, "scoreLead": -0.6, "visits": 400, "pointsLost": 0.0,
             "relativePointsLost": 0.0, "pv": ["Q4", "D16", "R14"]},
            {"move": "D16", "winrate": 0.45, "scoreLead": -1.1, "visits": 90, "pointsLost": 0.5,
             "relativePointsLost": 0.5, "pv": ["D16"]},
        ]
    return SimpleNamespace(root=root, current_node=second, board_size=(19, 19), komi=6.5, rules="japanese",
                           stones=[first.moves[0], second.moves[0]], prisoner_count={"B": 0, "W": 0})


class RequestTests(unittest.TestCase):
    history = [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "在"},
               {"role": "user", "content": "形势如何"}]

    def test_openai_compatible_request(self):
        url, headers, body = llm.build_request(
            {"protocol": "openai", "base_url": "https://api.example.com/v1/", "model": "m", "api_key": "sk-test"},
            "system text", self.history)
        self.assertEqual(url, "https://api.example.com/v1/chat/completions")
        self.assertEqual(headers["Authorization"], "Bearer sk-test")
        self.assertEqual(body["messages"][0], {"role": "system", "content": "system text"})
        self.assertEqual([m["role"] for m in body["messages"][1:]], ["user", "assistant", "user"])
        self.assertTrue(body["stream"])

    def test_claude_request_keeps_system_separate(self):
        url, headers, body = llm.build_request(
            {"protocol": "anthropic", "base_url": "https://api.anthropic.com", "model": "claude-sonnet-5-5",
             "api_key": "test-key"}, "system text", self.history)
        self.assertEqual(url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(headers["x-api-key"], "test-key")
        self.assertEqual(headers["anthropic-version"], llm.ANTHROPIC_VERSION)
        self.assertNotIn("Authorization", headers)
        self.assertEqual(body["system"], "system text")
        self.assertTrue(all(message["role"] != "system" for message in body["messages"]))
        self.assertGreater(body["max_tokens"], 0)

    def test_local_service_needs_no_key_but_claude_does(self):
        _, headers, _ = llm.build_request({"protocol": "openai", "base_url": "http://localhost:11434/v1", "model": "m"},
                                          "s", self.history)
        self.assertNotIn("Authorization", headers)
        with self.assertRaises(llm.LLMError):
            llm.build_request({"protocol": "anthropic", "base_url": "https://api.anthropic.com", "model": "m"},
                              "s", self.history)

    def test_incomplete_or_odd_settings_are_refused_with_a_message(self):
        for config in ({}, {"base_url": "https://x/v1"}, {"base_url": "ftp://x", "model": "m"}):
            with self.assertRaises(llm.LLMError):
                llm.build_request(config, "s", self.history)

    def test_stream_events_of_both_protocols(self):
        self.assertEqual(llm.parse_event("openai", '{"choices":[{"delta":{"content":"黑"}}]}'), "黑")
        self.assertEqual(llm.parse_event("openai", '{"choices":[{"delta":{"role":"assistant"}}]}'), "")
        self.assertEqual(llm.parse_event("openai", "[DONE]"), "")
        self.assertEqual(llm.parse_event("openai", "not json"), "")
        self.assertEqual(llm.parse_event(
            "anthropic", '{"type":"content_block_delta","delta":{"type":"text_delta","text":"好"}}'), "好")
        self.assertEqual(llm.parse_event("anthropic", '{"type":"message_start","message":{}}'), "")
        with self.assertRaises(llm.LLMError):
            llm.parse_event("anthropic", '{"type":"error","error":{"type":"overloaded_error","message":"busy"}}')


class _Handler(BaseHTTPRequestHandler):
    seen = []
    mode = "stream"

    def log_message(self, *_args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        type(self).seen.append((self.path, dict(self.headers), body))
        if type(self).mode == "denied":
            payload = json.dumps({"error": {"message": "bad key"}}).encode()
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        claude = self.path.endswith("/messages")
        if type(self).mode == "whole":
            reply = ({"content": [{"type": "text", "text": "整段回复"}]} if claude
                     else {"choices": [{"message": {"content": "整段回复"}}]})
            payload = json.dumps(reply).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for piece in ("黑棋", "稍好", "。"):
            event = ({"type": "content_block_delta", "delta": {"type": "text_delta", "text": piece}} if claude
                     else {"choices": [{"delta": {"content": piece}}]})
            self.wfile.write(("data: " + json.dumps(event) + "\n\n").encode())
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")


class StreamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        _Handler.seen, _Handler.mode = [], "stream"
        # A proxy configured on the machine must not swallow requests to localhost.
        import os
        self._saved = {key: os.environ.pop(key) for key in list(os.environ) if key.lower().endswith("_proxy")}
        self.addCleanup(os.environ.update, self._saved)

    def config(self, protocol):
        base = self.base + ("/v1" if protocol == "openai" else "")
        return {"protocol": protocol, "base_url": base, "model": "m", "api_key": "test-key"}

    def test_both_protocols_stream_text(self):
        for protocol, path in (("openai", "/v1/chat/completions"), ("anthropic", "/v1/messages")):
            with self.subTest(protocol=protocol):
                pieces = list(llm.stream_chat(self.config(protocol), "s", [{"role": "user", "content": "问"}], timeout=5))
                self.assertEqual("".join(pieces), "黑棋稍好。")
                self.assertEqual(_Handler.seen[-1][0], path)

    def test_non_streaming_answer_is_accepted(self):
        _Handler.mode = "whole"
        for protocol in ("openai", "anthropic"):
            self.assertEqual(list(llm.stream_chat(self.config(protocol), "s", [{"role": "user", "content": "问"}], timeout=5)),
                             ["整段回复"])

    def test_http_error_becomes_a_readable_message(self):
        _Handler.mode = "denied"
        with self.assertRaisesRegex(llm.LLMError, "401.*bad key"):
            list(llm.stream_chat(self.config("openai"), "s", [{"role": "user", "content": "问"}], timeout=5))

    def test_unreachable_service_is_reported(self):
        config = {"protocol": "openai", "base_url": "http://127.0.0.1:9/v1", "model": "m"}
        with self.assertRaises(llm.LLMError):
            list(llm.stream_chat(config, "s", [{"role": "user", "content": "问"}], timeout=2))

    def test_session_records_the_exchange(self):
        session, done, deltas = core.ChatSession(), threading.Event(), []
        result = {}
        started = session.ask("形势如何", self.config("openai"), "system", deltas.append,
                              lambda reply: (result.setdefault("reply", reply), done.set()),
                              lambda message: (result.setdefault("error", message), done.set()))
        self.assertTrue(started)
        self.assertTrue(done.wait(5))
        self.assertEqual(result.get("reply"), "黑棋稍好。")
        self.assertEqual("".join(deltas), "黑棋稍好。")
        self.assertEqual([m["role"] for m in session.messages], ["user", "assistant"])
        self.assertFalse(session.busy)
        sent = _Handler.seen[-1][2]["messages"]
        self.assertEqual(sent[0]["content"], "system")
        self.assertEqual(sent[-1], {"role": "user", "content": "形势如何"})


class SessionTests(unittest.TestCase):
    def test_stopped_reply_calls_nothing_and_one_request_runs_at_a_time(self):
        release, entered = threading.Event(), threading.Event()

        def slow(_config, _system, _messages, should_stop):
            yield "一"
            entered.set()
            release.wait(5)
            if not should_stop():
                yield "二"

        session, calls = core.ChatSession(stream=slow), []
        self.assertTrue(session.ask("问", {}, "s", calls.append, lambda r: calls.append(("done", r)),
                                    lambda m: calls.append(("error", m))))
        self.assertTrue(entered.wait(5))
        self.assertFalse(session.ask("再问", {}, "s", calls.append, calls.append, calls.append))
        session.stop()
        release.set()
        threading.Event().wait(0.2)
        self.assertEqual(calls, ["一"])
        self.assertFalse(session.busy)
        self.assertEqual([m["role"] for m in session.messages], ["user"])

    def test_error_is_delivered_and_session_is_usable_again(self):
        def failing(*_args, **_kwargs):
            raise llm.LLMError("余额不足")
            yield  # pragma: no cover

        session, done, seen = core.ChatSession(stream=failing), threading.Event(), {}
        session.ask("问", {}, "s", lambda piece: None, lambda reply: done.set(),
                    lambda message: (seen.setdefault("error", message), done.set()))
        self.assertTrue(done.wait(5))
        self.assertEqual(seen["error"], "余额不足")
        self.assertFalse(session.busy)

    def test_history_is_trimmed_to_recent_turns_starting_with_the_user(self):
        messages = []
        for index in range(30):
            messages += [{"role": "user", "content": f"q{index}"}, {"role": "assistant", "content": f"a{index}"}]
        kept = core.trim_history(messages + [{"role": "user", "content": "last"}], turns=3)
        self.assertEqual(kept[0]["role"], "user")
        self.assertEqual(kept[-1]["content"], "last")
        self.assertLessEqual(len(kept), 6)


class ContextTests(unittest.TestCase):
    def test_game_context_carries_moves_board_and_engine_numbers(self):
        text = core.game_context(sample_game(), "zh")
        self.assertIn("1.BQ16 2.WD4", text)
        self.assertIn("轮到黑棋下", text)
        self.assertIn("黑胜率 46.0%", text)
        self.assertIn("白+0.8", text)
        self.assertIn("约亏 1.2 目", text)
        self.assertIn("1. Q4，胜率 47.0%", text)
        self.assertIn("后续 Q4 D16 R14", text)
        rows = {line.split()[0]: line for line in text.splitlines() if line[:2].strip().isdigit()}
        self.assertEqual(rows["16"].split()[1:20][15], "X")   # Q16
        self.assertEqual(rows["4"].split()[1:20][3], "O")     # D4

    def test_candidate_winrate_is_shown_from_the_movers_side(self):
        game = sample_game()
        third = Node(game.current_node, Move("B", "Q4"))
        third.analysis_exists, third.winrate, third.score, third.root_visits = True, 0.47, -0.6, 300
        third.candidate_moves = [{"move": "D16", "winrate": 0.47, "scoreLead": -0.6, "visits": 200, "pv": ["D16"]}]
        game.current_node = third
        self.assertIn("1. D16，胜率 53.0%", core.game_context(game, "zh"))

    def test_unanalysed_position_says_so_instead_of_inventing_numbers(self):
        text = core.game_context(sample_game(analysed=False), "zh")
        self.assertIn("还没有分析完", text)
        self.assertNotIn("胜率 ", text)

    def test_english_context(self):
        text = core.game_context(sample_game(), "en")
        self.assertIn("Black to play", text)
        self.assertIn("Black win rate 46.0%", text)

    def test_explanation_context_uses_the_generated_result(self):
        result = {"player": "B", "move_index": 2, "selected_move": "D5",
                  "selected": {"winrate": 51.2, "score_lead": 0.4}, "alternative": {"move": "C6", "winrate": 51.0, "score_lead": 0.3},
                  "explanation": {"verdict": {"label": {"zh": "基本等价", "en": "About equal"}},
                                  "summary": {"zh": "D5 与 C6 基本等价。", "en": "D5 and C6 are about equal."},
                                  "reasons": [{"level": "board", "text": {"zh": "D5 与 D4 相连。", "en": "D5 connects to D4."}}]},
                  "branches": [{"id": "selected", "steps": [{"ply": 0}, {"ply": 1, "player": "B", "move": "D5"},
                                                             {"ply": 2, "player": "W", "move": "C6"}]}]}
        text = core.explanation_context(result, "zh")
        for expected in ("第 3 手 黑 D5", "结论：基本等价", "[棋盘事实] D5 与 D4 相连。", "对比手 C6", "BD5 WC6"):
            self.assertIn(expected, text)
        self.assertEqual(core.explanation_context(None), "")
        system = core.build_system("GAME", text, "zh")
        self.assertIn("围棋老师", system)
        self.assertLess(system.index("GAME"), system.index("结论：基本等价"))

    def test_markdown_becomes_label_markup_without_inline_style_changes(self):
        markup = core.to_markup("## 结论\n**要点：**\n- **Q16** 是 *好* 手 [x]\n`D4` 与 2*3*4")
        lines = markup.split("\n")
        self.assertTrue(lines[0].startswith("[b]") and "结论" in lines[0])
        self.assertTrue(lines[1].startswith("[b]") and "要点" in lines[1])
        self.assertEqual(lines[2], "• Q16 是 好 手 &bl;x&br;")
        self.assertEqual(lines[3], "D4 与 2*3*4")


class SettingsTests(unittest.TestCase):
    def test_round_trip_keeps_only_known_fields(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "chat.json"
            settings = dict(core.default_settings(), api_key="test-key", model="m", unknown="x")
            core.save_settings(settings, path)
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("unknown", stored)
            loaded = core.load_settings(path)
            self.assertEqual((loaded["api_key"], loaded["model"]), ("test-key", "m"))

    def test_settings_live_beside_the_running_configuration(self):
        with TemporaryDirectory() as directory:
            config = Path(directory) / "portable-config.json"
            self.assertEqual(core.settings_path(config), Path(directory).resolve() / "explainer_chat.json")
            self.assertEqual(core.settings_path(None, home=directory), Path(directory) / ".katrain" / "explainer_chat.json")

    def test_missing_or_broken_file_gives_defaults(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "chat.json"
            self.assertEqual(core.load_settings(path), core.default_settings())
            path.write_text("{not json", encoding="utf-8")
            self.assertEqual(core.load_settings(path), core.default_settings())
            path.write_text('{"protocol": "other"}', encoding="utf-8")
            self.assertEqual(core.load_settings(path)["protocol"], "openai")

    def test_configured_means_a_key_or_a_local_service(self):
        base = core.default_settings()
        self.assertFalse(core.is_configured(base))
        self.assertTrue(core.is_configured(dict(base, api_key="test-key")))
        self.assertTrue(core.is_configured(dict(base, base_url="http://localhost:11434/v1")))
        self.assertFalse(core.is_configured(dict(base, base_url="http://localhost.evil.example/v1")))
        self.assertFalse(core.is_configured(dict(base, api_key="k", model="")))

    def test_presets_are_well_formed(self):
        names = [preset[0] for preset in llm.PRESETS]
        self.assertEqual(len(names), len(set(names)))
        for _name, protocol, base_url, _model in llm.PRESETS:
            self.assertIn(protocol, (llm.OPENAI, llm.ANTHROPIC))
            self.assertTrue(base_url == "" or base_url.startswith(("http://", "https://")))


if __name__ == "__main__":
    unittest.main()
