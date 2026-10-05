"""Verdict tiers, shape naming, tenuki evidence, PV trust and the warm engine."""

import io
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from explainer.board import Board
from explainer.engine import AnalysisEngine, EnginePool, discover_settings
from explainer.explanation import generate_explanation
from explainer.server import prune_runs
from explainer.service import explain_move, trusted_pv
from explainer.sgf import parse_sgf


def board_after(moves, size=19):
    board = Board(size)
    for player, move in moves:
        board.play(player, move)
    return board


def analysis(selected, alternative, ai_move, **extra):
    return {'selected': selected, 'alternative': alternative, 'ai_move': ai_move, **extra}


class VerdictTests(unittest.TestCase):
    def explain(self, selected, alternative, ai_move, **extra):
        board = board_after([('B', 'Q16'), ('W', 'D4')])
        return generate_explanation(board, 'B', selected['move'], analysis(selected, alternative, ai_move, **extra))

    def test_noise_sized_gap_is_reported_as_equal_and_not_as_a_ranking(self):
        result = self.explain({'move': 'Q4', 'winrate': 40.10, 'score_lead': -0.63},
                              {'move': 'D16', 'winrate': 39.83, 'score_lead': -0.48}, 'D16')
        self.assertEqual(result['verdict']['level'], 'equal')
        self.assertTrue(result['summary']['zh'].startswith('Q4 与 AI 一选 D16 基本等价'))
        self.assertIn('+0.3 个百分点', result['summary']['zh'])
        self.assertNotIn('0.27', result['summary']['zh'])
        comparison = next(item for item in result['reasons'] if item['id'] == 'candidate-comparison')
        self.assertIn('基本等价', comparison['text']['zh'])

    def test_tiers_use_search_precision_before_display_rounding(self):
        near = self.explain({'move': 'Q4', 'winrate': 49.04, 'score_lead': -.49},
                            {'move': 'D16', 'winrate': 50.0, 'score_lead': 0.0}, 'D16')
        self.assertEqual(near['verdict']['level'], 'equal')
        comparison = next(item for item in near['reasons'] if item['id'] == 'candidate-comparison')
        self.assertIn('基本等价', comparison['text']['zh'])
        boundary = self.explain({'move': 'Q4', 'winrate': 49.0, 'score_lead': -.5},
                                {'move': 'D16', 'winrate': 50.0, 'score_lead': 0.0}, 'D16')
        self.assertEqual(boundary['verdict']['level'], 'slight')

    def test_loss_is_stated_first_with_the_expected_reply(self):
        branches = [{'id': 'selected', 'steps': [{'ply': 1, 'player': 'B', 'move': 'Q4'},
                                                 {'ply': 2, 'player': 'W', 'move': 'R6'}]}]
        result = self.explain({'move': 'Q4', 'winrate': 36.3, 'score_lead': -0.8},
                              {'move': 'D16', 'winrate': 43.4, 'score_lead': -0.3}, 'D16', branches=branches)
        self.assertEqual(result['verdict']['level'], 'inaccuracy')
        self.assertTrue(result['summary']['zh'].startswith(
            '小失误：按本次搜索，Q4 不如 AI 一选 D16（胜率 -7.1 个百分点、目差 -0.5 目）。'))
        self.assertIn('搜索预计白方的下一手是 R6', result['summary']['zh'])
        self.assertTrue(result['summary']['en'].startswith('Inaccuracy:'))

    def test_large_score_loss_is_a_blunder(self):
        result = self.explain({'move': 'Q4', 'winrate': 20.0, 'score_lead': -9.0},
                              {'move': 'D16', 'winrate': 45.0, 'score_lead': -1.0}, 'D16')
        self.assertEqual(result['verdict']['level'], 'blunder')

    def test_lopsided_game_is_graded_by_score_not_saturated_winrate(self):
        result = self.explain({'move': 'Q4', 'winrate': 99.0, 'score_lead': 28.0},
                              {'move': 'D16', 'winrate': 99.6, 'score_lead': 32.0}, 'D16',
                              base_eval={'winrate': 99.5})
        self.assertEqual(result['verdict']['level'], 'mistake')
        self.assertIn('按目差分档', result['summary']['zh'])
        close = self.explain({'move': 'Q4', 'winrate': 93.0, 'score_lead': 30.0},
                             {'move': 'D16', 'winrate': 99.0, 'score_lead': 30.2}, 'D16',
                             base_eval={'winrate': 99.0})
        self.assertEqual(close['verdict']['level'], 'equal')

    def test_first_choice_that_loses_the_research_is_called_unstable(self):
        result = self.explain({'move': 'D16', 'winrate': 39.0, 'score_lead': -1.0},
                              {'move': 'Q4', 'winrate': 42.0, 'score_lead': -0.2}, 'D16', actual_move='Q4')
        self.assertEqual(result['verdict']['level'], 'unstable')
        self.assertIn('实战的 Q4 的评估反而更高', result['summary']['zh'])

    def test_first_choice_states_its_advantage_over_the_game_move(self):
        result = self.explain({'move': 'D16', 'winrate': 45.0, 'score_lead': 0.5},
                              {'move': 'Q4', 'winrate': 40.0, 'score_lead': -1.5}, 'D16', actual_move='Q4')
        self.assertEqual(result['verdict']['level'], 'best')
        self.assertIn('与实战的 Q4 相比：胜率 +5.0 个百分点、目差 +2.0 目', result['summary']['zh'])

    def test_close_root_candidates_are_listed_as_one_tier(self):
        ranked = [{'move': 'D16', 'order': 0, 'visits': 116, 'winrate': 40.81, 'score_lead': -0.41},
                  {'move': 'Q4', 'order': 1, 'visits': 75, 'winrate': 40.84, 'score_lead': -0.45},
                  {'move': 'C16', 'order': 2, 'visits': 3, 'winrate': 40.80, 'score_lead': -0.40},
                  {'move': 'R4', 'order': 3, 'visits': 60, 'winrate': 37.00, 'score_lead': -1.40}]
        result = self.explain({'move': 'D16', 'winrate': 40.0, 'score_lead': -0.5},
                              {'move': 'Q4', 'winrate': 40.0, 'score_lead': -0.5}, 'D16', root_ranked=ranked)
        close = next(item for item in result['reasons'] if item['id'] == 'close-candidates')
        self.assertIn('Q4', close['text']['zh'])
        self.assertNotIn('C16', close['text']['zh'])  # three visits are not evidence
        self.assertNotIn('R4', close['text']['zh'])

    def test_without_search_numbers_there_is_no_verdict(self):
        result = generate_explanation(Board(9), 'B', 'E5', {})
        self.assertIsNone(result['verdict'])


