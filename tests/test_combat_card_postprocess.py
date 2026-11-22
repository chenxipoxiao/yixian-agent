import copy
import hashlib
from pathlib import Path
import unittest

from yixian.combat_card_postprocess import (
    BOUNDARY, load_card_postprocess_contract, resolve_normal_card_postprocess)
from yixian.combat_card_cleanup import resolve_normal_card_cleanup, BOUNDARY as OLD_BOUNDARY
from yixian.combat_initialization import IncompleteCombatState


def players():
    return [{'hp': 20, 'max_hp': 20, 'def': 0, 'raw_buffs': {},
             'attack_context': {'complete': True, 'fate_strategy_ids': [],
                                'xianmo_strategy_ids': [], 'talent_ids': [], 'keyin_type_ids': []},
             'resonance_context': {'selected_id': 0, 'round': 1, 'realm': 1}}
            for _ in range(2)]


def run(p=None, **kwargs):
    return resolve_normal_card_postprocess(p if p is not None else players(),
        actor_index=kwargs.pop('actor_index', 0),
        card_item=kwargs.pop('card_item', {'effective_card_id': 0, 'had_used': False}),
        is_temp_card=kwargs.pop('is_temp_card', False),
        checkpoint=kwargs.pop('checkpoint', {'boundary': BOUNDARY, 'earlier_triggers_resolved': True}),
        **kwargs)


