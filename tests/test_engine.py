"""Protocol and perspective checks without a KataGo process or GPU."""

import io
import json
from pathlib import Path
import queue
from tempfile import TemporaryDirectory
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from explainer.engine import AnalysisEngine, actor_metric


class FakeProcess:
    def __init__(self):
        self.stdin = io.StringIO()
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        self.returncode = None

    def poll(self):
        return self.returncode

    def wait(self, timeout):
        self.returncode = 0
        return self.returncode


class ActorMetricTests(unittest.TestCase):
    def test_black_values_remain_black_and_probabilities_become_percentages(self):
        result = actor_metric({'winrate': 0.25, 'scoreLead': 2.5, 'visits': 512}, 'B')
        self.assertEqual(result, {'winrate': 25.0, 'score_lead': 2.5,
                                  'black_winrate': 25.0, 'visits': 512})

    def test_white_values_complement_probability_and_reverse_signed_lead_once(self):
        result = actor_metric({'winrate': 0.25, 'scoreLead': 2.5, 'visits': 512}, 'W')
        self.assertEqual(result, {'winrate': 75.0, 'score_lead': -2.5,
                                  'black_winrate': 25.0, 'visits': 512})

    def test_negative_black_lead_is_positive_for_white(self):
        result = actor_metric({'winrate': 0.4, 'scoreLead': -3.25}, 'W')
        self.assertEqual(result['winrate'], 60.0)
        self.assertEqual(result['score_lead'], 3.25)
        self.assertEqual(result['visits'], 0)


class EngineProtocolTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.client = AnalysisEngine(None, self.directory.name)
        self.client.input_file = io.StringIO()
        self.client.output_file = io.StringIO()
        self.client.process = FakeProcess()
        self.client.deadline = time.monotonic() + 120
        self.game = SimpleNamespace(initial_stones=[['B', 'D4'], ['B', 'Q16']],
                                    initial_player='W', rules='chinese', komi=0.5,
                                    board_size=19)
        self.history = [['W', 'D16'], ['B', 'Q4'], ['W', 'pass']]

    def final(self, **overrides):
        result = {'id': 'position-1', 'isDuringSearch': False,
                  'moveInfos': [{'move': 'C3', 'order': 0, 'winrate': 0.4,
                                 'scoreLead': -1.2, 'visits': 512}]}
        result.update(overrides)
        return result

    def query(self, **kwargs):
        return self.client.query(self.game, self.history, 512, **kwargs)

    def test_unmatched_and_partial_results_do_not_replace_matching_final(self):
        self.client.responses.put({'id': 'another-job', 'error': 'unrelated'})
        self.client.responses.put(self.final(isDuringSearch=True))
        expected = self.final()
        self.client.responses.put(expected)
        self.assertEqual(self.query(), expected)

    def test_full_setup_history_and_only_first_move_restriction_are_preserved(self):
        self.client.responses.put(self.final())
        self.query(forced_move='C3', actor='B')
        payload = json.loads(self.client.process.stdin.getvalue())
        self.assertEqual(payload['initialStones'], self.game.initial_stones)
        self.assertEqual(payload['initialPlayer'], 'W')
        self.assertEqual(payload['moves'], self.history)
        self.assertEqual(payload['rules'], 'chinese')
        self.assertEqual(payload['komi'], 0.5)
        self.assertEqual(payload['maxVisits'], 512)
        self.assertEqual(payload['allowMoves'],
                         [{'player': 'B', 'moves': ['C3'], 'untilDepth': 1}])
        self.assertEqual(json.loads(self.client.input_file.getvalue()), payload)

    def test_unrestricted_root_does_not_send_candidate_restriction(self):
        self.client.responses.put(self.final())
        self.query()
        self.assertNotIn('allowMoves', json.loads(self.client.process.stdin.getvalue()))

    def test_warning_is_recorded_and_final_result_rejected_conservatively(self):
        warning = {'id': 'position-1', 'warning': 'Rule was converted', 'field': 'rules'}
        self.client.responses.put(warning)
        self.client.responses.put(self.final())
        with self.assertRaisesRegex(ValueError, 'Rule was converted'):
            self.query()
        self.assertEqual(self.client.warnings, [warning])
        # A warning is nonterminal in the protocol: the final response was consumed.
        self.assertTrue(self.client.responses.empty())

    def test_engine_error_is_reported_without_waiting_for_final(self):
        self.client.responses.put({'id': 'position-1', 'error': 'Illegal move'})
        with self.assertRaisesRegex(ValueError, 'Illegal move'):
            self.query()

    def test_empty_and_no_results_final_responses_are_rejected(self):
        for final in (self.final(moveInfos=[]), self.final(noResults=True)):
            with self.subTest(final=final):
                self.client.request_counter = 0
                self.client.responses.put(final)
                with self.assertRaisesRegex(ValueError, 'no usable moves'):
                    self.query()

    def test_eof_reports_engine_log_tail(self):
        self.client.logs = ['first log', 'OpenCL initialization failed']
        self.client.responses.put({'_eof': True})
        with self.assertRaisesRegex(RuntimeError, 'OpenCL initialization failed'):
            self.query()

    def test_non_json_stdout_reports_parse_error(self):
        self.client.responses.put({'_parse_error': 'not JSON'})
        with self.assertRaisesRegex(RuntimeError, 'not JSON'):
            self.query()

    def test_queue_timeout_is_explicit(self):
        self.client.responses = Mock()
        self.client.responses.get.side_effect = queue.Empty
        with self.assertRaisesRegex(TimeoutError, 'Timed out waiting for KataGo'):
            self.query()

    def test_total_deadline_prevents_waiting(self):
        self.client.deadline = time.monotonic() - 1
        with self.assertRaises(TimeoutError):
            self.query()

    def test_exited_process_is_reported_before_waiting(self):
        self.client.process.returncode = 1
        with self.assertRaisesRegex(RuntimeError, 'exited before the query'):
            self.query()

    def test_normal_close_releases_streams_and_records_cleanup(self):
        self.client.close()
        self.assertTrue(self.client.cleanup['process_stopped'])
        self.assertTrue(self.client.cleanup['reader_threads_stopped'])
        self.assertEqual(self.client.cleanup['returncode'], 0)
        self.assertTrue(self.client.input_file.closed)
        self.assertTrue(self.client.output_file.closed)
        for stream in (self.client.process.stdin, self.client.process.stdout, self.client.process.stderr):
            self.assertTrue(stream.closed)
        summary = json.loads((Path(self.directory.name) / 'cleanup.json').read_text(encoding='utf-8'))
        self.assertTrue(summary['process_stopped'])
        self.assertTrue((Path(self.directory.name) / 'engine.log').is_file())


if __name__ == '__main__':
    unittest.main()
