"""Pipeline invariants with deterministic protocol doubles, without a GPU."""

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from explainer.board import Board, other
from explainer.service import explain_move
from explainer.sgf import parse_sgf


class FakeEngine:
    def __init__(self, settings, output_dir):
        self.version = 'Test engine'
        self.cleanup = {'process_stopped': True, 'reader_threads_stopped': True}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def query(self, game, moves, visits, forced_move=None, actor=None):
        board = Board(game.board_size, game.initial_stones, game.initial_player, game.rules)
        for player, move in moves:
            board.play(player, move)
        valid = []
        for vertex in ('A9', 'A1', 'E5', 'G5', 'H4', 'pass'):
            try:
                board.copy().play(board.to_play, vertex)
                valid.append(vertex)
            except ValueError:
                pass
        root_info = {'currentPlayer': board.to_play, 'winrate': .4 + len(moves) * .01,
                     'scoreLead': -2 + len(moves) * .1, 'visits': visits + 1}
        choices = [forced_move] if forced_move else valid[:2]
        infos = []
        for rank, move in enumerate(choices):
            replay = board.copy()
            replay.play(replay.to_play, move)
            pv = [move]
            for followup in ('pass', 'pass'):
                replay.play(replay.to_play, followup)
                pv.append(followup)
            infos.append({'move': move, 'order': rank, 'winrate': .42 + rank * .20,
                          'scoreLead': -1.8 - rank * .1, 'visits': visits,
                          'pv': pv, 'ownership': [0.0] * game.board_size ** 2})
        return {'rootInfo': root_info, 'moveInfos': infos}


class ExplanationPipelineTests(unittest.TestCase):
    def explain(self, sgf, index, choice='actual', custom=None):
        game = parse_sgf(sgf)
        with TemporaryDirectory() as directory, patch('explainer.service.AnalysisEngine', FakeEngine):
            return explain_move(game, 'game', index, choice,
                                SimpleNamespace(model=Path('test-model.bin.gz')), directory,
                                lambda *args: None, custom)

    def test_actual_capture_is_the_subject_even_if_the_ai_prefers_another_move(self):
        result = self.explain('(;SZ[9]KM[7.5]RU[Chinese]PL[B]AB[bc][cd][dc]AW[cc];B[cb])', 0)
        self.assertEqual(result['selected_move'], 'C8')
        self.assertEqual(result['actual_move'], 'C8')
        self.assertEqual(result['alternative']['move'], result['ai_move'])
        first = result['branches'][0]['steps'][1]
        self.assertEqual(first['facts']['captured'], ['C7'])
        self.assertIn('提掉', result['explanation']['summary']['zh'])
        self.assertEqual(result['branches'][0]['steps'][0]['ply'], 0)
        self.assertTrue(result['explanation']['continuation'])
        self.assertEqual(result['cleanup']['process_stopped'], True)

    def test_every_white_continuation_eval_keeps_white_perspective(self):
        result = self.explain('(;SZ[9]KM[6.5]RU[Japanese];B[dd];W[ff])', 1)
        self.assertEqual(result['player'], 'W')
        for branch in result['branches']:
            for step in branch['steps']:
                metric = step['eval']
                self.assertAlmostEqual(metric['winrate'] + metric['black_winrate'], 100)
                self.assertGreater(metric['score_lead'], 0)
        self.assertEqual([s['player'] for s in result['branches'][0]['steps'][1:]], ['W', 'B', 'W'])

    def test_occupied_custom_move_is_rejected_before_candidate_search(self):
        with self.assertRaises(ValueError):
            self.explain('(;SZ[9]KM[7.5]RU[Chinese];B[dd];W[ff])', 1, 'ai', 'D6')

    def test_ai_selection_uses_original_order_not_raw_metric_sort(self):
        result = self.explain('(;SZ[9]KM[7.5]RU[Chinese];B[dd])', 0, 'ai')
        self.assertEqual(result['selected_move'], result['ai_move'])
        self.assertEqual(result['selected']['original_order'], 0)
        self.assertEqual(result['branches'][0]['move'], result['selected_move'])


if __name__ == '__main__':
    unittest.main()
