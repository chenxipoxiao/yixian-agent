from copy import deepcopy
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from yixian.combat_chase import resolve_chase as resolve_v1
from yixian.combat_chase_v2 import resolve_chase, advance_chase_checkpoint, load_chase_contract, EVIDENCE
from yixian.combat_initialization import ROOT, IncompleteCombatState
from yixian.combat_action_boundaries import begin_actor_turn, pending_request, advance_actor_turn
from yixian.combat_resurrection import advance_resurrection_checkpoint


def players(buffs=None, actor=0):
    states=[{'hp':30,'raw_buffs':{},'action_again_per_round':2,
             'chase_context':{'complete':True,'fate_strategy_ids':[],
                              'xianmo_strategy_ids':[],'talent_ids':[],'keyin_type_ids':[]},
             'resonance_context':{'selected_id':0,'round':13,'realm':4}} for _ in range(2)]
    states[actor]['raw_buffs']=dict(buffs or {})
    return states


def run(p=None, card=0, actor=0):
    return resolve_chase(players() if p is None else p,actor_index=actor,effective_card_id=card)


def boundary(p, actor=0):
    # Explicit component fixtures, not inferred human gameplay actions.
    state=begin_actor_turn(p,actor_index=actor,sequence_id='synthetic-chase-v2')
    for phase in ('turn_start_effects','action_execution'):
        request=pending_request(state)
        assert request['phase']==phase
        state=advance_actor_turn(state,{'request_id':request['request_id'],
            'input_sha256':request['input_sha256'],'resolved':True,'players':state['players'],'action_result':1})
        state=advance_resurrection_checkpoint(state)['state']
    assert state['phase']=='chase_resolution_and_effects'
    return state


