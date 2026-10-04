"""Tests for facts the explanation displays, rather than engine strength."""
import unittest

from explainer.board import Board, BoardError, vertex_to_point, point_to_vertex
from explainer.sgf import parse_sgf, SGFError
from explainer.explanation import generate_explanation


class BoardTests(unittest.TestCase):
    def test_gtp_coordinates_and_skipped_i(self):
        self.assertEqual(vertex_to_point("A1", 19), (0, 18))
        self.assertEqual(vertex_to_point("T19", 19), (18, 0))
        self.assertEqual(vertex_to_point("J9", 9), (8, 0))
        self.assertEqual(point_to_vertex((8, 0), 9), "J9")
        self.assertIsNone(vertex_to_point("pass", 13))
        for bad in ("I3", "T9", "A0", "Q20", "A-1"):
            with self.assertRaises(BoardError):
                vertex_to_point(bad, 9)

    def test_capture(self):
        board = Board(9, [["B", "B3"], ["B", "D3"], ["B", "C2"], ["W", "C3"]])
        facts = board.play("B", "C4")
        self.assertEqual(facts["captured"], ["C3"])
        self.assertIsNone(board.group_at("C3"))
        self.assertEqual(board.to_play, "W")

    def test_connection_and_liberties(self):
        board = Board(9, [["B", "B4"], ["B", "D4"]])
        self.assertEqual(len(board.groups()), 2)
        facts = board.play("B", "C4")
        self.assertEqual(facts["connectedGroups"], 2)
        self.assertEqual(facts["moveGroupLibertiesAfter"], 8)
        self.assertEqual(len(board.groups()), 1)

    def test_created_atari(self):
        board = Board(9, [["B", "B3"], ["B", "C2"], ["W", "C3"]])
        self.assertEqual(board.group_at("C3")["libertyCount"], 2)
        facts = board.play("B", "D3")
        self.assertEqual(facts["createdAtariGroups"], [["C3"]])
        self.assertEqual(board.group_at("C3")["liberties"], ["C4"])

    def test_atari_rescue_does_not_claim_unconditional_safety(self):
        board = Board(9, [["W", "B3"], ["W", "D3"], ["W", "C2"], ["B", "C3"]])
        facts = board.play("B", "C4")
        self.assertEqual(facts["rescuedAtariGroups"], [["C3"]])
        self.assertEqual(facts["moveGroupLibertiesAfter"], 3)

    def test_illegal_moves_leave_position_and_turn_unchanged(self):
        board = Board(9, [["W", "B3"], ["W", "D3"], ["W", "C2"], ["W", "C4"]])
        before = board.snapshot()
        with self.assertRaises(BoardError):
            board.play("B", "C3")
        self.assertEqual(board.snapshot(), before)
        with self.assertRaises(BoardError):
            board.play("W", "A1")
        self.assertEqual(board.snapshot(), before)

    def test_ko_and_named_rule_difference_after_passes(self):
        setup = [["B", "B3"], ["B", "D3"], ["B", "C2"],
                 ["W", "C3"], ["W", "B4"], ["W", "D4"], ["W", "C5"]]
        for rule in ("chinese", "japanese", "korean", "aga"):
            board = Board(9, setup, rules=rule)
            board.play("B", "C4")
            with self.assertRaises(BoardError):
                board.play("W", "C3")
            board.play("W", "pass")
            board.play("B", "pass")
            if rule == "aga":
                with self.assertRaisesRegex(BoardError, "superko"):
                    board.play("W", "C3")
            else:
                self.assertEqual(board.play("W", "C3")["captured"], ["C4"])

    def test_copy_keeps_ko_history(self):
        setup = [["B", "B3"], ["B", "D3"], ["B", "C2"],
                 ["W", "C3"], ["W", "B4"], ["W", "D4"], ["W", "C5"]]
        board = Board(9, setup, rules="aga")
        board.play("B", "C4")
        board.play("W", "pass")
        copied = board.copy()
        copied.play("B", "pass")
        with self.assertRaisesRegex(BoardError, "superko"):
            copied.play("W", "C3")
        self.assertEqual(board.to_play, "B")


