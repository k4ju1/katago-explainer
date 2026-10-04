"""Public recognition checks for sourced, specifically named corner patterns."""
import unittest

from explainer.board import Board, other, point_to_vertex, vertex_to_point
from explainer.joseki import find_joseki
from explainer.terms import get_terms


SHUSAKU_ID = "komoku-shusaku-kosumi"
RETREAT_ID = "komoku-high-approach-attach-retreat"
MI_ID = "star-33-mi-flying-dagger"
KICK_ID = "star-approach-kick"


def colored(vertices):
    return [("B" if index % 2 == 0 else "W", vertex)
            for index, vertex in enumerate(vertices.split())]


SHUSAKU = colored("C4 E3 D5")
RETREAT = colored("C4 E4 E3 F3 D3 F4 C6 K3")
MI = colored("D4 C3 D3 C4 C6 B6 B7 C5 D6 D5 E5 E4 E2 F4 F5 G5 G6")
KICK = colored("D4 F3 E3 F4 D6 K3")


def replay(line):
    board = Board(19, to_play=line[0][0] if line else "B")
    for player, move in line:
        board.play(player, move)
    return board


def selected_entries(line, history=None):
    before = replay(line[:-1])
    return find_joseki(before, *line[-1], line[:-1] if history is None else history)


def named_entry(line, expected_id):
    entries = selected_entries(line)
    return next(entry for entry in entries if entry["id"] == expected_id)


def transformed(line, rotation, reflected, color_swap):
    """Independent geometric oracle: rotate the public board coordinates."""
    result = []
    for player, vertex in line:
        x, y = vertex_to_point(vertex, 19)
        if reflected:
            x = 18 - x
        for _ in range(rotation):
            x, y = 18 - y, x
        result.append((other(player) if color_swap else player,
                       point_to_vertex((x, y), 19)))
    return result


