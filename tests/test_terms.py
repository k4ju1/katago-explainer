"""Glossary selection must be stable and cannot leak caller edits."""

import unittest

from explainer.terms import get_terms


class GlossaryTests(unittest.TestCase):
    def test_unknown_and_duplicate_ids_are_skipped_while_order_is_preserved(self):
        rows = get_terms(['atari', 'unknown-term', 'joseki', 'atari', None, {}, ['ko'], 'ko'])
        self.assertEqual([row['id'] for row in rows], ['atari', 'joseki', 'ko'])
        self.assertEqual(rows[0]['term']['zh'], '打吃')
        self.assertEqual(set(rows[0]), {'id', 'term', 'definition'})
        self.assertEqual(set(rows[0]['definition']), {'zh', 'en'})

    def test_single_id_and_empty_inputs(self):
        self.assertEqual(get_terms('komoku')[0]['term']['zh'], '小目')
        self.assertEqual(get_terms('unknown-term'), [])
        self.assertEqual(get_terms([]), [])
        self.assertEqual(get_terms(None), [])

    def test_results_are_independent_nested_dictionaries(self):
        first = get_terms(['sente', 'thickness'])
        first[0]['term']['zh'] = 'changed'
        first[1]['definition']['en'] = 'changed'
        later = get_terms(['sente', 'thickness'])
        self.assertEqual(later[0]['term']['zh'], '先手')
        self.assertNotEqual(later[1]['definition']['en'], 'changed')


if __name__ == '__main__':
    unittest.main()
