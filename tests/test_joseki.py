"""Tests for joseki recognition claims, especially false move-order matches."""
import unittest

from explainer.board import Board, point_to_vertex, vertex_to_point
from explainer.joseki import find_joseki


TRADITIONAL = [("B", "D4"), ("W", "C3"), ("B", "C4"), ("W", "D3"),
               ("B", "E3"), ("W", "E2"), ("B", "F3")]
KNIGHT = [("B", "D4"), ("W", "C3"), ("B", "C4"), ("W", "D3"),
          ("B", "F3"), ("W", "E3")]
KICK = [("B", "D4"), ("W", "F3"), ("B", "E3"), ("W", "F4"),
        ("B", "D6"), ("W", "K3")]
KOMOKU = [("B", "C4"), ("W", "E3")]


def before_move(line):
    board = Board(to_play=line[0][0])
    for player, move in line[:-1]:
        board.play(player, move)
    return board


class JosekiTests(unittest.TestCase):
    def test_four_sourced_prefixes_and_professional_roles(self):
        cases = [(TRADITIONAL, "star-33-traditional", "长"),
                 (KNIGHT, "star-33-knight", "长"),
                 (KICK, "star-approach-kick", "拆三"),
                 (KOMOKU, "komoku-knight-approach", "小飞挂角")]
        for line, family, role in cases:
            with self.subTest(family=family):
                board = before_move(line)
                result = find_joseki(board, *line[-1], history=line[:-1])
                self.assertEqual([item["id"] for item in result], [family])
                entry = result[0]
                self.assertEqual(entry["move_role"]["zh"], role)
                self.assertTrue(entry["move_explanation"]["zh"])
                self.assertTrue(entry["move_explanation"]["en"])
                self.assertIn("顺序与棋形", entry["relation"]["zh"])
                self.assertEqual([(step["player"], step["move"])
                                  for step in entry["reference_line"]], line)
                self.assertEqual(sum(step["selected"] for step in entry["reference_line"]), 1)
                self.assertTrue(entry["reference_line"][-1]["selected"])
                self.assertTrue(entry["sources"][0]["url"].startswith("https://"))
                self.assertIn("前缀", entry["stage"]["zh"])
                self.assertTrue(all(note["zh"] and note["en"] for note in entry["notes"]))

    def test_reference_small_knight_and_three_space_extension_coordinates(self):
        result = find_joseki(before_move(KNIGHT[:5]), *KNIGHT[4], KNIGHT[:4])[0]
        self.assertEqual(result["move_role"]["zh"], "小飞")
        result = find_joseki(before_move(KICK), *KICK[-1], KICK[:-1])[0]
        self.assertEqual(result["reference_line"][-1]["move"], "K3")
        x1, _ = vertex_to_point("F3", 19)
        x2, _ = vertex_to_point("K3", 19)
        self.assertEqual(x2 - x1 - 1, 3)  # G3, H3, J3; GTP skips I.

    def test_hane_explains_two_stone_head_and_separates_reference_reply(self):
        line = TRADITIONAL[:5]
        entry = find_joseki(before_move(line), *line[-1], line[:-1])[0]
        text = entry["move_explanation"]
        for coordinate in ("C3", "D3", "D4", "E3", "E2"):
            self.assertIn(coordinate, text["zh"])
            self.assertIn(coordinate, text["en"])
        self.assertIn("二子头扳", text["zh"])
        self.assertIn("只是一个应法", text["zh"])
        self.assertIn("not a forecast", text["en"])
        board = before_move(line)
        self.assertEqual(board.group_at("C3")["stones"], ["C3", "D3"])
        self.assertIn("E3", board.group_at("C3")["liberties"])

    def test_each_selected_role_has_observable_explanation(self):
        cases = [(TRADITIONAL, 3, "直接接到", "connects directly"),
                 (TRADITIONAL, 4, "两子直接相连", "joining the stones"),
                 (TRADITIONAL, 6, "反扳", "counter-hane"),
                 (KNIGHT, 5, "并未直接连成", "not directly connected"),
                 (KNIGHT, 6, "紧邻对方", "touches the opposing"),
                 (KICK, 3, "占去它的一口气", "removes one of its liberties"),
                 (KICK, 4, "向第四线长出", "toward the fourth line"),
                 (KICK, 5, "空点 D5", "empty point D5"),
                 (KICK, 6, "留三个空点", "three empty points"),
                 (KOMOKU, 2, "对方小目 C4", "opposing 3-4 stone at C4")]
        for full_line, count, zh, en in cases:
            line = full_line[:count]
            with self.subTest(family=full_line, count=count):
                entry = find_joseki(before_move(line), *line[-1], line[:-1])[0]
                self.assertIn(zh, entry["move_explanation"]["zh"])
                self.assertIn(en, entry["move_explanation"]["en"])

    def test_rotated_kick_and_jump_explanations_use_actual_vertices(self):
        # Reflection to the upper-right corner: D4->Q16, E3->P17, D5->Q15.
        reflected = [(actor, point_to_vertex((18 - vertex_to_point(move, 19)[0],
                                             18 - vertex_to_point(move, 19)[1]), 19))
                     for actor, move in KICK]
        for count, required in [(3, ["P17", "Q16", "O17"]),
                                (5, ["Q14", "Q16", "Q15"])]:
            line = reflected[:count]
            entry = find_joseki(before_move(line), *line[-1], line[:-1])[0]
            for move in required:
                self.assertIn(move, entry["move_explanation"]["zh"])
                self.assertIn(move, entry["move_explanation"]["en"])
            self.assertNotIn("D5", entry["move_explanation"]["zh"])

    def test_kick_liberty_claim_is_demonstrable_and_not_atari_claim(self):
        line = KICK[:3]
        board = before_move(line)
        liberties_before = board.group_at("F3")["libertyCount"]
        entries = find_joseki(board, *line[-1], line[:-1])
        after = board.copy()
        after.play(*line[-1])
        self.assertEqual(liberties_before - after.group_at("F3")["libertyCount"], 1)
        self.assertGreater(after.group_at("F3")["libertyCount"], 1)
        self.assertNotIn("打吃", entries[0]["move_explanation"]["zh"])
        self.assertNotIn("atari", entries[0]["move_explanation"]["en"])

    def test_eight_symmetries_and_both_colors_have_exact_reference(self):
        for swap in (False, True):
            for flip_x in (False, True):
                for flip_y in (False, True):
                    for color_swap in (False, True):
                        transformed = []
                        for actor, move in TRADITIONAL:
                            x, y = vertex_to_point(move, 19)
                            if swap:
                                x, y = y, x
                            if flip_x:
                                x = 18 - x
                            if flip_y:
                                y = 18 - y
                            if color_swap:
                                actor = "W" if actor == "B" else "B"
                            transformed.append((actor, point_to_vertex((x, y), 19)))
                        with self.subTest(swap=swap, flip_x=flip_x, flip_y=flip_y, colors=color_swap):
                            entries = find_joseki(before_move(transformed), *transformed[-1], transformed[:-1])
                            self.assertEqual(len(entries), 1)
                            self.assertEqual(entries[0]["id"], "star-33-traditional")
                            self.assertEqual([(step["player"], step["move"])
                                              for step in entries[0]["reference_line"]], transformed)

    def test_shared_initial_invasion_has_only_two_named_branches(self):
        line = TRADITIONAL[:2]
        entries = find_joseki(before_move(line), *line[-1], line[:-1])
        self.assertEqual({entry["id"] for entry in entries},
                         {"star-33-traditional", "star-33-knight"})
        self.assertEqual(len(entries), 2)
        self.assertTrue(all("第 2/" in entry["stage"]["zh"] for entry in entries))
        self.assertTrue(all(entry["move_role"]["zh"] == "点三三" for entry in entries))
        self.assertTrue(all(any("尚未选择" in note["zh"] for note in entry["notes"])
                            for entry in entries))
        self.assertTrue(all(entry["reference_line"][1]["selected"] for entry in entries))
        self.assertTrue(all(not step["selected"] for entry in entries
                            for step in entry["reference_line"][2:]))
        self.assertEqual(entries[0]["move_explanation"], entries[1]["move_explanation"])
        self.assertNotIn("小飞", entries[0]["move_explanation"]["zh"])
        self.assertNotIn("扳", entries[0]["move_explanation"]["zh"])

    def test_seed_star_or_komoku_alone_is_not_a_joseki(self):
        self.assertEqual(find_joseki(Board(), "B", "D4", []), [])
        self.assertEqual(find_joseki(Board(), "B", "C4", []), [])

    def test_shape_only_without_history_and_missing_setup_seed(self):
        board = before_move(TRADITIONAL)
        entry = find_joseki(board, *TRADITIONAL[-1])[0]
        self.assertIn("仅作棋形", entry["relation"]["zh"])
        self.assertNotIn("顺序与棋形均吻合", entry["relation"]["zh"])
        setup = Board(setup=TRADITIONAL[:1], to_play="W")
        for actor, move in TRADITIONAL[1:-1]:
            setup.play(actor, move)
        entry = find_joseki(setup, *TRADITIONAL[-1], TRADITIONAL[1:-1])[0]
        self.assertIn("起始棋子未", entry["relation"]["zh"])
        self.assertIn("shape match only", entry["relation"]["en"])

    def test_complete_setup_diagram_with_empty_history_is_shape_only(self):
        board = Board(setup=KICK[:-1], to_play="W")
        entry = find_joseki(board, *KICK[-1], history=[])[0]
        self.assertIn("仅作棋形", entry["relation"]["zh"])
        self.assertIn("未在历史中完整记录", entry["relation"]["zh"])

    def test_supplied_permuted_history_suppresses_identical_shape(self):
        board = before_move(TRADITIONAL)
        wrong = list(TRADITIONAL[:-1])
        wrong[0], wrong[2] = wrong[2], wrong[0]
        self.assertEqual(find_joseki(board, *TRADITIONAL[-1], wrong), [])
        # Omitting a middle move is not a root-setup suffix.
        wrong = TRADITIONAL[:2] + TRADITIONAL[3:-1]
        self.assertEqual(find_joseki(board, *TRADITIONAL[-1], wrong), [])

    def test_captured_extra_historical_local_moves_are_not_erased_from_match(self):
        history = [("B", "A1"), ("W", "A2"), ("B", "T19"), ("W", "B1")]
        # A1 can be captured by A2/B1. Its earlier local fight remains relevant
        # even if a later current diagram resembles the catalogue.
        history += TRADITIONAL[:-1]
        replayed = Board()
        for actor, move in history:
            replayed.play(actor, move)
        self.assertIsNone(replayed.group_at("A1"))
        # Remove the surviving foreign stones only to make an adversarial
        # edited diagram. Retaining history must still suppress the match.
        board = Board(setup=TRADITIONAL[:-1], to_play="B")
        self.assertEqual(find_joseki(board, *TRADITIONAL[-1], history), [])

    def test_any_extra_current_local_stone_of_either_color_suppresses(self):
        for actor, move in [("B", "A1"), ("W", "H3"), ("B", "E4"), ("W", "H8")]:
            with self.subTest(actor=actor, move=move):
                board = Board(setup=TRADITIONAL[:-1] + [(actor, move)], to_play="B")
                self.assertEqual(find_joseki(board, *TRADITIONAL[-1], TRADITIONAL[:-1]), [])

    def test_elsewhere_moves_and_passes_do_not_change_local_order(self):
        line = [("B", "D4"), ("W", "Q16"), ("B", "pass"), ("W", "C3"),
                ("B", "C4"), ("W", "D3"), ("B", "E3"), ("W", "E2"), ("B", "F3")]
        board = before_move(line)
        entries = find_joseki(board, *line[-1], line[:-1])
        self.assertEqual(len(entries), 1)
        self.assertIn("顺序与棋形", entries[0]["relation"]["zh"])

    def test_move_dictionary_history_is_supported(self):
        line = [{"player": actor, "move": move} for actor, move in KNIGHT[:-1]]
        result = find_joseki(before_move(KNIGHT), *KNIGHT[-1], line)
        self.assertEqual(result[0]["id"], "star-33-knight")

    def test_illegal_moves_pass_other_sizes_and_bad_history_return_no_match(self):
        board = before_move(KNIGHT)
        snapshot = board.snapshot()
        for actor, move in [("B", "E3"), ("W", "D4"), ("W", "I3"),
                            ("W", "T20"), ("W", "pass"), ("X", "E3")]:
            self.assertEqual(find_joseki(board, actor, move), [])
        for history in ["not history", [["B"]], [{"player": "Z", "move": "D4"}],
                        [["B", "I4"]], [["B", "D4"]] * 1001]:
            self.assertEqual(find_joseki(board, *KNIGHT[-1], history), [])
        for size in (9, 13):
            smaller = Board(size, setup=[("B", "D4")], to_play="W")
            self.assertEqual(find_joseki(smaller, "W", "C3", [("B", "D4")]), [])
        self.assertEqual(board.snapshot(), snapshot)

    def test_result_mutation_does_not_change_future_catalogue_matches(self):
        board = before_move(KICK)
        first = find_joseki(board, *KICK[-1], KICK[:-1])[0]
        first["name"]["zh"] = "changed"
        first["reference_line"][0]["role"]["en"] = "changed"
        first["sources"][0]["url"] = "changed"
        second = find_joseki(board, *KICK[-1], KICK[:-1])[0]
        self.assertNotEqual(second["name"]["zh"], "changed")
        self.assertNotEqual(second["reference_line"][0]["role"]["en"], "changed")
        self.assertNotEqual(second["sources"][0]["url"], "changed")


if __name__ == "__main__":
    unittest.main()
