import copy
import unittest
from tests import test_combat_start_hand_projection_v3 as prior_tests
from yixian.combat_start_hand_projection_v178 import add_start_hands,CONTRACT


class StartHandProjectionV178Tests(prior_tests.StartHandProjectionTests):
    def project(self):
        return add_start_hands(self.turn,self.source,self.row,self.ctx,self.req)

    def dream(self):
        self.req[0]['required_field']='dream_echo_hand'
        self.row['players'][0]['candidate_start']['board']=[349,2]
        self.turn['p1']['publicData']['lastRoundData']['usedCards']=[349,2]

    def test_dream_same_start_source_guard_and_order(self):
        self.dream();before=copy.deepcopy((self.turn,self.row,self.ctx))
        result=self.project();h=result['players'][0].pop('dream_echo_hand')
        self.assertEqual(h['raw_cards'],[7,8]);self.assertEqual(h['projection_contract'],CONTRACT)
        self.assertEqual(result,self.ctx);self.assertEqual((self.turn,self.row,self.ctx),before)
        del self.turn['p1']['publicData']['lastRoundData']['handCards']
        with self.assertRaises(ValueError):self.project()

    def test_dream_requires_same_seat_consumer_and_no_replacement(self):
        self.dream();self.req[0]['player_index']=1
        with self.assertRaisesRegex(ValueError,'consumer'):self.project()
        self.req[0]['player_index']=0;self.ctx=self.project()
        with self.assertRaisesRegex(ValueError,'replace'):self.project()

    def test_dream_and_flag_additions_are_atomic(self):
        self.dream();self.req.append({**self.req[0],'player_index':1,'required_field':'element_flag_hand'})
        result=self.project();self.assertEqual(result['players'][0]['dream_echo_hand']['raw_cards'],[7,8])
        self.assertEqual(result['players'][1]['element_flag_hand']['raw_cards'],[7,8])
        before=copy.deepcopy(self.ctx);self.turn['p2']['publicData']['lastRoundData']['handCards']=None
        with self.assertRaises(ValueError):self.project()
        self.assertEqual(self.ctx,before)

    def test_dream_does_not_import_outcome_or_current_private_fields(self):
        self.dream();expected=self.project()
        self.turn['p1']['privateData']={'handCards':[99999]};self.turn['p1']['publicData']['handCards']=[88888]
        self.row['outcome']={'recorded_hp_delta':999,'winner_snapshot_slot':'p1'}
        self.turn['battleParams']=[0,1,999];self.turn['hpDelta']=-200
        self.assertEqual(self.project(),expected)


if __name__=='__main__':unittest.main()