class SGFTests(unittest.TestCase):
    def test_sizes_setup_handicap_komi_and_mainline(self):
        for size in (9, 13, 19):
            record = parse_sgf(f"(;GM[1]FF[4]SZ[{size}]RU[Japanese]KM[0.5]HA[2]AB[aa][cc];W[dd];B[])")
            self.assertEqual(record.board_size, size)
            self.assertEqual(record.initial_player, "W")
            self.assertEqual(record.rules, "japanese")
            self.assertEqual(record.komi, .5)
            self.assertEqual(record.moves[1], ["B", "pass"])
            self.assertEqual(len(record.board_at(0).cells), 2)
            self.assertEqual(len(record.board_at(2).cells), 3)
            self.assertEqual(record.board_at(2).to_play, "W")

    def test_first_variation_and_escaped_comments(self):
        record = parse_sgf(r"(;SZ[9]RU[Chinese]KM[7.5]C[x\]y; literal](;B[aa];W[bb])(;B[cc]))")
        self.assertEqual(record.moves, [["B", "A9"], ["W", "B8"]])
        self.assertTrue(any("variations" in warning["en"] for warning in record.warnings))

    def test_compressed_setup_and_sgf_column_i_is_gtp_j(self):
        record = parse_sgf("(;SZ[9]RU[AGA]KM[0]AB[aa:bb]PL[W];W[ii])")
        self.assertEqual(len(record.initial_stones), 4)
        self.assertEqual(record.moves, [["W", "J1"]])

    def test_legacy_tt_is_pass_and_missing_rules_are_disclosed(self):
        record = parse_sgf("(;SZ[19];B[tt];W[])")
        self.assertEqual(record.moves, [["B", "pass"], ["W", "pass"]])
        self.assertEqual(len(record.warnings), 2)

    def test_unsupported_or_invalid_records(self):
        invalid = [
            "(;SZ[9]RU[NZ];B[aa])", "(;SZ[9]RU[Tromp-Taylor];B[aa])",
            "(;SZ[9];B[aa];AE[aa];W[bb])", "(;SZ[9];B[aa];PL[B];B[bb])",
            "(;SZ[9];B[aa];W[aa])", "(;SZ[9]AB[aa]AW[aa])",
            "(;SZ[9];B[aa]W[bb])", "(;SZ[9];W[aa])", "(;SZ[9:13])",
            "(;SZ[9]KM[nan])", "(;SZ[9])(;SZ[9])", "(;SZ[9];B[aa]",
        ]
        for sgf in invalid:
            with self.subTest(sgf=sgf), self.assertRaises(SGFError):
                parse_sgf(sgf)

    def test_1000_ply_limit(self):
        sgf = "(;SZ[9]RU[Chinese]KM[7.5]" + "".join(";B[]" if i % 2 == 0 else ";W[]" for i in range(1001)) + ")"
        with self.assertRaisesRegex(SGFError, "1000"):
            parse_sgf(sgf)


