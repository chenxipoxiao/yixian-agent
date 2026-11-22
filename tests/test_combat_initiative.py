from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from yixian.combat_initialization import IncompleteCombatState
from yixian.combat_initiative import (
    EVIDENCE,ROOT,UnsupportedSpeedComponent,load_initiative_contract,
    derive_displayed_speed,compare_initiative_candidates,
)


def snapshot(exp=20,buffs=None,talents=None,keyin=None):
    return {'exp':999,'permanentBuffTempDatas':{'369':999},'lastRoundData':{
        'exp':exp,'permanentBuffTempDatas':{} if buffs is None else buffs,
        'talents':[24] if talents is None else talents,'usedKeYinCards':[] if keyin is None else keyin}}


class InitiativeTests(unittest.TestCase):
    def test_all_four_stored_speed_components_are_summed_once(self):
        r=derive_displayed_speed(snapshot(20,{'10012':2,'10045':4,'10056':3,'369':5}))
        self.assertEqual((r['extra_speed'],r['candidate_initiative_score']),(14,34))

    def test_signed_values_are_not_replaced_by_effect_description_constants(self):
        r=derive_displayed_speed(snapshot(20,{'10056':7,'369':-10}))
        self.assertEqual((r['extra_speed'],r['candidate_initiative_score']),(-3,17))

    def test_unrelated_permanent_counters_do_not_increase_speed(self):
        r=derive_displayed_speed(snapshot(20,{'10000':100,'10023':30,'10024':66,'17':1}))
        self.assertEqual(r['candidate_initiative_score'],20)

    def test_current_and_future_public_values_are_ignored(self):
        p=snapshot(12,{'369':3});r=derive_displayed_speed(p)
        p.update(exp=500,firstPlayerId='future',winner='irrelevant')
        self.assertEqual(derive_displayed_speed(p),r)

    def test_explicit_empty_maps_and_lists_are_valid(self):
        r=derive_displayed_speed(snapshot(0,{},[],[]))
        self.assertEqual(r['candidate_initiative_score'],0)

    def test_missing_snapshot_fields_are_not_defaulted(self):
        for field in ('exp','permanentBuffTempDatas','talents','usedKeYinCards'):
            p=snapshot();del p['lastRoundData'][field]
            with self.subTest(field=field),self.assertRaises(IncompleteCombatState):derive_displayed_speed(p)

    def test_conditional_talent_variants_reject_even_with_talent278(self):
        for identifier in (128,10128,20128,30128):
            with self.subTest(identifier=identifier),self.assertRaises(UnsupportedSpeedComponent):
                derive_displayed_speed(snapshot(talents=[identifier,278]))

    def test_speed_engraving_variants_require_reviewed_parameters(self):
        for identifier in (42,10042,20042):
            with self.subTest(identifier=identifier),self.assertRaises(UnsupportedSpeedComponent):
                derive_displayed_speed(snapshot(keyin=[identifier]))

    def test_other_engraving_and_talent_ids_do_not_add_speed_in_this_helper(self):
        self.assertEqual(derive_displayed_speed(snapshot(keyin=[41,10043],talents=[24,25,85]))['extra_speed'],0)

    def test_invalid_identifiers_and_values_fail(self):
        for field,values in [('talents',[True]),('talents',[0]),('usedKeYinCards',[-1]),('usedKeYinCards',None)]:
            p=snapshot();p['lastRoundData'][field]=values
            with self.subTest(field=field,values=values),self.assertRaises(IncompleteCombatState):derive_displayed_speed(p)
        for value in (True,1.5,'3',-1):
            with self.subTest(value=value),self.assertRaises(IncompleteCombatState):derive_displayed_speed(snapshot(value))

    def test_malformed_permanent_maps_reject(self):
        for value in ({'0369':2},{369:2},{'369':True},[],None):
            p=snapshot();p['lastRoundData']['permanentBuffTempDatas']=value
            with self.subTest(value=value),self.assertRaises(IncompleteCombatState):derive_displayed_speed(p)

    def test_mode_scope_rejects_other_modes_and_nonintegers(self):
        for mode in (16,121,True,'3'):
            with self.subTest(mode=mode),self.assertRaises(IncompleteCombatState):derive_displayed_speed(snapshot(),game_mode=mode)

    def test_higher_total_can_reverse_cultivation_only_candidate(self):
        r=compare_initiative_candidates([snapshot(10,{'10056':3}),snapshot(12)])
        self.assertEqual(r['candidate_first_index'],0);self.assertTrue(r['strict_score_order_available'])
        self.assertFalse(r['actual_initiative_resolved'])

    def test_swap_is_symmetric_and_inputs_unchanged(self):
        p=[snapshot(10),snapshot(15)];original=deepcopy(p)
        self.assertEqual(compare_initiative_candidates(p)['candidate_first_index'],1)
        self.assertEqual(compare_initiative_candidates(p[::-1])['candidate_first_index'],0)
        self.assertEqual(p,original)

    def test_tie_never_selects_first_slot_or_samples_an_outcome(self):
        for _ in range(2):
            r=compare_initiative_candidates([snapshot(10,{'369':2}),snapshot(12)])
            self.assertIsNone(r['candidate_first_index']);self.assertFalse(r['strict_score_order_available'])
            self.assertFalse(r['actual_initiative_resolved'])

    def test_pair_count_and_nested_input_validation(self):
        for value in ([],[snapshot()],{},[snapshot(),snapshot(),snapshot()]):
            with self.subTest(value=value),self.assertRaises(IncompleteCombatState):compare_initiative_candidates(value)

    def test_calibration_and_label_guards_remain_false(self):
        r=compare_initiative_candidates([snapshot(),snapshot(1)])
        for key in ('full_initiative_rules_recovered','counterfactual_safe','server_parity_verified','training_label_allowed','observed_first_used_as_input'):
            self.assertFalse(r[key])
        self.assertEqual(r['players'][0]['resonance_context'],'not_evaluated; absence_is_not_assumed')

    def test_contract_pins_evidence(self):
        self.assertFalse(load_initiative_contract()['training_label_allowed'])
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/EVIDENCE;path.parent.mkdir(parents=True);path.write_bytes((ROOT/EVIDENCE).read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'evidence hash mismatch'):load_initiative_contract(Path(d))
