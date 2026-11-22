from copy import deepcopy
import unittest
from yixian.combat_report_comparison_v1 import cases_equal, canonical_case


def case(key='13007'):
    return {'compiled': {'preparation_v77_context': {'bindings': [
        {'values': {key: 0}}]}}, 'simulation': {'hp_delta': 70,
        'trace': [{'hp': -15}]}, 'settlement': {'life_damage': 20}}


class ReportComparison(unittest.TestCase):
    def test_documented_integer_key_boundary_and_no_mutation(self):
        live = case(13007); original = deepcopy(live)
        self.assertTrue(cases_equal(case(), live))
        self.assertEqual(live, original)

    def test_combat_terminal_change_rejected(self):
        changed = case(); changed['simulation']['hp_delta'] += 1
        self.assertFalse(cases_equal(case(), changed))

    def test_intermediate_trace_change_rejected(self):
        changed = case(); changed['simulation']['trace'][0]['hp'] += 1
        self.assertFalse(cases_equal(case(), changed))

    def test_settlement_change_rejected(self):
        changed = case(); changed['settlement']['life_damage'] -= 1
        self.assertFalse(cases_equal(case(), changed))

    def test_metadata_value_and_presence_not_ignored(self):
        changed = case(); changed['compiled']['preparation_v77_context']['bindings'][0]['values']['13007'] = 1
        self.assertFalse(cases_equal(case(), changed))
        del changed['compiled']['preparation_v77_context']
        self.assertFalse(cases_equal(case(), changed))

    def test_colliding_keys_rejected(self):
        changed = case(); changed['compiled']['preparation_v77_context']['bindings'][0]['values'][13007] = 0
        with self.assertRaises(ValueError): canonical_case(changed)

    def test_undocumented_key_and_nonfinite_rejected(self):
        changed = case(); changed['simulation'][1] = 2
        with self.assertRaises(ValueError): canonical_case(changed)
        changed = case(); changed['simulation']['hp_delta'] = float('nan')
        with self.assertRaises(ValueError): canonical_case(changed)

    def test_value_types_not_coerced(self):
        changed = case(); changed['settlement']['life_damage'] = 20.0
        self.assertFalse(cases_equal(case(), changed))


if __name__ == '__main__': unittest.main()