class ShapeTests(unittest.TestCase):
    def shape(self, moves, player, move, size=19):
        result = generate_explanation(board_after(moves, size), player, move, {})
        reasons = [item for item in result['reasons'] if item['id'].startswith('move-shape')]
        return result, reasons, [term['id'] for term in result['terms']]

    def test_hane_is_one_label_never_also_attach_or_diagonal(self):
        moves = [('B', 'K4'), ('W', 'K3'), ('B', 'A1'), ('W', 'A19')]
        _, reasons, terms = self.shape(moves, 'B', 'L3')
        self.assertEqual(len(reasons), 1)
        self.assertIn('是扳', reasons[0]['text']['zh'])
        self.assertIn('L4 留有断点', reasons[0]['text']['zh'])
        self.assertIn('hane', terms)
        self.assertNotIn('attach', terms)
        self.assertNotIn('diagonal', terms)

    def test_cut_requires_separate_chains_and_a_partner_stone(self):
        moves = [('B', 'K10'), ('W', 'L10'), ('B', 'A1'), ('W', 'K11')]
        _, reasons, terms = self.shape(moves, 'B', 'L11')
        self.assertIn('是断', reasons[0]['text']['zh'])
        self.assertIn('cut', terms)

    def test_extension_push_kick_attachment_and_jump(self):
        cases = [
            ([('B', 'K10'), ('W', 'A1')], 'B', 'K11', '长出一子', 'extend'),
            ([('B', 'K10'), ('W', 'K12')], 'B', 'K11', '是顶', 'push'),
            ([('B', 'K4'), ('W', 'M3')], 'B', 'L3', '尖顶', 'kick'),
            ([('B', 'A1'), ('W', 'K10')], 'B', 'K11', '靠在对方 K10', 'attach'),
            ([('B', 'A1'), ('W', 'K4')], 'B', 'K3', '是托', 'attach_under'),
            ([('B', 'K10'), ('W', 'A1')], 'B', 'K12', '一间跳', 'jump'),
            ([('B', 'K10'), ('W', 'A1')], 'B', 'K13', '二间跳', 'two_space_jump'),
            ([('B', 'K10'), ('W', 'A1')], 'B', 'L13', '大飞形', 'large_knight'),
            ([('B', 'A1'), ('W', 'K4')], 'B', 'L5', '肩冲', 'shoulder_hit'),
        ]
        for moves, player, move, phrase, term in cases:
            with self.subTest(move=move, term=term):
                _, reasons, terms = self.shape(moves, player, move)
                self.assertEqual(len(reasons), 1)
                self.assertIn(phrase, reasons[0]['text']['zh'])
                self.assertIn(term, terms)

    def test_empty_corner_and_approach_are_named(self):
        _, reasons, terms = self.shape([], 'B', 'Q16')
        self.assertIn('右上角的星位', reasons[0]['text']['zh'])
        self.assertIn('star_point', terms)
        result = generate_explanation(board_after([('B', 'Q16')]), 'W', 'R14', {}, history=[('B', 'Q16')])
        self.assertIn('挂角', result['summary']['zh'])
        self.assertIn('小飞', result['summary']['zh'])


