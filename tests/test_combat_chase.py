from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from yixian.combat_chase import (
    resolve_chase, advance_chase_checkpoint, load_chase_contract, EVIDENCE,
)
from yixian.combat_initialization import ROOT, IncompleteCombatState
from yixian.combat_action_boundaries import begin_actor_turn, pending_request, advance_actor_turn
from yixian.combat_resurrection import advance_resurrection_checkpoint


def players(buffs=None, actor_index=0):
    result=[{'hp':30,'raw_buffs':{},'action_again_per_round':2,
             'chase_context':{'complete':True,'fate_strategy_ids':[],
                              'xianmo_strategy_ids':[],'talent_ids':[],'keyin_type_ids':[]},
             'resonance_context':{'selected_id':0,'round':13,'realm':4}}
            for _ in range(2)]
    result[actor_index]['raw_buffs']=dict(buffs or {})
    return result


def run(p=None, card=0, actor=0):
    return resolve_chase(players() if p is None else p,actor_index=actor,effective_card_id=card)


def chase_state(p=None, actor=0):
    # Explicit synthetic phase replies only; never replay-derived actions.
    state=begin_actor_turn(players() if p is None else p,actor_index=actor,sequence_id='synthetic-chase')
    for phase in ('turn_start_effects','action_execution'):
        request=pending_request(state)
        assert request['phase']==phase
        reply={'request_id':request['request_id'],'input_sha256':request['input_sha256'],
               'resolved':True,'players':state['players'],'action_result':1}
        state=advance_actor_turn(state,reply)
        state=advance_resurrection_checkpoint(state)['state']
    assert state['phase']=='chase_resolution_and_effects'
    return state