class ExplanationTests(unittest.TestCase):
    def test_capture_explanation_is_board_verified_and_bilingual(self):
        board = Board(9, [["B", "B3"], ["B", "D3"], ["B", "C2"], ["W", "C3"]])
        original = board.snapshot()
        result = generate_explanation(board, "B", "C4", {"ai_move": "C4"}, ["C4", "A1"])
        reason = next(item for item in result["reasons"] if item["id"] == "immediate-0")
        self.assertEqual(reason["level"], "board")
        self.assertIn("captures 1", reason["text"]["en"])
        self.assertIn("C3", reason["text"]["zh"])
        self.assertEqual(len(result["continuation"]), 2)
        self.assertEqual(board.snapshot(), original)
        self.assertFalse(any("territory gain" in item["text"]["en"] for item in result["reasons"]))

    def test_opening_development_is_tentative_not_literal_connection(self):
        board = Board(19)
        for player, move in [["B", "Q16"], ["W", "D4"], ["B", "Q4"], ["W", "D16"],
                             ["B", "R14"], ["W", "C6"], ["B", "F3"], ["W", "C14"]]:
            board.play(player, move)
        analysis = {"ai_move": "O3", "selected": {"move": "O3", "winrate": 36.4, "score_lead": -.8},
                    "alternative": {"move": "R6", "winrate": 35.6, "score_lead": -.9}}
        result = generate_explanation(board, "B", "O3", analysis, ["O3", "R6"])
        positional = next(item for item in result["reasons"] if item["id"] == "positional-reading")
        location = next(item for item in result["reasons"] if item["id"] == "location")
        self.assertEqual(positional["level"], "tentative")
        self.assertIn("lower side", positional["text"]["en"])
        self.assertIn("Q4", positional["text"]["en"])
        self.assertIn("line 3", location["text"]["en"])
        comparison = next(item for item in result["reasons"] if item["id"] == "candidate-comparison")
        self.assertIn("+0.8 percentage points", comparison["text"]["en"])
        self.assertIn("practically equal", comparison["text"]["en"])
        self.assertEqual(result["verdict"]["level"], "equal")
        self.assertFalse(any("joins" in item["text"]["en"] for item in result["reasons"]))

    def test_white_perspective_does_not_flip_black_ownership(self):
        board = Board(9, to_play="W")
        selected, alternate = [0.0] * 81, [0.0] * 81
        selected[0], alternate[0] = -.6, .2
        result = generate_explanation(board, "W", "A9", {
            "selected": {"move": "A9", "winrate": 55, "score_lead": 2, "ownership": selected},
            "alternative": {"move": "B9", "winrate": 53, "score_lead": 1, "ownership": alternate},
        })
        ownership = next(item for item in result["reasons"] if item["id"] == "ownership-clue")
        comparison = next(item for item in result["reasons"] if item["id"] == "candidate-comparison")
        # Black-oriented -0.6 versus +0.2 is 0.8 points toward White, in the corner.
        self.assertIn("upper-left corner", ownership["text"]["en"])
        self.assertIn("about 0.8 points of predicted ownership toward White", ownership["text"]["en"])
        self.assertIn("对白方多约 0.8 目", ownership["text"]["zh"])
        self.assertIn("White's", comparison["text"]["en"])
        self.assertIn("+2.0 percentage points", comparison["text"]["en"])

    def test_illegal_pv_stops_before_using_unverified_steps(self):
        board = Board(9)
        result = generate_explanation(board, "B", "A1", {}, ["A1", "A1", "B1"])
        self.assertEqual(len(result["continuation"]), 1)
        self.assertTrue(any("illegal move" in item["en"] for item in result["limitations"]))

    def test_later_tactical_effect_requires_actual_line(self):
        board = Board(9, [["B", "B3"], ["B", "C2"], ["W", "C3"]])
        result = generate_explanation(board, "B", "A1", {
            "branches": [{"id": "selected", "steps": [
                {"player": "B", "move": "A1"}, {"player": "W", "move": "J9"},
                {"player": "B", "move": "D3"}]}]})
        tactical = next(item for item in result["reasons"] if item["id"] == "continuation-fact-3")
        self.assertEqual(tactical["level"], "board")
        self.assertEqual(tactical["ply"], 3)
        self.assertIn("giving atari", tactical["text"]["en"])

    def test_service_branch_baseline_is_not_a_move(self):
        board = Board(9)
        result = generate_explanation(board, "B", "C3", {
            "branches": [
                {"id": "selected", "steps": [
                    {"ply": 0, "player": None, "move": None, "eval": {"winrate": 50}},
                    {"ply": 1, "player": "B", "move": "C3", "eval": {"winrate": 51.5}},
                    {"ply": 2, "player": "W", "move": "G7", "eval": {"winrate": 51.2}}]},
                {"id": "alternative", "steps": [
                    {"ply": 0, "player": None, "move": None},
                    {"ply": 1, "player": "B", "move": "G3"},
                    {"ply": 2, "player": "W", "move": "C7"}]}],
        })
        self.assertEqual(len(result["continuation"]), 2)
        self.assertIn("51.5%", result["continuation"][0]["en"])
        self.assertIn("G7", next(item for item in result["reasons"] if item["id"] == "anticipated-reply")["text"]["en"])
        self.assertIn("C7", next(item for item in result["reasons"] if item["id"] == "alternative-reply")["text"]["en"])
        self.assertFalse(any("illegal move" in item["en"] for item in result["limitations"]))

    def counterfactual_capture(self, selected_move, capture_line=None, ai_line=None):
        board = parse_sgf('(;SZ[9]KM[7.5]RU[Chinese]PL[B]AB[bc][cd][dc]AW[cc])').board_at(0)
        capture_line = capture_line or ["C8", "F4"]
        ai_line = ai_line or ["F4", "G5"]
        lines = {"C8": capture_line, "F4": ai_line}
        metrics = {"C8": {"move": "C8", "winrate": 30, "score_lead": -2},
                   "F4": {"move": "F4", "winrate": 40, "score_lead": 0}}
        alternative_move = "F4" if selected_move == "C8" else "C8"
        branches = [{"id": branch_id, "steps": [{"ply": 0, "player": None, "move": None}] +
                     [{"ply": index + 1, "player": "B" if index % 2 == 0 else "W", "move": vertex}
                      for index, vertex in enumerate(lines[first_move])]}
                    for branch_id, first_move in (("selected", selected_move), ("alternative", alternative_move))]
        return generate_explanation(board, "B", selected_move, {
            "ai_move": "F4", "selected": metrics[selected_move],
            "alternative": metrics[alternative_move], "branches": branches})

    def test_capture_vs_first_occupation_explains_actual_move_tradeoff(self):
        result = self.counterfactual_capture("C8")
        opportunity = next(item for item in result["reasons"] if item["id"] == "opportunity-order")
        self.assertEqual(opportunity["level"], "search")
        self.assertIn("choosing C8 lets White occupy F4 first at ply 2", opportunity["text"]["en"])
        self.assertIn("immediate capture at C8", opportunity["text"]["en"])
        self.assertIn("not a forced reply", opportunity["text"]["en"])
        self.assertIn("白方", opportunity["text"]["zh"])
        engine_judgment = next(item for item in result["reasons"] if item["id"] == "capture-versus-engine-choice")
        self.assertEqual(engine_judgment["level"], "search")
        self.assertIn("both win probability and expected score lead", engine_judgment["text"]["en"])
        urgency = next(item for item in result["reasons"] if item["id"] == "capture-urgency")
        self.assertEqual(urgency["level"], "board")
        self.assertIn("already in atari", urgency["text"]["en"])

    def test_counterfactual_is_symmetric_when_ai_move_is_selected(self):
        result = self.counterfactual_capture("F4")
        opportunity = next(item for item in result["reasons"] if item["id"] == "opportunity-order")
        self.assertIn("choosing C8 lets White occupy F4 first", opportunity["text"]["en"])
        self.assertIn("choosing F4 instead lets Black", opportunity["text"]["en"])
        self.assertFalse(any(item["id"] == "capture-versus-engine-choice" for item in result["reasons"]))

    def test_no_opportunity_claim_without_the_opponents_occupation(self):
        result = self.counterfactual_capture("C8", capture_line=["C8", "G5"], ai_line=["F4", "H5"])
        self.assertFalse(any(item["id"] == "opportunity-order" for item in result["reasons"]))

    def test_later_recapture_does_not_mean_opponent_occupied_first(self):
        line = ["C8", "G5", "F4", "F3", "pass", "E4", "pass", "G4", "pass", "F5", "pass", "F4"]
        result = self.counterfactual_capture("C8", capture_line=line, ai_line=["F4", "H5"])
        self.assertEqual(len(result["continuation"]), len(line))
        self.assertFalse(any(item["id"] == "opportunity-order" for item in result["reasons"]))


if __name__ == "__main__":
    unittest.main()
