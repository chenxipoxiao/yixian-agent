import copy
import unittest

from yixian.combat_card_cleanup import (BOUNDARY, resolve_normal_card_cleanup,
                                       load_card_cleanup_contract)
from yixian.combat_attack_calculation import prepare_normal_attack
from yixian.combat_hit import resolve_normal_attack_hit
from yixian.combat_initialization import IncompleteCombatState


def players():
    return [{'hp': 20, 'max_hp': 20, 'def': 0, 'raw_buffs': {},
             'attack_context': {'complete': True, 'fate_strategy_ids': [],
                                'xianmo_strategy_ids': [], 'talent_ids': [], 'keyin_type_ids': []},
             'resonance_context': {'selected_id': 0, 'round': 1, 'realm': 1}} for _ in range(2)]


def run_cleanup(p=None, **kwargs):
    return resolve_normal_card_cleanup(p if p is not None else players(),
        actor_index=kwargs.pop('actor_index', 0),
        card_item=kwargs.pop('card_item', {'effective_card_id': 0, 'had_used': False}),
        checkpoint=kwargs.pop('checkpoint', {'boundary': BOUNDARY, 'preceding_hooks_resolved': True}),
        **kwargs)


class CombatCardCleanupTests(unittest.TestCase):
    def test_plain_tail_marks_used_and_counts_effect(self):
        r=run_cleanup();self.assertTrue(r['cleanup_resolved'])
        self.assertEqual(r['candidate_players'][0]['raw_buffs'], {'363': 1})
        self.assertTrue(r['candidate_card_item']['had_used'])

    def test_only_actor_changes(self):
        p=players();p[0]['raw_buffs']={'6':7,'306':3,'302':5};r=run_cleanup(p,actor_index=1)
        self.assertEqual(r['candidate_players'][0],p[0])
        self.assertEqual(r['candidate_players'][1]['raw_buffs'],{'363':1})

    def test_sword_intent_subtracts_used_amount(self):
        p=players();p[0]['raw_buffs']={'6':9,'306':4};out=run_cleanup(p)['candidate_players'][0]['raw_buffs']
        self.assertEqual(out,{'6':5,'363':1})

    def test_used_intent_can_exhaust_current_amount(self):
        for current in (2,4):
            p=players();p[0]['raw_buffs']={'6':current,'306':4}
            self.assertNotIn('6',run_cleanup(p)['candidate_players'][0]['raw_buffs'])

    def test_absent_sword_intent_does_not_create_negative_buff(self):
        p=players();p[0]['raw_buffs']={'306':4}
        self.assertEqual(run_cleanup(p)['candidate_players'][0]['raw_buffs'],{'363':1})

    def test_unspent_intent_is_not_consumed(self):
        p=players();p[0]['raw_buffs']={'6':7}
        self.assertEqual(run_cleanup(p)['candidate_players'][0]['raw_buffs']['6'],7)

    def test_zero_used_intent_does_not_remove_existing_zero_six(self):
        p=players();p[0]['raw_buffs']={'6':0,'306':0}
        self.assertEqual(run_cleanup(p)['candidate_players'][0]['raw_buffs'],{'6':0,'363':1})

    def test_228_retains_sword_intent_consuming_one_charge(self):
        for charges,remaining in ((1,None),(2,1),(0,None),(-1,None)):
            with self.subTest(charges=charges):
                p=players();p[0]['raw_buffs']={'6':7,'306':7,'228':charges}
                out=run_cleanup(p)['candidate_players'][0]['raw_buffs']
                self.assertEqual(out.get('228'),remaining);self.assertEqual(out['6'],7)
                self.assertNotIn('306',out)

    def test_retention_without_used_marker_does_not_consume(self):
        p=players();p[0]['raw_buffs']={'6':7,'228':1}
        self.assertEqual(run_cleanup(p)['candidate_players'][0]['raw_buffs']['228'],1)

    def test_pending_intent_is_added_after_spending(self):
        p=players();p[0]['raw_buffs']={'6':7,'306':7,'307':2,'478':3}
        r=run_cleanup(p);self.assertEqual(r['candidate_players'][0]['raw_buffs'],{'6':5,'363':1})
        changes=[e['requested_delta'] for e in r['candidate_events'] if e.get('buff_id')==6]
        self.assertEqual(changes,[-7,5])

    def test_nonpositive_pending_and_bonus_follow_native_presence(self):
        for pending,bonus,expected in ((0,3,3),(-2,3,1),(-3,2,None),(-1,0,None),(-1,-2,None)):
            with self.subTest(pending=pending,bonus=bonus):
                p=players();p[0]['raw_buffs']={'307':pending,'478':bonus}
                out=run_cleanup(p)['candidate_players'][0]['raw_buffs']
                self.assertEqual(out.get('6'),expected);self.assertNotIn('307',out)
                self.assertEqual(out.get('478'),None if bonus>0 else bonus)

    def test_478_requires_307_presence(self):
        p=players();p[0]['raw_buffs']={'478':4}
        self.assertEqual(run_cleanup(p)['candidate_players'][0]['raw_buffs'],{'478':4,'363':1})

    def test_bookkeeping_transfers_damage_before_removing_markers(self):
        p=players();p[0]['raw_buffs']={'302':8,'303':2,'644':6,'363':4,'330':237,'382':9,'729':1}
        out=run_cleanup(p)['candidate_players'][0]['raw_buffs']
        self.assertEqual(out,{'644':14,'363':5})

    def test_no_damage_does_not_erase_accumulated_total(self):
        p=players();p[0]['raw_buffs']={'644':9,'302':0}
        self.assertEqual(run_cleanup(p)['candidate_players'][0]['raw_buffs'],{'644':9,'363':1})

    def test_negative_requested_delta_follows_modify_semantics(self):
        p=players();p[0]['raw_buffs']={'644':5,'302':-2,'306':-3}
        out=run_cleanup(p)['candidate_players'][0]['raw_buffs']
        self.assertEqual(out,{'644':3,'6':3,'363':1})

    def test_does_not_claim_earlier_post_hook_counters_cleared(self):
        p=players();p[0]['raw_buffs']={'333':2,'323':4,'493':4,'326':5,'409':1,'351':3}
        out=run_cleanup(p)['candidate_players'][0]['raw_buffs']
        for key,val in p[0]['raw_buffs'].items():self.assertEqual(out[key],val)

    def test_already_used_item_still_counts_another_effect(self):
        r=run_cleanup(card_item={'effective_card_id':0,'had_used':True})
        self.assertEqual(r['candidate_players'][0]['raw_buffs']['363'],1)

    def test_hit_candidates_need_explicit_prior_hook_boundary(self):
        p=players();p[0]['raw_buffs']={'6':4}
        pre=prepare_normal_attack(p,actor_index=0,effective_card_id=0,next_card_id=0)
        hit=resolve_normal_attack_hit(pre['candidate_players'],pre['pending_damage_packet'],effective_card_id=0,
              battle_context={'complete':True,'scene_behavior_present':False,'default_opponents':[1,0]})
        self.assertTrue(hit['hit_resolved']);self.assertEqual(hit['hp_loss'],7)
        self.assertEqual(hit['candidate_players'][0]['raw_buffs']['6'],4)
        blocked=run_cleanup(hit['candidate_players'],checkpoint=hit)
        self.assertFalse(blocked['cleanup_resolved'])
        # Supplying this boundary is an explicit synthetic environment case;
        # it does not assert that the missing real post-card hooks are executed.
        tail=run_cleanup(hit['candidate_players']);out=tail['candidate_players'][0]['raw_buffs']
        self.assertNotIn('6',out);self.assertNotIn('302',out);self.assertNotIn('303',out)
        self.assertEqual(out['644'],7);self.assertFalse(tail['action_completed'])

    def test_missing_or_wrong_checkpoint_does_not_mutate(self):
        for c in (None,{}, {'boundary':BOUNDARY}, {'boundary':'action_execution','preceding_hooks_resolved':True},
                  {'boundary':BOUNDARY,'preceding_hooks_resolved':1}):
            p=players();p[0]['raw_buffs']={'302':5}
            r=run_cleanup(p,checkpoint=c);self.assertFalse(r['cleanup_resolved'])
            self.assertEqual(r['candidate_players'],p);self.assertEqual(r['candidate_events'],[])

    def test_unknown_or_reached_secondary_effects_block(self):
        for buff in ('502','547','692','482','495','999999'):
            for index in (0,1):
                p=players();p[0]['raw_buffs']={'6':5,'306':5};p[index]['raw_buffs'][buff]=1
                r=run_cleanup(p);self.assertFalse(r['cleanup_resolved'])
                self.assertEqual(r['candidate_players'],p);self.assertEqual(r['candidate_events'],[])

    def test_missing_effect_selection_is_unknown(self):
        for field in ('attack_context','resonance_context'):
            p=players();del p[1][field];self.assertFalse(run_cleanup(p)['cleanup_resolved'])

    def test_nonempty_effect_selections_block(self):
        for field in ('fate_strategy_ids','xianmo_strategy_ids','talent_ids','keyin_type_ids'):
            p=players();p[0]['attack_context'][field]=[1]
            self.assertFalse(run_cleanup(p)['cleanup_resolved'])

    def test_resonance61_not_silently_skipped(self):
        p=players();p[0]['resonance_context']['selected_id']=61
        self.assertFalse(run_cleanup(p)['cleanup_resolved'])

    def test_other_card_and_overrides_block(self):
        for item in ({'effective_card_id':100001,'had_used':False},
                     {'effective_card_id':0,'had_used':False,'card_config_overrides':{'name':'木灵'}}):
            self.assertFalse(run_cleanup(card_item=item)['cleanup_resolved'])
        p=players();p[1]['card_config_overrides']={'0':{'attack':9}}
        self.assertFalse(run_cleanup(p)['cleanup_resolved'])

    def test_types_are_explicit(self):
        for kw in ({'actor_index':True},{'game_mode':True},{'game_mode':4},
                   {'card_item':{'effective_card_id':0}},
                   {'card_item':{'effective_card_id':False,'had_used':False}},
                   {'card_item':{'effective_card_id':0,'had_used':0}}):
            with self.assertRaises(IncompleteCombatState):run_cleanup(**kw)

    def test_overflow_does_not_partially_apply(self):
        for buffs in ({'6':999999,'307':2},{'644':999999,'302':2},{'363':1000000}):
            p=players();p[0]['raw_buffs']=buffs;before=copy.deepcopy(p)
            with self.assertRaises(IncompleteCombatState):run_cleanup(p)
            self.assertEqual(p,before)

    def test_caller_objects_are_not_mutated_or_shared(self):
        p=players();p[0]['raw_buffs']={'6':6,'306':6}
        item={'effective_card_id':0,'had_used':False,'grid_number':3};before=copy.deepcopy(p)
        r=run_cleanup(p,card_item=item)
        self.assertEqual(p,before);self.assertFalse(item['had_used'])
        r['candidate_players'][0]['raw_buffs']['6']=99
        self.assertEqual(p,before);self.assertEqual(r['candidate_card_item']['grid_number'],3)

    def test_contract_and_result_keep_limits(self):
        contract=load_card_cleanup_contract();r=run_cleanup()
        self.assertEqual(contract['boundary'],BOUNDARY)
        for k in ('whole_post_card_hook_completed','action_completed','action_phase_reply_available',
                  'training_label_allowed','settlement_allowed','server_parity_verified','state_committed'):
            self.assertFalse(r[k])
        self.assertNotIn('action_result',r);self.assertNotIn('resolved',r)
        self.assertIsNone(r['winner_index'])


if __name__=='__main__':unittest.main()