class ContinuationTests(unittest.TestCase):
    def test_tenuki_in_the_line_is_named_instead_of_measured(self):
        history = [('B', 'D4'), ('W', 'C3'), ('B', 'C4'), ('W', 'D3')]
        result = generate_explanation(board_after(history), 'B', 'E3', {},
                                      ['E3', 'E2', 'Q4', 'D16', 'F2'], history=history)
        lines = [item['zh'] for item in result['continuation']]
        self.assertIn('脱先：离开此前的局部，转向右下角', lines[2])
        self.assertIn('落在左上角，仍在别处', lines[3])
        self.assertNotIn('相距', ''.join(lines))
        self.assertNotIn('脱先', lines[4])  # F2 returns to the original area
        reason = next(item for item in result['reasons'] if item['id'] == 'tenuki-in-line')
        self.assertEqual(reason['ply'], 3)
        self.assertIn('第 2 手可以暂告一段落', reason['text']['zh'])
        self.assertIn('tenuki', [term['id'] for term in result['terms']])

    def test_opponent_ignoring_the_move_is_reported_at_ply_two(self):
        result = generate_explanation(board_after([('B', 'Q16'), ('W', 'D4')]), 'B', 'F3', {}, ['F3', 'Q4'])
        reason = next(item for item in result['reasons'] if item['id'] == 'tenuki-in-line')
        self.assertIn('没有在局部应这手', reason['text']['zh'])


class TenukiEvidenceTests(unittest.TestCase):
    def explain(self, tenuki):
        board = board_after([('B', 'Q16'), ('W', 'D4'), ('B', 'Q4'), ('W', 'D16')])
        return generate_explanation(board, 'B', 'F3', {
            'selected': {'move': 'F3', 'winrate': 48.0, 'score_lead': -0.2}, 'tenuki': tenuki})

    def test_move_value_and_shared_vital_point(self):
        result = self.explain({'pass': {'eval': {'winrate': 20.0, 'score_lead': -12.7}, 'reply': 'F3'}})
        reason = next(item for item in result['reasons'] if item['id'] == 'move-value')
        self.assertEqual(reason['level'], 'search')
        self.assertIn('约值 12.5 目', reason['text']['zh'])
        self.assertIn('正是 F3 这一点', reason['text']['zh'])
        self.assertIn('不是实战选项', reason['text']['zh'])
        self.assertTrue(any('假设停一手' in item['zh'] for item in result['limitations']))

    def test_reply_elsewhere_means_the_area_is_not_urgent(self):
        result = self.explain({'pass': {'eval': {'winrate': 40.0, 'score_lead': -3.0}, 'reply': 'R10'}})
        reason = next(item for item in result['reasons'] if item['id'] == 'move-value')
        self.assertIn('别处的 R10（右边）', reason['text']['zh'])

    def test_local_follow_up_suggests_sente_and_distant_one_gote(self):
        local = self.explain({'ignored': {'eval': {'winrate': 70.0, 'score_lead': 9.8}, 'followup': 'C6'}})
        reason = next(item for item in local['reasons'] if item['id'] == 'followup-if-ignored')
        self.assertIn('同一局部的 C6', reason['text']['zh'])
        self.assertIn('+10.0 目', reason['text']['zh'])
        self.assertIn('sente', [term['id'] for term in local['terms']])
        distant = self.explain({'ignored': {'eval': {'winrate': 60.0, 'score_lead': 6.0}, 'followup': 'R10'}})
        reason = next(item for item in distant['reasons'] if item['id'] == 'followup-if-ignored')
        self.assertIn('可以考虑脱先', reason['text']['zh'])
        terms = [term['id'] for term in distant['terms']]
        self.assertIn('gote', terms)
        self.assertNotIn('sente', terms)

    def test_local_follow_up_without_search_gain_does_not_claim_sente(self):
        result = self.explain({'ignored': {'eval': {'winrate': 47.0, 'score_lead': -.5}, 'followup': 'C6'}})
        reason = next(item for item in result['reasons'] if item['id'] == 'followup-if-ignored')
        self.assertIn('局部后续候选', reason['text']['zh'])
        self.assertIn('不能判断对方必须应一手', reason['text']['zh'])
        self.assertNotIn('sente', [term['id'] for term in result['terms']])

    def test_no_evidence_no_claim(self):
        ids = [item['id'] for item in self.explain({})['reasons']]
        self.assertNotIn('move-value', ids)
        self.assertNotIn('followup-if-ignored', ids)


