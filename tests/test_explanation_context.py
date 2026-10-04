"""Context must improve teaching without replacing search evidence."""
import unittest

from explainer.board import Board
from explainer.explanation import generate_explanation


class ExplanationContextTests(unittest.TestCase):
    def corner(self):
        board = Board(19)
        history = [('B', 'D4'), ('W', 'C3'), ('B', 'C4'), ('W', 'D3')]
        for player, move in history:
            board.play(player, move)
        return board, history

    def test_hane_reference_is_distinct_from_candidate_search(self):
        board, history = self.corner()
        analysis = {'selected': {'winrate': 45.0, 'score_lead': -1.0},
                    'alternative': {'move': 'F3', 'winrate': 48.0, 'score_lead': 0.0},
                    'ai_move': 'F3'}
        result = generate_explanation(board, 'B', 'E3', analysis, history=history)
        self.assertIn('E3 是「扳（二子头扳）', result['summary']['zh'])
        self.assertEqual(len(result['joseki']), 1)
        comparison = next(reason for reason in result['reasons'] if reason['id'] == 'candidate-comparison')
        self.assertIn('-3.000 个百分点', comparison['text']['zh'])
        self.assertEqual(analysis['selected']['winrate'], 45.0)
        self.assertNotIn('engine-choice', [reason['id'] for reason in result['reasons']])
        reference_reason = next(reason for reason in result['reasons'] if reason['level'] == 'reference')
        self.assertEqual(reference_reason['text'], result['joseki'][0]['move_explanation'])
        self.assertIn('E3', reference_reason['text']['zh'])

    def test_setup_does_not_assert_order_and_wrong_history_suppresses_name(self):
        board, _ = self.corner()
        result = generate_explanation(board, 'B', 'E3', {})
        self.assertIn('仅作棋形对应', result['joseki'][0]['relation']['zh'])
        wrong = [('B', 'C4'), ('W', 'D3'), ('B', 'D4'), ('W', 'C3')]
        result = generate_explanation(board, 'B', 'E3', {}, history=wrong)
        self.assertEqual(result['joseki'], [])

    def test_real_continuation_reply_gets_its_own_joseki_role(self):
        board, history = self.corner()
        original = list(history)
        result = generate_explanation(board, 'B', 'E3', {}, ['E3', 'E2'], history=history)
        self.assertIn('本手为「反扳」', result['continuation'][1]['zh'])
        reason = next(item for item in result['reasons'] if item['id'] == 'continuation-reference-2')
        self.assertEqual(reason['level'], 'reference')
        self.assertEqual(reason['ply'], 2)
        self.assertIn('E2', reason['text']['zh'])
        self.assertEqual(history, original)

    def test_immediate_atari_uses_chinese_term_without_sente_claim(self):
        board = Board(9, [('B', 'C2'), ('B', 'B3'), ('W', 'C3')], 'B')
        result = generate_explanation(board, 'B', 'D3', {})
        self.assertIn('形成打吃', result['summary']['zh'])
        terms = {item['id']: item['term']['zh'] for item in result['terms']}
        self.assertEqual(terms['atari'], '打吃')
        self.assertNotIn('sente', terms)
        self.assertNotIn('thickness', terms)

    def test_connection_and_knight_shape_have_different_teaching_terms(self):
        board = Board(9, [('B', 'C3'), ('B', 'E3')], 'B')
        result = generate_explanation(board, 'B', 'D3', {})
        self.assertIn('粘住', result['summary']['zh'])
        self.assertIn('connect', [term['id'] for term in result['terms']])
        board = Board(9, [('B', 'C3')], 'B')
        result = generate_explanation(board, 'B', 'E4', {})
        self.assertIn('小飞形', result['summary']['zh'])
        self.assertNotIn('connect', [term['id'] for term in result['terms']])
        self.assertEqual(result['joseki'], [])


if __name__ == '__main__':
    unittest.main()
