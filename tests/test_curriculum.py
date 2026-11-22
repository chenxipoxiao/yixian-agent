import unittest
from copy import deepcopy
from yixian.curriculum import make_cases, split_cases, fingerprint


class CurriculumTests(unittest.TestCase):
    def test_case_generation_and_grouping_are_reproducible(self):
        cases = make_cases(12)
        self.assertEqual(fingerprint(cases), fingerprint(make_cases(12)))
        variant = deepcopy(cases[0]); variant['id'] += '-view2'
        splits = split_cases(cases + [variant])
        groups = [{r['source']['game_id'] for r in rows} for rows in splits.values()]
        for i, left in enumerate(groups):
            for right in groups[i+1:]:
                self.assertFalse(left & right)
        self.assertTrue(all(r['source']['evidence']=='synthetic' for r in cases))


if __name__ == '__main__':
    unittest.main()