class OwnershipTests(unittest.TestCase):
    def test_distant_free_moves_do_not_dominate_the_summary(self):
        board = board_after([('B', 'D4'), ('W', 'C6')])
        selected, alternative = [0.0] * 361, [0.0] * 361
        for index in range(19 * 4):          # far away: where each line spends a free move
            selected[index] = 0.9
        selected[15 * 19 + 2] = 0.8          # C4, beside the candidates
        selected[13 * 19 + 2], alternative[13 * 19 + 2] = 0.6, -0.6   # the White stone at C6
        result = generate_explanation(board, 'B', 'D6', {
            'selected': {'move': 'D6', 'winrate': 50, 'score_lead': 0, 'ownership': selected},
            'alternative': {'move': 'E3', 'winrate': 50, 'score_lead': 0, 'ownership': alternative}})
        summary = next(item for item in result['reasons'] if item['id'] == 'ownership-clue')
        self.assertIn('对黑方多约 2.0 目', summary['text']['zh'])
        self.assertNotIn('上边', summary['text']['zh'])
        group = next(item for item in result['reasons'] if item['id'] == 'ownership-group')
        self.assertIn('白方 C6', group['text']['zh'])
        self.assertIn('-0.60', group['text']['zh'])
        self.assertIn('+0.60', group['text']['zh'])


class TrustedPvTests(unittest.TestCase):
    def test_tail_with_few_visits_is_dropped(self):
        info = {'pv': ['E3', 'E2', 'Q4', 'D16', 'Q16', 'F3'], 'pvVisits': [514, 400, 120, 12, 9, 4]}
        self.assertEqual(trusted_pv(info), (['E3', 'E2', 'Q4'], True))

    def test_full_or_uncounted_pv_is_kept_up_to_the_limit(self):
        info = {'pv': list('ABCDEFGH'), 'pvVisits': [500] * 8}
        self.assertEqual(trusted_pv(info), (list('ABCDEF'), False))
        self.assertEqual(trusted_pv({'pv': ['E3', 'E2']}), (['E3', 'E2'], False))
        self.assertEqual(trusted_pv({'pv': ['E3'], 'pvVisits': [3]}), (['E3'], False))


class BatchProtocolTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.client = AnalysisEngine(None, self.directory.name)
        self.client.input_file, self.client.output_file = io.StringIO(), io.StringIO()
        self.client.process = SimpleNamespace(stdin=io.StringIO(), poll=lambda: None)
        self.client.deadline = time.monotonic() + 60
        self.game = SimpleNamespace(initial_stones=[], initial_player='B', rules='chinese', komi=7.5, board_size=19)

    def final(self, number):
        return {'id': f'position-{number}', 'isDuringSearch': False,
                'rootInfo': {'currentPlayer': 'B', 'winrate': .5, 'scoreLead': 0, 'visits': number},
                'moveInfos': [{'move': 'D4', 'order': 0, 'winrate': .5, 'scoreLead': 0, 'visits': number}]}

    def test_answers_return_in_request_order_whatever_order_they_arrive(self):
        for number in (3, 1, 2):
            self.client.responses.put(self.final(number))
        requests = [{'moves': [], 'visits': 100}, {'moves': [['B', 'D4']], 'visits': 100, 'ownership': False},
                    {'moves': [], 'visits': 100, 'forced_move': 'Q16', 'actor': 'B'}]
        answers = self.client.query_many(self.game, requests)
        self.assertEqual([answer['id'] for answer in answers], ['position-1', 'position-2', 'position-3'])
        sent = [line for line in self.client.process.stdin.getvalue().splitlines() if line]
        self.assertEqual(len(sent), 3)
        self.assertIn('"includeOwnership":false', sent[1])
        self.assertIn('"allowMoves"', sent[2])
        self.assertEqual(self.client.query_many(self.game, []), [])


