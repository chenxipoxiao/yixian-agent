import unittest
from yixian.settlement import ordinary_destiny_damage, audit_recorded_damage


class SettlementTests(unittest.TestCase):
    def test_client_branch_boundaries(self):
        self.assertEqual(ordinary_destiny_damage(1, 20), 5)
        self.assertEqual(ordinary_destiny_damage(1, 21), 6)
        self.assertEqual(ordinary_destiny_damage(1, 200), 7)
        self.assertEqual(ordinary_destiny_damage(9, 20), 13)
        self.assertEqual(ordinary_destiny_damage(10, 20), 15)
        self.assertEqual(ordinary_destiny_damage(10, 1000), 22)

    def test_negative_or_nonfinite_input_rejected(self):
        for value in (-1, float('nan'), float('inf'), True):
            with self.assertRaises(ValueError):
                ordinary_destiny_damage(1, value)

    def test_mismatch_is_evidence_not_relabelled(self):
        result = audit_recorded_damage([{'id':'a', 'round':1, 'outcome':{
            'status':'recorded_winner','recorded_hp_delta':-21, 'recorded_destiny_damage':-3}}])
        self.assertEqual(result['mismatching'], 1)
        self.assertFalse(result['current_season_rules_verified'])
