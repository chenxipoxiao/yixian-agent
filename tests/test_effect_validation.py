from copy import deepcopy
import unittest

from yixian.effect_validation import audit_effect_settlement
from yixian.effects import EffectEngine


def record(*, fate=45, before=1, after=1, actual=8, round_number=10, difference=21):
    return {'id':'sample', 'game_id':'whole-game', 'round':round_number, 'game_mode':3, 'season_mec':10,
            'outcome':{'status':'recorded_winner','winner_snapshot_slot':'p1',
                       'recorded_hp_delta':difference,'recorded_destiny_damage':actual},
            'players':[
                {'snapshot_slot':'p1','start_snapshot':{'talents':[],'board':[1],'xian_mo_strategies':[],
                    'fate_strategies':[],'talentTempDatas':{}},'after_snapshot':{}},
                {'snapshot_slot':'p2','start_snapshot':{'talents':[fate],'board':[2],'xian_mo_strategies':[],
                    'fate_strategies':[],'talentTempDatas':{'105':before} if fate==105 else {}},
                 'after_snapshot':{'talentTempDatas':{'105':after}}}]}


class EffectValidationTests(unittest.TestCase):
    def test_targeted_damage_compares_same_records_and_does_not_mutate(self):
        row=record()
        original=deepcopy(row)
        audit=audit_effect_settlement([row],engine=EffectEngine())
        self.assertEqual(audit['same_eligible_records'],{'base_matching':0,'base_mismatching':1,
                         'implemented_matching':1,'implemented_mismatching':0})
        self.assertEqual(row,original)
        self.assertFalse(audit['current_season_rules_verified'])
        self.assertEqual(audit['coverage']['season_2011']['eligible_records'],0)

    def test_after_counter_cannot_enable_spent_immunity(self):
        row=record(fate=105,before=0,after=1,actual=0)
        audit=audit_effect_settlement([row])
        compared=audit['records'][0]
        self.assertEqual(compared['implemented_damage'],16)
        self.assertFalse(compared['implemented_match'])
        self.assertEqual(compared['counter_output_comparison']['predicted_remaining'],0)
        self.assertEqual(audit['counter_outputs']['mismatching'],1)

    def test_counter_transition_is_verified_as_output(self):
        row=record(fate=105,before=1,after=0,actual=0)
        audit=audit_effect_settlement([row])
        self.assertEqual(audit['counter_outputs'],{'checked':1,'matching':1,'mismatching':0})
        self.assertEqual(audit['records'][0]['implemented_damage'],0)

    def test_known_unimplemented_cards_and_fates_are_excluded(self):
        row=record()
        row['players'][0]['start_snapshot']['board'].append(5000006)
        row['players'][1]['start_snapshot']['talents'].append(154)
        audit=audit_effect_settlement([row])
        self.assertEqual(audit['eligible_records'],0)
        self.assertEqual(audit['excluded_target_records'],1)
        self.assertIn('winner_unimplemented_destiny_card:5000006',audit['exclusion_reasons'])
        self.assertIn('loser_unimplemented_settlement_fate:154',audit['exclusion_reasons'])
        self.assertNotIn('implemented_damage',audit['records'][0])

    def test_missing_start_counter_is_not_inferred_from_after(self):
        row=record(fate=105,before=1,after=0,actual=0)
        del row['players'][1]['start_snapshot']['talentTempDatas']
        audit=audit_effect_settlement([row])
        self.assertEqual(audit['eligible_records'],0)
        self.assertIn('loser_talent_105_start_counter_dictionary_missing',audit['exclusion_reasons'])

    def test_no_target_effect_does_not_inflate_coverage(self):
        row=record()
        row['players'][1]['start_snapshot']['talents']=[]
        audit=audit_effect_settlement([row])
        self.assertEqual(audit['target_records'],0)
        self.assertEqual(audit['outside_target_scope_records'],1)
        self.assertEqual(audit['same_eligible_records']['implemented_matching'],0)

    def test_invalid_outcome_is_not_a_comparison_label(self):
        row=record()
        row['outcome']['recorded_hp_delta']='unknown'
        audit=audit_effect_settlement([row])
        self.assertEqual(audit['eligible_records'],0)
        self.assertEqual(audit['baseline_full_sample']['records_checked'],0)
        self.assertIn('recorded_outcome_unavailable_or_invalid',audit['exclusion_reasons'])


if __name__=='__main__':
    unittest.main()