class ChaseV2Tests(unittest.TestCase):
    def test_ordinary_entangle_spends_request_and_counter_then_stops(self):
        p=players({'315':1,'104':2})
        r=run(p)
        self.assertTrue(r['resolved']);self.assertFalse(r['continue_action'])
        self.assertEqual(r['stop_or_block_reason'],'restriction104_after_counter')
        self.assertEqual(r['players'][0]['raw_buffs'],{'104':1,'308':1,'691':1})

    def test_last_entangle_removed_without_success_counter(self):
        b=run(players({'315':1,'104':1}))['players'][0]['raw_buffs']
        self.assertEqual(b,{'308':1,'691':1});self.assertNotIn('738',b)

    def test_present_zero_negative_entangle_still_counts_requested_reduction(self):
        for value in (0,-1,-5):
            p=players({'315':1,'104':value,'691':4})
            r=run(p)
            self.assertTrue(r['resolved']);self.assertFalse(r['continue_action'])
            self.assertEqual(r['players'][0]['raw_buffs'],{'691':5,'308':1})

    def test_absent_entangle_does_not_touch_debuff_counter(self):
        r=run(players({'315':1,'691':4}))
        self.assertTrue(r['continue_action'])
        self.assertEqual(r['players'][0]['raw_buffs'],{'691':4,'308':1,'738':1})

    def test_agility_is_spent_even_when_entangle_prevents_chase(self):
        for discounted,cost in ((False,10),(True,9)):
            p=players({'15':20,'104':1})
            if discounted:p[0]['chase_context']['fate_strategy_ids']=[348]
            r=run(p);self.assertEqual(r['request_source'],'agility')
            self.assertEqual(r['players'][0]['raw_buffs']['15'],20-cost)
            self.assertFalse(r['continue_action']);self.assertNotIn('738',r['players'][0]['raw_buffs'])

    def test_intrinsic_chase_does_not_spend_agility(self):
        p=players({'15':20,'104':1})
        r=run(p,card=16)
        self.assertEqual(r['request_source'],'card_action_again')
        self.assertEqual(r['players'][0]['raw_buffs']['15'],20)
        self.assertEqual(r['players'][0]['raw_buffs']['691'],1)

    def test_no_request_leaves_entangle_and_counters_unchanged(self):
        p=players({'104':1,'691':4});r=run(p)
        self.assertEqual(r['players'],p);self.assertEqual(r['events'],[])
        self.assertEqual(r['stop_or_block_reason'],'no_chase_request')

    def test_limit_reached_removes_request_without_spending_entangle(self):
        p=players({'315':1,'104':2,'308':2,'691':4});r=run(p)
        self.assertEqual(r['stop_or_block_reason'],'runtime_chase_limit')
        self.assertEqual(r['players'][0]['raw_buffs'],{'104':2,'308':2,'691':4})

    def test_earlier_restrictions_take_priority(self):
        for restriction in ('215','561'):
            p=players({'315':1,'104':1,restriction:1});r=run(p)
            self.assertEqual(r['stop_or_block_reason'],'restriction215_or561')
            self.assertEqual(r['players'][0]['raw_buffs'],{'104':1,restriction:1})

    def test_entangle_precedes683_and_success_only_effects(self):
        p=players({'315':1,'104':1,'683':1,'235':1,'614':1,'640':1,'690':1})
        p[0]['chase_context'].update(fate_strategy_ids=[340],xianmo_strategy_ids=[7112],keyin_type_ids=[163])
        p[1]['raw_buffs']={'256':2,'279':3}
        r=run(p)
        self.assertTrue(r['resolved']);self.assertEqual(r['stop_or_block_reason'],'restriction104_after_counter')
        self.assertEqual(r['players'][0]['hp'],30);self.assertEqual(r['players'][1],p[1])
        for k in ('235','614','640','690','683'):self.assertEqual(r['players'][0]['raw_buffs'][k],1)

    def test_each_buff_immunity_skips_entangle_and_debuff_counter(self):
        for immunity in ('388','462','685'):
            for value in (0,1):
                p=players({'315':1,'104':1,immunity:value});r=run(p)
                self.assertTrue(r['continue_action'])
                self.assertEqual(r['players'][0]['raw_buffs']['104'],1)
                self.assertNotIn('691',r['players'][0]['raw_buffs'])
                if immunity=='685':self.assertNotIn('685',r['players'][0]['raw_buffs'])

    def test_season_immunity_skips_entangle(self):
        p=players({'315':1,'104':1});p[0]['chase_context']['xianmo_strategy_ids']=[28001]
        r=run(p);self.assertTrue(r['continue_action'])
        self.assertEqual(r['players'][0]['raw_buffs']['104'],1)
        self.assertNotIn('691',r['players'][0]['raw_buffs'])

    def test_entangle_is_actor_local(self):
        p=players({'315':1,'104':2},actor=1);p[0]['raw_buffs']={'104':4,'691':7}
        r=run(p,actor=1)
        self.assertEqual(r['players'][0],p[0])
        self.assertEqual(r['players'][1]['raw_buffs'],{'104':1,'308':1,'691':1})

    def test_exact_event_order_records_paid_cost_then_restriction(self):
        r=run(players({'15':10,'104':1}))
        self.assertEqual([e['buff_id'] for e in r['events']],[15,308,104,691])
        self.assertEqual([e['requested_delta'] for e in r['events']],[-10,1,-1,1])

    def test_missing_resonance_returns_original_state_and_no_events(self):
        for key in (None,'selected_id','round','realm'):
            p=players({'15':10,'104':1})
            if key is None:del p[0]['resonance_context']
            else:del p[0]['resonance_context'][key]
            saved=deepcopy(p);r=run(p)
            self.assertFalse(r['resolved']);self.assertEqual(r['players'],saved);self.assertEqual(r['events'],[])
            self.assertEqual(r['stop_or_block_reason'],'missing_restriction104_resonance_context')
            self.assertEqual(p,saved)

    def test_nonzero_resonance_rejected_including_override_conditions(self):
        for selected in (7,136):
            p=players({'315':1,'104':1,'444':1});p[0]['chase_context']['talent_ids']=[206]
            p[0]['resonance_context']['selected_id']=selected
            r=run(p);self.assertFalse(r['resolved'])
            self.assertEqual(r['stop_or_block_reason'],'unsupported_restriction104_resonance_context')
            self.assertEqual(r['players'],p);self.assertEqual(r['events'],[])

    def test_206_and444_without_resonance_cannot_bypass_entangle(self):
        p=players({'315':1,'104':1,'444':1});p[0]['chase_context']['talent_ids']=[206]
        r=run(p);self.assertTrue(r['resolved']);self.assertFalse(r['continue_action'])
        self.assertEqual(r['players'][0]['hp'],30)

    def test_opponent277_presence_rejected_without_tentative_costs(self):
        for value in (-1,0,3):
            p=players({'15':10,'104':1});p[1]['raw_buffs']={'277':value}
            r=run(p)
            self.assertFalse(r['resolved']);self.assertEqual(r['players'],p);self.assertEqual(r['events'],[])
            self.assertEqual(r['stop_or_block_reason'],'unsupported_opponent277_restriction104_effect')

    def test_immunity_does_not_reach_opponent277(self):
        p=players({'315':1,'104':1,'388':1});p[1]['raw_buffs']={'277':3}
        r=run(p)
        self.assertTrue(r['continue_action']);self.assertNotIn('105',r['players'][0]['raw_buffs'])

    def test_counter_bounds_raise_without_mutating_inputs(self):
        p=players({'15':10,'104':1,'691':1_000_000});saved=deepcopy(p)
        with self.assertRaises(IncompleteCombatState):run(p)
        self.assertEqual(p,saved)

    def test_phase_reply_stops_and_still_requires_turn_end_resurrection(self):
        state=boundary(players({'315':1,'104':1}));saved=deepcopy(state)
        r=advance_chase_checkpoint(state,effective_card_id=0)
        self.assertEqual(state,saved)
        self.assertEqual(r['state']['phase'],'resurrection_before_turn_end')
        self.assertEqual(r['state']['players'][0]['raw_buffs'],{'308':1,'691':1})
        self.assertFalse(r['training_label_allowed']);self.assertFalse(r['settlement_allowed'])

    def test_unresolved_phase_reply_cannot_advance_or_spend(self):
        p=players({'15':10,'104':1});del p[0]['resonance_context']
        state=boundary(p)
        r=advance_chase_checkpoint(state,effective_card_id=0)
        self.assertEqual(r['state']['phase'],'chase_resolution_and_effects')
        self.assertEqual(r['state']['players'],state['players'])

    def test_non_entangle_paths_match_legacy_results(self):
        for card in (0,16,1000039):
            for buffs in ({},{'315':1},{'15':20},{'315':1,'215':1},
                          {'315':1,'683':1},{'315':1,'614':1},{'315':1,'308':2}):
                p=players(buffs);old=resolve_v1(p,actor_index=0,effective_card_id=card);new=run(p,card=card)
                for key in ('resolved','players','events','continue_action','request_source','stop_or_block_reason'):
                    self.assertEqual(new[key],old[key],(card,buffs,key))

    def test_legacy_entangle_scope_and_source_are_preserved(self):
        p=players({'315':1,'104':1})
        self.assertFalse(resolve_v1(p,actor_index=0,effective_card_id=0)['resolved'])
        self.assertTrue(run(p)['resolved'])
        root=Path(__file__).resolve().parents[1]
        self.assertEqual(hashlib.sha256((root/'yixian/combat_chase.py').read_bytes()).hexdigest(),
                         'f678a90f406ac3cd32206ad6b81003d2a960ceb679478c6a564305eaa29cdeef')

    def test_contract_still_disallows_full_battle_training(self):
        c=load_chase_contract();self.assertEqual(c['schema_version'],2)
        self.assertEqual(c['effective_card_config_count'],3025)
        self.assertEqual(c['prior_chase_contract']['schema_version'],1)
        for key in ('complete_chase_rules','server_parity_verified','training_label_allowed',
                    'settlement_allowed','full_action_scheduler_available'):self.assertFalse(c[key])

    def test_evidence_tampering_rejected(self):
        with TemporaryDirectory() as directory:
            p=Path(directory)/EVIDENCE;p.parent.mkdir(parents=True)
            p.write_bytes((ROOT/EVIDENCE).read_bytes()+b' ')
            with self.assertRaises(ValueError):load_chase_contract(directory)


if __name__=='__main__':unittest.main()