class ClassicJosekiTests(unittest.TestCase):
    def test_shusaku_named_only_when_its_diagonal_response_is_played(self):
        opening = selected_entries(SHUSAKU[:2])
        self.assertNotIn(SHUSAKU_ID, {entry["id"] for entry in opening})
        entry = named_entry(SHUSAKU, SHUSAKU_ID)
        self.assertIn("秀策尖", entry["name"]["zh"])
        self.assertEqual(entry["move_role"]["zh"], "秀策尖")
        self.assertIn("顺序与棋形均吻合", entry["relation"]["zh"])
        self.assertTrue(any("不据此认定全盘" in note["zh"] for note in entry["notes"]))

    def test_generic_diagonal_cannot_be_named_shusaku_or_kick(self):
        for line in (colored("C4 Q16 D5"), colored("D4 F3 E5")):
            with self.subTest(line=line):
                names = {entry["id"] for entry in selected_entries(line)}
                self.assertNotIn(SHUSAKU_ID, names)
                self.assertNotIn(KICK_ID, names)

    def test_kick_named_only_after_actual_contact_response(self):
        self.assertNotIn(KICK_ID, {entry["id"] for entry in selected_entries(KICK[:2])})
        entry = named_entry(KICK[:3], KICK_ID)
        self.assertEqual(entry["move_role"]["zh"], "尖顶")
        self.assertIn("尖顶定式", entry["name"]["zh"])
        self.assertIn("紧贴", entry["move_explanation"]["zh"])

    def test_attach_hane_does_not_commit_to_retreat_branch(self):
        for count in (2, 3, 4):
            with self.subTest(count=count):
                self.assertNotIn(RETREAT_ID,
                                 {entry["id"] for entry in selected_entries(RETREAT[:count])})
        entry = named_entry(RETREAT[:5], RETREAT_ID)
        self.assertEqual(entry["move_role"]["zh"], "退")
        self.assertIn("托退定式", entry["name"]["zh"])
        self.assertTrue(any("尚未选择" in note["zh"] for note in entry["notes"]))

    def test_shared_flying_dagger_opening_is_not_prematurely_named(self):
        for count in (2, 5, 6, 13, 16):
            with self.subTest(count=count):
                entries = selected_entries(MI[:count])
                self.assertNotIn(MI_ID, {entry["id"] for entry in entries})
                self.assertFalse(any("芈氏飞刀" in entry["name"]["zh"] for entry in entries))
        entry = named_entry(MI, MI_ID)
        self.assertEqual(entry["move_role"]["zh"], "外扳")
        self.assertIn("外扳分支入口", entry["name"]["zh"])
        self.assertTrue(any("不自动判定征子有利" in note["zh"] for note in entry["notes"]))

    def test_new_classics_work_in_all_symmetries_and_both_colors(self):
        for expected_id, full_line in ((SHUSAKU_ID, SHUSAKU), (RETREAT_ID, RETREAT),
                                      (MI_ID, MI)):
            for rotation in range(4):
                for reflection in (False, True):
                    for color_swap in (False, True):
                        line = transformed(full_line, rotation, reflection, color_swap)
                        with self.subTest(pattern=expected_id, rotation=rotation,
                                          reflection=reflection, colors=color_swap):
                            entries = selected_entries(line)
                            self.assertEqual([entry["id"] for entry in entries], [expected_id])
                            entry = entries[0]
                            self.assertEqual([(step["player"], step["move"])
                                              for step in entry["reference_line"]], line)
                            self.assertEqual([step["ply"] for step in entry["reference_line"]
                                              if step["selected"]], [len(line)])
                            self.assertIn("顺序与棋形均吻合", entry["relation"]["zh"])
                            role_vertices = {
                                SHUSAKU_ID: (0, 1, 2),
                                RETREAT_ID: (3, 7),
                                MI_ID: (12, 14, 15, 16),
                            }[expected_id]
                            for language in ("zh", "en"):
                                for index in role_vertices:
                                    self.assertIn(line[index][1], entry["move_explanation"][language])
                                self.assertNotIn("{m", entry["move_explanation"][language])

    def test_retreat_geometry_does_not_claim_direct_corner_connection(self):
        before = replay(RETREAT[:4])
        entry = named_entry(RETREAT[:5], RETREAT_ID)
        after = before.copy()
        after.play(*RETREAT[4])
        self.assertEqual(set(after.group_at("D3")["stones"]), {"D3", "E3"})
        self.assertEqual(after.group_at("C4")["stones"], ["C4"])
        self.assertIn("直接接住托子", entry["move_explanation"]["zh"])
        self.assertIn("仍未直接连成一块", entry["move_explanation"]["zh"])
        self.assertIn("not yet directly connected", entry["move_explanation"]["en"])

    def test_solid_connection_really_joins_approach_and_hane(self):
        before = replay(RETREAT[:5])
        self.assertEqual(before.group_at("E4")["stones"], ["E4"])
        self.assertEqual(before.group_at("F3")["stones"], ["F3"])
        facts = before.play(*RETREAT[5])
        self.assertEqual(facts["connectedGroups"], 2)
        self.assertEqual(set(before.group_at("F4")["stones"]), {"E4", "F3", "F4"})
        entry = named_entry(RETREAT[:6], RETREAT_ID)
        for move in ("F4", "E4", "F3"):
            self.assertIn(move, entry["move_explanation"]["zh"])
        self.assertIn("直接连成一块", entry["move_explanation"]["zh"])

    def test_extension_gaps_remain_and_do_not_establish_life(self):
        after = replay(RETREAT)
        self.assertNotIn(vertex_to_point("C5", 19), after.cells)
        self.assertEqual(after.group_at("C6")["stones"], ["C6"])
        self.assertEqual(after.group_at("K3")["stones"], ["K3"])
        for empty in ("G3", "H3", "J3"):
            self.assertNotIn(vertex_to_point(empty, 19), after.cells)
        jump = named_entry(RETREAT[:7], RETREAT_ID)
        self.assertIn("不能仅凭", jump["move_explanation"]["zh"])
        self.assertIn("一个空点", jump["move_explanation"]["zh"])
        extension = named_entry(RETREAT, RETREAT_ID)
        self.assertIn("三个空点", extension["move_explanation"]["zh"])

    def test_local_extras_and_legally_reordered_history_suppress_classics(self):
        for expected_id, line in ((SHUSAKU_ID, SHUSAKU), (RETREAT_ID, RETREAT), (MI_ID, MI)):
            for color in ("B", "W"):
                with self.subTest(pattern=expected_id, extra=color):
                    before = Board(19, setup=line[:-1] + [(color, "A1")],
                                   to_play=line[-1][0])
                    self.assertNotIn(expected_id, {entry["id"] for entry in
                                      find_joseki(before, *line[-1], line[:-1])})
        for line in (RETREAT, MI):
            with self.subTest(reordered=line):
                wrong = list(line[:-1])
                wrong[0], wrong[2] = wrong[2], wrong[0]
                reordered = replay(wrong)
                before = replay(line[:-1])
                self.assertEqual(reordered.cells, before.cells)
                self.assertEqual(find_joseki(before, *line[-1], wrong), [])

    def test_new_classic_catalogue_applies_only_to_19_line_boards(self):
        for size in (9, 13):
            for expected_id, line in ((SHUSAKU_ID, SHUSAKU), (RETREAT_ID, RETREAT), (MI_ID, MI)):
                with self.subTest(size=size, pattern=expected_id):
                    before = Board(size, setup=line[:-1], to_play=line[-1][0])
                    self.assertEqual(find_joseki(before, *line[-1], line[:-1]), [])

    def test_transformed_role_prose_uses_actual_vertices(self):
        for count in (5, 6, 7, 8):
            line = transformed(RETREAT, 2, False, True)
            entry = named_entry(line[:count], RETREAT_ID)
            self.assertIn(line[count - 1][1], entry["move_explanation"]["zh"])
            self.assertIn(line[count - 1][1], entry["move_explanation"]["en"])
            self.assertNotIn(RETREAT[count - 1][1], entry["move_explanation"]["zh"])
        line = transformed(MI, 1, True, False)
        entry = named_entry(line, MI_ID)
        for index in (12, 14, 15, 16):
            for language in ("zh", "en"):
                self.assertIn(line[index][1], entry["move_explanation"][language])

    def test_classic_references_have_multiple_sources_and_defined_chinese_terms(self):
        for expected_id, line, required_term in ((SHUSAKU_ID, SHUSAKU, "秀策尖"),
                                               (RETREAT_ID, RETREAT, "托退"),
                                               (MI_ID, MI, "芈氏飞刀")):
            with self.subTest(pattern=expected_id):
                entry = named_entry(line, expected_id)
                urls = {source["url"] for source in entry["sources"]}
                self.assertGreaterEqual(len(urls), 2)
                self.assertTrue(all(url.startswith("https://") for url in urls))
                terms = get_terms(entry["term_ids"])
                self.assertEqual({term["id"] for term in terms}, set(entry["term_ids"]))
                self.assertTrue(any(required_term in term["term"]["zh"] for term in terms))
                self.assertTrue(all(term["definition"]["zh"] and term["definition"]["en"]
                                    for term in terms))


if __name__ == "__main__":
    unittest.main()