class CombatCardPostprocessTests(unittest.TestCase):
    def test_plain_card_clears_chain_and_early_temporary_markers(self):
        p=players();p[0]['raw_buffs']={str(k):2 for k in (337,333,304,395,662)}
        p[0]['raw_buffs']['720']=7
        r=run(p)
        self.assertTrue(r['postprocess_resolved'])
        self.assertEqual(r['candidate_players'][0]['raw_buffs'], {'720':7,'363':1})
        self.assertTrue(r['candidate_card_item']['had_used'])

    def test_category_and_cleanup_removals_are_actor_only(self):
        p=players();p[0]['raw_buffs']={'337':1,'304':4,'6':2,'306':2}
        r=run(p,actor_index=1)
        self.assertEqual(r['candidate_players'][0],p[0])
        self.assertEqual(r['candidate_players'][1]['raw_buffs'],{'363':1})

    def test_present_zero_and_negative_markers_are_removed(self):
        for value in (0,-2):
            p=players();p[0]['raw_buffs']={str(k):value for k in (337,333,304,395,662)}
            self.assertEqual(run(p)['candidate_players'][0]['raw_buffs'],{'363':1})

    def test_temp_card_retains_662_but_still_cleans_other_markers(self):
        p=players();p[0]['raw_buffs']={'662':3,'395':4,'333':2}
        r=run(p,is_temp_card=True)
        self.assertEqual(r['candidate_players'][0]['raw_buffs'],{'662':3,'363':1})
        self.assertTrue(r['candidate_card_item']['had_used'])

    def test_cloud_override_increments_chain_and_total(self):
        p=players();p[0]['raw_buffs']={'338':1,'304':4,'720':9}
        r=run(p);b=r['candidate_players'][0]['raw_buffs']
        self.assertEqual((b['304'],b['720']),(5,10));self.assertNotIn('305',b)
        self.assertTrue(r['classification']['is_yun_jian'])
        self.assertFalse(r['classification']['is_kuang_jian'])

    def test_357_links_cloud_override_to_craze_class(self):
        p=players();p[0]['raw_buffs']={'338':0,'357':0}
        r=run(p);b=r['candidate_players'][0]['raw_buffs']
        self.assertEqual((b['304'],b['720'],b['305']),(1,1,1))
        self.assertTrue(r['classification']['is_kuang_jian'])

    def test_357_alone_does_not_classify_normal_card(self):
        p=players();p[0]['raw_buffs']={'357':1,'304':3}
        r=run(p)
        self.assertFalse(r['classification']['is_yun_jian'])
        self.assertFalse(r['classification']['is_kuang_jian'])
        self.assertNotIn('304',r['candidate_players'][0]['raw_buffs'])

    def test_571_makes_cloud_but_not_craze(self):
        for value in (-1,0,1):
            p=players();p[0]['raw_buffs']={'571':value}
            r=run(p);self.assertTrue(r['classification']['is_yun_jian'])
            self.assertFalse(r['classification']['is_kuang_jian'])
            self.assertEqual(r['candidate_players'][0]['raw_buffs']['720'],1)

    def test_492_category_is_decided_before_consuming_last_charge(self):
        p=players();p[0]['raw_buffs']={'492':1,'504':1}
        r=run(p);b=r['candidate_players'][0]['raw_buffs']
        self.assertEqual(b,{'304':1,'720':1,'305':1,'363':1})
        self.assertTrue(r['classification']['is_yun_jian'])
        self.assertTrue(r['classification']['is_kuang_jian'])

    def test_nested_492_counter_above_charge_only_unwinds_counter(self):
        p=players();p[0]['raw_buffs']={'492':1,'504':2,'304':5}
        r=run(p);b=r['candidate_players'][0]['raw_buffs']
        self.assertEqual(b,{'492':1,'504':1,'363':1})
        self.assertFalse(r['classification']['is_yun_jian'])

    def test_331_is_craze_only_unless_357_links_it(self):
        for linked in (False,True):
            p=players();p[0]['raw_buffs']={'331':2,'546':1,'304':4}
            if linked:p[0]['raw_buffs']['357']=1
            r=run(p);b=r['candidate_players'][0]['raw_buffs']
            self.assertTrue(r['classification']['is_kuang_jian'])
            self.assertEqual(r['classification']['is_yun_jian'],linked)
            self.assertEqual(b['331'],1);self.assertNotIn('546',b)
            self.assertEqual(b.get('304'),5 if linked else None)

    def test_both_charge_families_are_consumed_independently(self):
        p=players();p[0]['raw_buffs']={'492':2,'504':1,'331':3,'546':2}
        b=run(p)['candidate_players'][0]['raw_buffs']
        self.assertEqual((b['492'],b['331'],b['546']),(1,2,1))
        self.assertNotIn('504',b);self.assertEqual(b['305'],1)

    def test_absent_charge_does_not_decrement_or_clear_orphan_counter(self):
        p=players();p[0]['raw_buffs']={'504':2,'546':0}
        b=run(p)['candidate_players'][0]['raw_buffs']
        self.assertEqual(b,{'504':2,'546':0,'363':1})

    def test_signed_charge_counter_matrix_preserves_presence_semantics(self):
        for charge_id,counter_id,cloud in (('492','504',True),('331','546',False)):
            for charge in (-1,0,1,2):
                for count in (None,-1,0,1,2,3):
                    with self.subTest(charge_id=charge_id,charge=charge,count=count):
                        p=players();b=p[0]['raw_buffs'];b[charge_id]=charge
                        if count is not None:b[counter_id]=count
                        r=run(p);out=r['candidate_players'][0]['raw_buffs'];c=0 if count is None else count
                        qualifies=c<=charge
                        self.assertEqual(r['classification']['is_kuang_jian'],qualifies)
                        self.assertEqual(r['classification']['is_yun_jian'],qualifies and cloud)
                        expected_charge=charge-1 if 0<c<=charge else charge
                        if 0<c<=charge and expected_charge<=0:self.assertNotIn(charge_id,out)
                        else:self.assertEqual(out[charge_id],expected_charge)
                        if count is not None and count>1:self.assertEqual(out[counter_id],count-1)
                        else:self.assertNotIn(counter_id,out)

    def test_624_preserves_chain_and_counts_total_even_without_yun_class(self):
        p=players();p[0]['raw_buffs']={'624':1,'304':4,'720':10}
        r=run(p);b=r['candidate_players'][0]['raw_buffs']
        self.assertFalse(r['classification']['is_yun_jian'])
        self.assertEqual(b,{'304':5,'720':11,'363':1})

    def test_cloud_card_does_not_spend_624(self):
        p=players();p[0]['raw_buffs']={'624':2,'338':1}
        b=run(p)['candidate_players'][0]['raw_buffs']
        self.assertEqual(b['624'],2);self.assertEqual(b['304'],1);self.assertEqual(b['720'],1)

    def test_zero_and_negative_624_still_enter_preservation_once(self):
        for value in (0,-3):
            p=players();p[0]['raw_buffs']={'624':value}
            self.assertEqual(run(p)['candidate_players'][0]['raw_buffs'],{'304':1,'720':1,'363':1})

    def test_cumulative720_survives_later_chain_break(self):
        p=players();p[0]['raw_buffs']={'624':1}
        p=run(p)['candidate_players'];out=run(p)['candidate_players'][0]['raw_buffs']
        self.assertEqual(out,{'720':1,'363':2})

    def test_cleanup_suffix_still_retains_then_adds_sword_intent(self):
        p=players();p[0]['raw_buffs']={'492':1,'504':1,'6':7,'306':7,'228':1,
            '307':2,'478':3,'302':5,'303':1,'644':4,'330':237,'382':1,'729':1}
        b=run(p)['candidate_players'][0]['raw_buffs']
        self.assertEqual(b,{'6':12,'644':9,'304':1,'720':1,'305':1,'363':1})

    def test_events_show_category_before_consumption_before_cleanup(self):
        p=players();p[0]['raw_buffs']={'337':1,'333':1,'492':1,'504':1,'6':3,'306':3}
        events=run(p)['candidate_events'];ids=[x.get('buff_id') for x in events]
        self.assertLess(ids.index(337),ids.index(333));self.assertLess(ids.index(333),ids.index(304))
        self.assertLess(ids.index(304),ids.index(720));self.assertLess(ids.index(305),ids.index(492))
        self.assertLess(ids.index(504),ids.index(6));self.assertLess(ids.index(6),ids.index(363))

    def test_rejects_unsupported_interactions_on_either_player_atomically(self):
        for index in (0,1):
            for buff in (232,446,755,502,547,692,482,495,99999):
                p=players();p[0]['raw_buffs']={'337':1,'492':1,'504':1};p[index]['raw_buffs'][str(buff)]=1
                saved=copy.deepcopy(p);r=run(p)
                self.assertFalse(r['postprocess_resolved']);self.assertEqual(r['candidate_players'],saved)
                self.assertEqual(r['candidate_events'],[]);self.assertEqual(p,saved)

    def test_missing_and_nonempty_context_are_not_assumed_empty(self):
        for index in (0,1):
            for key in ('fate_strategy_ids','xianmo_strategy_ids','talent_ids','keyin_type_ids'):
                for missing in (False,True):
                    p=players()
                    if missing:del p[index]['attack_context'][key]
                    else:p[index]['attack_context'][key]=[1]
                    self.assertFalse(run(p)['postprocess_resolved'])
            p=players();p[index]['resonance_context']['selected_id']=10
            self.assertFalse(run(p)['postprocess_resolved'])

    def test_hit_or_old_cleanup_boundary_does_not_establish_entry(self):
        for checkpoint in (None,{}, {'hit_resolved':True},
            {'boundary':OLD_BOUNDARY,'preceding_hooks_resolved':True},
            {'boundary':BOUNDARY,'earlier_triggers_resolved':1}):
            self.assertFalse(run(checkpoint=checkpoint)['postprocess_resolved'])

    def test_dynamic_or_other_card_is_blocked(self):
        for item in ({'effective_card_id':1,'had_used':False},
                     {'effective_card_id':0,'had_used':False,'card_config_overrides':{'name':'云剑'}}):
            self.assertFalse(run(card_item=item)['postprocess_resolved'])
        p=players();p[1]['card_config_overrides']={'attack':100}
        self.assertFalse(run(p)['postprocess_resolved'])

    def test_invalid_mode_actor_and_temp_flag_rejected(self):
        for kwargs in ({'game_mode':4},{'game_mode':True},{'actor_index':2},{'is_temp_card':1}):
            with self.assertRaises(IncompleteCombatState):run(**kwargs)

    def test_counter_overflow_cannot_commit_partial_removals(self):
        p=players();p[0]['raw_buffs']={'337':1,'338':1,'720':1_000_000}
        saved=copy.deepcopy(p)
        with self.assertRaises(IncompleteCombatState):run(p)
        self.assertEqual(p,saved)

    def test_input_is_immutable_and_report_is_candidate_only(self):
        p=players();p[0]['raw_buffs']={'492':1,'504':1,'333':1};saved=copy.deepcopy(p)
        item={'effective_card_id':0,'had_used':False};r=run(p,card_item=item)
        self.assertEqual(p,saved);self.assertFalse(item['had_used'])
        for key in ('state_committed','earlier_triggers_verified_by_this_component','whole_post_card_hook_completed',
                    'action_completed','action_phase_reply_available','server_parity_verified',
                    'training_label_allowed','settlement_allowed'):self.assertIs(r[key],False)
        self.assertIsNone(r['winner_index']);self.assertNotIn('action_result',r)

    def test_old_cleanup_contract_and_scope_stay_frozen(self):
        root=Path(__file__).resolve().parents[1]
        self.assertEqual(hashlib.sha256((root/'yixian/combat_card_cleanup.py').read_bytes()).hexdigest(),
                         '9b439774995344c5b7483cc49eda3dc10097169fffe076df001bb56de4579e85')
        p=players();p[0]['raw_buffs']={'492':1,'504':1}
        old=resolve_normal_card_cleanup(p,actor_index=0,card_item={'effective_card_id':0,'had_used':False},
            checkpoint={'boundary':OLD_BOUNDARY,'preceding_hooks_resolved':True})
        self.assertFalse(old['cleanup_resolved']);self.assertTrue(run(p)['postprocess_resolved'])
        contract=load_card_postprocess_contract()
        self.assertEqual(contract['client_dll_sha256'],contract['prior_cleanup_contract']['client_dll_sha256'])


if __name__ == '__main__':
    unittest.main()
