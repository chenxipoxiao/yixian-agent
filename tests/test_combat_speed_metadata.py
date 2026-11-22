from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from yixian.combat_initialization import ROOT, IncompleteCombatState
from yixian.combat_initiative import derive_displayed_speed, compare_initiative_candidates, load_initiative_contract
from yixian.combat_speed_metadata import (
    METADATA, EVIDENCE, load_speed_metadata, _same_wuxing,
)


def snapshot(cards=None, talents=None, keyin=None, exp=20, buffs=None):
    return {'lastRoundData': {'exp': exp, 'usedCards': [18] if cards is None else cards,
                             'talents': [128] if talents is None else talents,
                             'usedKeYinCards': [] if keyin is None else keyin,
                             'permanentBuffTempDatas': {} if buffs is None else buffs}}


class ConditionalSpeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.metadata = load_speed_metadata()

    def derive(self, p):
        return derive_displayed_speed(p, speed_metadata=self.metadata)

    def test_exact_variants_have_distinct_speed(self):
        for identifier, speed in [(128,3),(10128,4),(20128,5),(30128,6)]:
            with self.subTest(identifier=identifier):
                self.assertEqual(self.derive(snapshot(talents=[identifier]))['extra_speed'],speed)

    def test_single_element_with_neutral_cards_qualifies(self):
        self.assertEqual(self.derive(snapshot(cards=[0,18,-1,10018]))['extra_speed'],3)

    def test_no_element_and_empty_boards_do_not_qualify(self):
        for cards in ([],[0],[-1,0]):
            with self.subTest(cards=cards):self.assertEqual(self.derive(snapshot(cards=cards))['extra_speed'],0)

    def test_mixed_elements_do_not_qualify(self):
        for cards in ([17,18],[18,17]):
            with self.subTest(cards=cards):self.assertEqual(self.derive(snapshot(cards=cards))['extra_speed'],0)

    def test_exact_278_overrides_mixed_or_absent_elements(self):
        for cards in ([17,18],[],[0]):
            r=self.derive(snapshot(cards=cards,talents=[128,278]))
            self.assertEqual(r['extra_speed'],3)
            self.assertTrue(r['conditional_talent_components'][0]['exact_278_override'])

    def test_modulo278_is_not_an_override(self):
        self.assertEqual(self.derive(snapshot(cards=[17,18],talents=[128,10278]))['extra_speed'],0)

    def test_override_does_not_hide_unknown_board(self):
        with self.assertRaises(IncompleteCombatState):self.derive(snapshot(cards=[987654321],talents=[128,278]))

    def test_missing_board_is_not_repaired_with_current_board(self):
        p=snapshot();del p['lastRoundData']['usedCards'];p['usedCards']=[18]
        with self.assertRaises(IncompleteCombatState):self.derive(p)

    def test_malformed_unknown_or_out_of_scope_boards_reject(self):
        for cards in (None,{},[True],['18'],[-2],[987654321],[18]*9):
            p=snapshot();p['lastRoundData']['usedCards']=cards
            with self.subTest(cards=cards),self.assertRaises(IncompleteCombatState):self.derive(p)

    def test_unknown_family128_variant_rejects_even_if_condition_false(self):
        with self.assertRaises(IncompleteCombatState):self.derive(snapshot(cards=[],talents=[40128]))

    def test_known_speed_engravings_sum_exact_parameters(self):
        self.assertEqual(self.derive(snapshot(talents=[],keyin=[40042,50042]))['extra_speed'],7)

    def test_unknown_engraving_does_not_fall_back_to_another_config(self):
        for identifier in (42,10042,20042,60042):
            with self.subTest(identifier=identifier),self.assertRaises(IncompleteCombatState):
                self.derive(snapshot(talents=[],keyin=[identifier]))

    def test_engraving_only_does_not_require_unread_board(self):
        p=snapshot(talents=[],keyin=[40042]);del p['lastRoundData']['usedCards']
        self.assertEqual(self.derive(p)['extra_speed'],3)

    def test_components_accumulate_without_replacing_stored_speed(self):
        r=self.derive(snapshot(keyin=[50042],buffs={'369':-2,'10056':7,'17':1}))
        self.assertEqual((r['extra_speed'],r['candidate_initiative_score']),(12,32))

    def test_display_loops_count_occurrences_without_implying_legal_duplicates(self):
        r=self.derive(snapshot(talents=[128,128],keyin=[40042,40042]))
        self.assertEqual(r['extra_speed'],12)

    def test_scan_matches_first_card_early_break(self):
        self.assertTrue(_same_wuxing([('金灵','木灵')]))
        self.assertFalse(_same_wuxing([('金灵',),('金灵','木灵')]))
        self.assertTrue(_same_wuxing([('金灵','木灵'),('金灵',)]))

    def test_current_private_and_outcome_fields_do_not_affect_prediction(self):
        p=snapshot();r=self.derive(p)
        p.update(usedCards=[17,18],talents=[30128,278],exp=999,firstPlayerId='future',privateData={'usedCards':[17]})
        self.assertEqual(self.derive(p),r)

    def test_inputs_are_unchanged_and_metadata_immutable(self):
        p=snapshot();original=deepcopy(p);self.derive(p);self.assertEqual(p,original)
        with self.assertRaises(TypeError):self.metadata.talent_speed[128]=999

    def test_untyped_metadata_rejects(self):
        with self.assertRaises(IncompleteCombatState):derive_displayed_speed(snapshot(),speed_metadata={})

    def test_conditional_speed_can_reverse_candidate_but_ties_still_abstain(self):
        p=[snapshot(exp=10),snapshot(talents=[],exp=12)]
        r=compare_initiative_candidates(p,speed_metadata=self.metadata)
        self.assertEqual(r['candidate_first_index'],0)
        p[1]['lastRoundData']['exp']=13
        self.assertIsNone(compare_initiative_candidates(p,speed_metadata=self.metadata)['candidate_first_index'])

    def test_metadata_and_evidence_hashes_are_enforced(self):
        for changed in (METADATA,EVIDENCE):
            with tempfile.TemporaryDirectory() as d:
                for name in (METADATA,EVIDENCE):
                    p=Path(d)/name;p.parent.mkdir(parents=True,exist_ok=True)
                    p.write_bytes((ROOT/name).read_bytes()+(b' ' if changed==name else b''))
                with self.assertRaisesRegex(ValueError,'hash mismatch'):load_speed_metadata(d)

    def test_contract_and_results_keep_label_and_server_guards(self):
        c=load_initiative_contract(include_conditional_metadata=True)
        self.assertEqual(c['conditional_metadata']['engraving_ids'],[40042,50042])
        for obj in (c,self.derive(snapshot())):
            for key in ('server_parity_verified','training_label_allowed','counterfactual_safe','full_initiative_rules_recovered'):
                self.assertFalse(obj[key])