class ChaseTests(unittest.TestCase):
    def test_contract_preserves_nontraining_scope(self):
        c=load_chase_contract()
        self.assertEqual(c['effective_card_config_count'],3025)
        for k in ('complete_chase_rules','server_parity_verified','training_label_allowed',
                  'settlement_allowed','full_action_scheduler_available','metadata_is_legality_or_effect_coverage'):
            self.assertIs(c[k],False)

    def test_evidence_tampering_rejected(self):
        with TemporaryDirectory() as directory:
            p=Path(directory)/EVIDENCE;p.parent.mkdir(parents=True)
            p.write_bytes((ROOT/EVIDENCE).read_bytes()+b' ')
            with self.assertRaises(ValueError):load_chase_contract(directory)

    def test_no_request_is_resolved_without_mutation(self):
        p=players();r=run(p)
        self.assertTrue(r['resolved']);self.assertFalse(r['continue_action'])
        self.assertEqual(r['players'],p);self.assertEqual(r['events'],[])

    def test_bracelet_all_three_levels_request_chase(self):
        for card in (16,10016,20016):
            with self.subTest(card=card):
                r=run(card=card)
                self.assertTrue(r['continue_action'])
                self.assertEqual(r['players'][0]['raw_buffs'],{'308':1,'738':1})

    def test_cloud_cards_do_not_gain_intrinsic_chase_from_name(self):
        for card in (1000039,1000042):
            self.assertFalse(run(card=card)['continue_action'])

    def test_intrinsic_flag_does_not_spend_agility_or_other_requests(self):
        p=players({'15':20,'272':2,'413':2,'500':2});r=run(p,16)
        for k in ('15','272','413','500'):self.assertEqual(r['players'][0]['raw_buffs'][k],p[0]['raw_buffs'][k])

    def test315_presence_including_zero_negative_removes_entire_key(self):
        for value in (-1,0,1,3):
            with self.subTest(value=value):
                r=run(players({'315':value,'15':10}))
                self.assertTrue(r['continue_action']);self.assertNotIn('315',r['players'][0]['raw_buffs'])
                self.assertEqual(r['players'][0]['raw_buffs']['15'],10)

    def test451_is_persistent_request(self):
        r=run(players({'451':2}))
        self.assertTrue(r['continue_action']);self.assertEqual(r['players'][0]['raw_buffs']['451'],2)

    def test_early_restrictions_clear315_before_any_count_or_cost(self):
        for restriction in (215,561):
            p=players({str(restriction):0,'315':2,'15':20})
            r=run(p,16)
            self.assertFalse(r['continue_action']);self.assertNotIn('315',r['players'][0]['raw_buffs'])
            self.assertNotIn('308',r['players'][0]['raw_buffs']);self.assertEqual(r['players'][0]['raw_buffs']['15'],20)

    def test_all_immunity_sources_bypass_restrictions(self):
        for source in (388,462,685,28001):
            p=players({'215':1,'561':1,'104':2,'683':1})
            if source==28001:p[0]['chase_context']['xianmo_strategy_ids']=[source]
            else:p[0]['raw_buffs'][str(source)]=1
            with self.subTest(source=source):
                r=run(p,16);self.assertTrue(r['continue_action'])
                self.assertEqual(r['players'][0]['raw_buffs']['104'],2)

    def test685_immunity_survives_consumption_for_current_decision(self):
        r=run(players({'685':1,'683':1}),16)
        self.assertTrue(r['continue_action']);self.assertNotIn('685',r['players'][0]['raw_buffs'])

    def test_no_request_does_not_consume685(self):
        r=run(players({'685':1}))
        self.assertFalse(r['continue_action']);self.assertEqual(r['players'][0]['raw_buffs'],{'685':1})

    def test_cap_still_consumes685_and315_without_increment(self):
        p=players({'685':2,'315':4,'308':2,'738':7,'15':20})
        r=run(p)
        self.assertFalse(r['continue_action'])
        self.assertEqual(r['players'][0]['raw_buffs'],{'685':1,'308':2,'738':7,'15':20})

    def test_runtime_zero_limit_is_explicitly_supported(self):
        p=players({'315':1});p[0]['action_again_per_round']=0
        r=run(p)
        self.assertFalse(r['continue_action']);self.assertEqual(r['players'][0]['raw_buffs'],{})

    def test_agility_threshold_and_exact_debit(self):
        for value,continued,remaining in [(9,False,9),(10,True,None),(11,True,1)]:
            r=run(players({'15':value}))
            self.assertIs(r['continue_action'],continued)
            self.assertEqual(r['players'][0]['raw_buffs'].get('15'),remaining)

    def test_each_reduced_cost_source_is9_and_does_not_stack(self):
        for fate,season in [([348],[]),([],[7065]),([348],[7065])]:
            p=players({'15':10});p[0]['chase_context'].update(fate_strategy_ids=fate,xianmo_strategy_ids=season)
            r=run(p);self.assertTrue(r['continue_action']);self.assertEqual(r['players'][0]['raw_buffs']['15'],1)

    def test_agility_not_spent_at_cap(self):
        r=run(players({'15':20,'308':2}))
        self.assertFalse(r['continue_action']);self.assertEqual(r['players'][0]['raw_buffs'],{'15':20,'308':2})

    def test272_precedes413_and_agility(self):
        r=run(players({'272':2,'413':2,'239':1,'15':20}),17)
        self.assertEqual(r['request_source'],'buff272')
        self.assertEqual({k:r['players'][0]['raw_buffs'][k] for k in ('272','413','15')},{'272':1,'413':2,'15':20})

    def test272_requires_zero323_and_elemental_card(self):
        for p,card in [(players({'272':1}),0),(players({'272':1,'323':1}),17),(players({'272':1,'323':-1}),17)]:
            self.assertFalse(run(p,card)['continue_action'])
        self.assertTrue(run(players({'272':1,'323':0}),17)['continue_action'])

    def test413_requires_matching_activation_presence(self):
        self.assertFalse(run(players({'413':1,'237':1}),17)['continue_action'])
        r=run(players({'413':1,'239':0}),17)
        self.assertTrue(r['continue_action']);self.assertNotIn('413',r['players'][0]['raw_buffs'])

    def test500_requires_subcategory8_or9(self):
        self.assertFalse(run(players({'500':1}))['continue_action'])
        r=run(players({'500':1,'15':10}),83)
        self.assertTrue(r['continue_action']);self.assertEqual(r['request_source'],'buff500')
        self.assertNotIn('500',r['players'][0]['raw_buffs']);self.assertEqual(r['players'][0]['raw_buffs']['15'],10)

    def test_conditional_requests_not_consumed_at_cap(self):
        for buff,card in [(272,17),(413,17),(500,83)]:
            p=players({str(buff):1,'239':1,'308':2})
            r=run(p,card);self.assertFalse(r['continue_action']);self.assertEqual(r['players'],p)

    def test_nonpositive_consumable_presence_is_removed(self):
        for value in (0,-1):
            r=run(players({'272':value}),17)
            self.assertTrue(r['continue_action']);self.assertNotIn('272',r['players'][0]['raw_buffs'])

    def test683_stops_after_count_without_success_count(self):
        r=run(players({'683':1,'15':10,'308':1,'738':9}))
        self.assertTrue(r['resolved']);self.assertFalse(r['continue_action'])
        self.assertEqual(r['players'][0]['raw_buffs'],{'683':1,'308':2,'738':9})

    def test104_unresolved_rolls_back_even_earlier_agility_debit(self):
        p=players({'104':1,'15':10});r=run(p)
        self.assertFalse(r['resolved']);self.assertIsNone(r['continue_action'])
        self.assertEqual(r['players'],p);self.assertEqual(r['events'],[])

    def test_unsupported_post_effects_block_atomically(self):
        cases=[('self',235),('self',614),('self',640),('self',690),('other',256),('other',279),
               ('fate',340),('season',7112),('talent',209),('keyin',163)]
        for kind,value in cases:
            p=players({'315':1,'685':1})
            if kind in ('self','other'):p[kind=='other']['raw_buffs'][str(value)]=1
            else:
                field={'fate':'fate_strategy_ids','season':'xianmo_strategy_ids','talent':'talent_ids','keyin':'keyin_type_ids'}[kind]
                p[0]['chase_context'][field]=[value]
                if kind=='talent':p[0]['raw_buffs']['444']=1
            with self.subTest(kind=kind,value=value):
                r=run(p);self.assertFalse(r['resolved']);self.assertEqual(r['players'],p);self.assertEqual(r['events'],[])

    def test_non_reached_effects_do_not_block_no_chase(self):
        p=players({'614':1});p[0]['chase_context']['fate_strategy_ids']=[340]
        self.assertTrue(run(p)['resolved']);self.assertFalse(run(p)['continue_action'])

    def test_non_reached_effects_do_not_block_cap_or683(self):
        for buffs in ({'235':1,'308':2},{'235':1,'683':1}):
            r=run(players(buffs));self.assertTrue(r['resolved']);self.assertFalse(r['continue_action'])

    def test_resonance7_effect_boundary(self):
        for round_no,expected in [(12,True),(13,False)]:
            p=players();p[0]['resonance_context'].update(selected_id=7,round=round_no)
            self.assertIs(run(p,16)['resolved'],expected)

    def test_missing_resonance_does_not_become_zero(self):
        p=players({'315':1});del p[0]['resonance_context'];r=run(p)
        self.assertFalse(r['resolved']);self.assertEqual(r['players'],p)

    def test_missing_complete_context_or_limit_blocks(self):
        for key in ('chase_context','action_again_per_round'):
            p=players();del p[0][key];self.assertFalse(run(p,16)['resolved'])
        for key in ('complete','fate_strategy_ids','xianmo_strategy_ids','talent_ids','keyin_type_ids'):
            p=players();del p[0]['chase_context'][key];self.assertFalse(run(p,16)['resolved'])

    def test_malformed_context_and_numeric_values_rejected(self):
        for field,value in [('action_again_per_round',True),('action_again_per_round',-1)]:
            p=players();p[0][field]=value
            with self.assertRaises(IncompleteCombatState):run(p,16)
        p=players();p[0]['chase_context']['talent_ids']=[True]
        with self.assertRaises(IncompleteCombatState):run(p,16)
        with self.assertRaises(IncompleteCombatState):run(actor=True)
        with self.assertRaises(IncompleteCombatState):run(card=True)
        with self.assertRaises(IncompleteCombatState):resolve_chase(players(),actor_index=0,effective_card_id=0,game_mode=1)

    def test_unknown_or_overridden_effective_card_blocks(self):
        self.assertFalse(run(card=2**31-1)['resolved'])
        p=players();p[0]['card_config_overrides']={'actionAgain':False}
        self.assertFalse(run(p,16)['resolved'])

    def test_counter_totals_accumulate_and_input_is_immutable(self):
        p=players({'308':1,'738':9,'315':1});before=deepcopy(p)
        r=run(p);self.assertEqual(p,before)
        self.assertEqual(r['players'][0]['raw_buffs'],{'308':2,'738':10})

    def test_right_actor_retains_left_right_slots(self):
        p=players({'15':10},actor_index=1);before=deepcopy(p)
        r=run(p,actor=1)
        self.assertEqual(r['players'][0],before[0]);self.assertEqual(r['players'][1]['raw_buffs'],{'308':1,'738':1})
        self.assertTrue(all(e['player_index']==1 for e in r['events']))

    def test_success_routes_through_resurrection_before_next_card(self):
        s=chase_state();r=advance_chase_checkpoint(s,effective_card_id=16)
        self.assertEqual(r['state']['phase'],'resurrection_after_chase_effects')
        self.assertEqual(advance_resurrection_checkpoint(r['state'])['state']['phase'],'action_execution')
        self.assertEqual(r['request']['input_sha256'],pending_request(s)['input_sha256'])

    def test_no_chase_routes_to_pre_turn_end_resurrection(self):
        r=advance_chase_checkpoint(chase_state(),effective_card_id=0)
        self.assertEqual(r['state']['phase'],'resurrection_before_turn_end')

    def test_unresolved_checkpoint_does_not_advance_or_consume(self):
        s=chase_state(players({'315':1,'614':1}));before=deepcopy(s)
        r=advance_chase_checkpoint(s,effective_card_id=0)
        self.assertEqual(r['state']['phase'],s['phase']);self.assertEqual(r['state']['completed_hooks'],s['completed_hooks'])
        self.assertEqual(r['state']['players'],s['players']);self.assertEqual(s,before)

    def test_handler_rejects_other_phase(self):
        with self.assertRaises(IncompleteCombatState):
            advance_chase_checkpoint(begin_actor_turn(players(),actor_index=0,sequence_id='wrong'),effective_card_id=16)

    def test18_guard_survives_chase_until_turn_end_boundary(self):
        p=players({'18':1});p[0]['hp']=-3
        r=advance_chase_checkpoint(chase_state(p),effective_card_id=16)
        self.assertEqual(r['state']['players'][0]['raw_buffs']['18'],1)
        continued=advance_resurrection_checkpoint(r['state'])['state']
        self.assertEqual(continued['phase'],'action_execution')
        self.assertFalse(continued['training_label_allowed']);self.assertIsNone(continued['winner_index'])


if __name__=='__main__':unittest.main()