class PooledEngine:
    started = 0

    def __init__(self, settings, output_dir):
        self.running, self.attached, self.closed = False, False, 0
        self.runs = [output_dir]

    def start(self):
        type(self).started += 1
        self.running = self.attached = True

    def alive(self):
        return self.running

    def attach(self, output_dir):
        self.attached = True
        self.runs.append(output_dir)

    def detach(self):
        self.attached = False

    def close(self):
        self.running = self.attached = False
        self.closed += 1


class EnginePoolTests(unittest.TestCase):
    def setUp(self):
        PooledEngine.started = 0
        self.pool = EnginePool(None, idle_seconds=60, factory=PooledEngine)
        self.addCleanup(self.pool.close)

    def test_process_is_reused_between_explanations(self):
        first = self.pool.acquire('run-1')
        self.pool.release(first)
        second = self.pool.acquire('run-2')
        self.assertIs(first, second)
        self.assertEqual(PooledEngine.started, 1)
        self.assertEqual(second.runs, ['run-1', 'run-2'])

    def test_failed_or_dead_engine_is_replaced(self):
        first = self.pool.acquire('run-1')
        self.pool.release(first, failed=True)
        self.assertEqual(first.closed, 1)
        second = self.pool.acquire('run-2')
        self.assertIsNot(first, second)
        second.running = False
        self.pool.release(second)
        third = self.pool.acquire('run-3')
        self.assertIsNot(second, third)
        self.assertEqual(PooledEngine.started, 3)

    def test_idle_engine_is_closed_but_a_busy_one_is_not(self):
        engine = self.pool.acquire('run-1')
        self.pool._expire(engine)
        self.assertTrue(engine.running)
        self.pool.release(engine)
        self.pool._expire(engine)
        self.assertFalse(engine.running)


class DiscoveryTests(unittest.TestCase):
    def layout(self, root, version='KaTrain-1.21.0'):
        base = root / version / 'KaTrain' / '_internal' / 'katrain'
        (base / 'KataGo').mkdir(parents=True)
        (base / 'models').mkdir()
        (base / 'KataGo' / 'katago.exe').write_text('')
        (base / 'KataGo' / 'analysis_config.cfg').write_text('')
        (root / 'project').mkdir()
        return base

    def test_files_are_found_without_machine_specific_names(self):
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            base = self.layout(root)
            (base / 'models' / 'kata1-b18c384nbt.bin.gz').write_text('')
            tuning = root / 'home' / '.katrain' / 'opencltuning'
            tuning.mkdir(parents=True)
            for name in ('tune13_gpuOther_x19_y19_c256_m128_h32_mv15.txt',
                         'tune13_gpuAnyCard_x19_y19_c384_m192_h32_mv15.txt',
                         'tune13_gpuAnyCard_x9_y9_c384_m192_h32_mv15.txt'):
                (tuning / name).write_text('')
            settings = discover_settings(root / 'project', environ={}, home=root / 'home')
            settings.validate()
            self.assertEqual(settings.engine, base / 'KataGo' / 'katago.exe')
            self.assertEqual(settings.model.name, 'kata1-b18c384nbt.bin.gz')
            self.assertEqual(settings.tuner.name, 'tune13_gpuAnyCard_x19_y19_c384_m192_h32_mv15.txt')

    def test_missing_tuning_file_is_optional_and_overrides_win(self):
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            base = self.layout(root)
            (base / 'models' / 'b10c384h6nbttflrs.bin.gz').write_text('')
            (base / 'models' / 'a-first-alphabetically.bin.gz').write_text('')
            other_model = root / 'other.bin.gz'
            other_model.write_text('')
            settings = discover_settings(root / 'project', environ={}, home=root / 'home')
            self.assertIsNone(settings.tuner)
            settings.validate()
            self.assertEqual(settings.model.name, 'b10c384h6nbttflrs.bin.gz')
            from_env = discover_settings(root / 'project', environ={'KATAGO_EXPLAINER_MODEL': str(other_model)},
                                         home=root / 'home')
            self.assertEqual(from_env.model, other_model)
            from_cli = discover_settings(root / 'project', {'model': base / 'models' / 'a-first-alphabetically.bin.gz'},
                                         environ={'KATAGO_EXPLAINER_MODEL': str(other_model)}, home=root / 'home')
            self.assertEqual(from_cli.model.name, 'a-first-alphabetically.bin.gz')
            (base / 'KataGo' / 'katago.exe').unlink()
            with self.assertRaises(ValueError):
                discover_settings(root / 'project', environ={}, home=root / 'home').validate()


class PruneRunsTests(unittest.TestCase):
    def test_only_old_generated_run_folders_are_removed(self):
        with TemporaryDirectory() as directory:
            runs = Path(directory)
            names = [f'20261004-1200{index:02d}-0123abcd' for index in range(5)]
            for name in names + ['mi-research', 'github-download-check']:
                (runs / name).mkdir()
                (runs / name / 'explanation.json').write_text('{}')
            (runs / 'plugin-backend.log').write_text('')
            removed = prune_runs(runs, keep=2)
            self.assertEqual(removed, names[:3])
            self.assertEqual(sorted(path.name for path in runs.iterdir()),
                             sorted(names[3:] + ['mi-research', 'github-download-check', 'plugin-backend.log']))
            self.assertEqual(prune_runs(runs / 'missing'), [])


class BatchingEngine:
    """Protocol double that records how positions are grouped."""
    batches = []

    def __init__(self, settings, output_dir):
        self.version, self.cleanup = 'Test engine', {'process_stopped': True}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def answer(self, game, request):
        board = Board(game.board_size, game.initial_stones, game.initial_player, game.rules)
        for player, move in request['moves']:
            board.play(player, move)
        forced = request.get('forced_move')
        occupied = {stone['move'] for stone in board.snapshot()['stones']}
        moves = [forced] if forced else [move for move in ('C3', 'G7') if move not in occupied]
        infos = [{'move': move, 'order': rank, 'winrate': .5 - rank * .1, 'scoreLead': 1.0 - rank,
                  'visits': request['visits'], 'pv': [move, 'G3', 'F3', 'pass'],
                  'pvVisits': [request['visits'], 90, 40, 2], 'ownership': [0.0] * 81}
                 for rank, move in enumerate(moves)]
        return {'rootInfo': {'currentPlayer': board.to_play, 'winrate': .5, 'scoreLead': 1.0,
                             'visits': request['visits']}, 'moveInfos': infos}

    def query(self, game, moves, visits, forced_move=None, actor=None):
        return self.query_many(game, [{'moves': moves, 'visits': visits,
                                       'forced_move': forced_move, 'actor': actor}])[0]

    def query_many(self, game, requests):
        type(self).batches.append(len(requests))
        return [self.answer(game, request) for request in requests]


class PipelineEvidenceTests(unittest.TestCase):
    def run_pipeline(self, sgf):
        BatchingEngine.batches = []
        game = parse_sgf(sgf)
        with TemporaryDirectory() as directory, patch('explainer.service.AnalysisEngine', BatchingEngine):
            return explain_move(game, 'game', 2, 'ai', SimpleNamespace(model=Path('model.bin.gz')),
                                directory, lambda *args: None)

    def test_positions_are_batched_and_tenuki_evidence_reaches_the_explanation(self):
        result = self.run_pipeline('(;SZ[9]KM[7.5]RU[Chinese];B[ee];W[cc])')
        # root; candidates plus the hypothetical pass; every line position plus the ignored-move test
        self.assertEqual(BatchingEngine.batches, [1, 3, 7])
        self.assertEqual(result['selected_move'], 'C3')
        for branch in result['branches']:   # the two-visit PV tail is not shown
            self.assertEqual([step['move'] for step in branch['steps'][1:]], [branch['move'], 'G3', 'F3'])
        self.assertEqual(set(result['tenuki']), {'pass', 'ignored'})
        ids = [item['id'] for item in result['explanation']['reasons']]
        self.assertIn('move-value', ids)
        self.assertIn('followup-if-ignored', ids)
        self.assertTrue(any('搜索真正走到的部分' in item['zh'] for item in result['explanation']['limitations']))
        self.assertEqual(result['budgets']['tenuki_visits'], 300)
        self.assertIsNotNone(result['explanation']['verdict'])

    def test_hypothetical_pass_is_skipped_next_to_a_real_pass(self):
        result = self.run_pipeline('(;SZ[9]KM[7.5]RU[Chinese];B[ee];W[])')
        self.assertEqual(result['tenuki'], {})
        self.assertEqual(BatchingEngine.batches[1], 2)


if __name__ == '__main__':
    unittest.main()
