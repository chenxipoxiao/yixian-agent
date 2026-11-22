import copy
import unittest

from yixian.combat_hit import resolve_normal_attack_hit, load_hit_contract
from yixian.combat_attack_calculation import prepare_normal_attack
from yixian.combat_initialization import IncompleteCombatState


def players():
    return [{'hp': 20, 'max_hp': 20, 'def': 0, 'raw_buffs': {},
             'attack_context': {'complete': True, 'fate_strategy_ids': [],
                                'xianmo_strategy_ids': [], 'talent_ids': [], 'keyin_type_ids': []},
             'resonance_context': {'selected_id': 0, 'round': 1, 'realm': 1}} for _ in range(2)]


def packet(damage=3, src=0):
    return {'source_index': src, 'target_index': 1-src, 'type': 0, 'damage': damage,
            'skip_wound_check': False, 'hit_def': False, 'feng_rui': 0}


CONTEXT = {'complete': True, 'scene_behavior_present': False, 'default_opponents': [1, 0]}


def run_hit(p=None, damage=3, src=0, **kw):
    return resolve_normal_attack_hit(p if p is not None else players(), packet(damage, src),
                                    effective_card_id=kw.pop('effective_card_id', 0),
                                    battle_context=kw.pop('battle_context', CONTEXT), **kw)


class CombatHitTests(unittest.TestCase):
    def test_plain_hit_counts_actual_loss(self):
        r=run_hit();p=r['candidate_players']
        self.assertTrue(r['hit_resolved']);self.assertEqual(p[1]['hp'],17)
        self.assertEqual(p[0]['raw_buffs'],{'303':1,'302':3})
        self.assertEqual(p[1]['raw_buffs'],{'409':1,'351':3})

    def test_shield_exact_and_partial_absorption(self):
        for defense,expected_hp in [(1,18),(3,20),(8,20)]:
            with self.subTest(defense=defense):
                p=players();p[1]['def']=defense;r=run_hit(p);out=r['candidate_players'][1]
                self.assertEqual(out['hp'],expected_hp);self.assertEqual(out['def'],max(0,defense-3))
                self.assertEqual(out['raw_buffs']['324'],min(3,defense));self.assertEqual(out['raw_buffs']['711'],1)
                self.assertTrue(r['settled_damage_packet']['hit_def'])
                self.assertEqual(r['hp_loss']+r['def_loss'],3)

    def test_zero_damage_no_defense_changes_nothing(self):
        p=players();r=run_hit(p,0);self.assertEqual(r['candidate_players'],p)
        self.assertEqual(r['candidate_events'],[])

    def test_zero_damage_with_defense_sets_flag_without_counter(self):
        p=players();p[1]['def']=4;r=run_hit(p,0)
        self.assertTrue(r['settled_damage_packet']['hit_def']);self.assertEqual(r['candidate_players'],p)

    def test_penetration_consumed_even_without_defense(self):
        p=players();p[0]['raw_buffs']['4']=2;r=run_hit(p)
        self.assertEqual(r['candidate_players'][0]['raw_buffs']['4'],1)

    def test_penetration_consumed_on_zero_packet(self):
        p=players();p[0]['raw_buffs']['4']=1;r=run_hit(p,0)
        self.assertNotIn('4',r['candidate_players'][0]['raw_buffs'])

    def test_310_takes_priority_without_consuming4(self):
        p=players();p[0]['raw_buffs'].update({'310':0,'4':2});p[1]['def']=50;r=run_hit(p)
        self.assertEqual(r['candidate_players'][1]['def'],50);self.assertEqual(r['hp_loss'],3)
        self.assertEqual(r['candidate_players'][0]['raw_buffs']['4'],2)

    def test_nonpositive_penetration_presence(self):
        for value in (0,-1):
            p=players();p[0]['raw_buffs']['4']=value;p[1]['def']=9;r=run_hit(p)
            self.assertEqual(r['hp_loss'],3);self.assertNotIn('4',r['candidate_players'][0]['raw_buffs'])

    def test_huti_consumes_after_defense(self):
        p=players();p[1]['def']=2;p[1]['raw_buffs'].update({'5':2,'745':1});r=run_hit(p)
        self.assertEqual(r['def_loss'],2);self.assertEqual(r['hp_loss'],0)
        self.assertEqual(r['candidate_players'][1]['raw_buffs'],{'5':1,'324':2,'711':1})
        self.assertNotIn('303',r['candidate_players'][0]['raw_buffs'])

    def test_full_defense_does_not_consume_huti(self):
        p=players();p[1]['def']=5;p[1]['raw_buffs'].update({'5':1,'745':1});r=run_hit(p)
        self.assertEqual(r['candidate_players'][1]['raw_buffs']['5'],1)
        self.assertEqual(r['candidate_players'][1]['raw_buffs']['745'],1)

    def test_nonpositive_huti_still_blocks_one_hit(self):
        for value in (0,-5):
            p=players();p[1]['raw_buffs']['5']=value;r=run_hit(p)
            self.assertEqual(r['hp_loss'],0);self.assertNotIn('5',r['candidate_players'][1]['raw_buffs'])

    def test_ignore_huti_does_not_override_wound_entry_check(self):
        p=players();p[0]['raw_buffs']['433']=0;p[1]['raw_buffs']['5']=1;r=run_hit(p)
        self.assertEqual(r['hp_loss'],3);self.assertNotIn('303',r['candidate_players'][0]['raw_buffs'])
        self.assertEqual(r['candidate_players'][0]['raw_buffs']['302'],3)
        self.assertEqual(r['candidate_players'][1]['raw_buffs']['5'],1)

    def test_598_precedes_huti_consumption(self):
        p=players();p[1]['raw_buffs'].update({'598':0,'5':1,'745':1});r=run_hit(p)
        self.assertEqual(r['hp_loss'],0);self.assertEqual(r['candidate_players'],p)

    def test_598_without_huti_still_counts_wound_attempt(self):
        p=players();p[1]['raw_buffs']['598']=1;r=run_hit(p)
        self.assertEqual(r['candidate_players'][0]['raw_buffs'],{'303':1})
        self.assertEqual(r['candidate_players'][1]['hp'],20)

    def test_677_caps_actual_hp_loss_after_shield(self):
        p=players();p[1]['def']=2;p[1]['raw_buffs']['677']=-1;r=run_hit(p,8)
        self.assertEqual((r['def_loss'],r['hp_loss']),(2,1))
        self.assertEqual(r['settled_damage_packet']['damage'],6)
        self.assertEqual(r['candidate_players'][0]['raw_buffs']['302'],1)

    def test_lethal_does_not_clip_overkill(self):
        p=players();p[1]['hp']=2;r=run_hit(p,7)
        self.assertEqual(r['candidate_players'][1]['hp'],-5);self.assertEqual(r['hp_loss'],7)
        self.assertIsNone(r['winner_index']);self.assertTrue(r['target_guard_checked'])

    def test_guard_triggers_inside_hit_and_only_on_target(self):
        p=players();p[0]['hp']=-2;p[0]['raw_buffs']['17']=1;p[1]['hp']=2;p[1]['raw_buffs']['17']=1
        r=run_hit(p,2);out=r['candidate_players']
        self.assertEqual(out[1]['hp'],0);self.assertEqual(out[1]['raw_buffs']['18'],1)
        self.assertNotIn('17',out[1]['raw_buffs']);self.assertIn('17',out[0]['raw_buffs'])
        kinds=[e['event'] for e in r['candidate_events']]
        self.assertLess(kinds.index('hp_loss'),kinds.index('consume17_add18'))
        self.assertEqual(r['candidate_events'][-1]['buff_id'],302)

    def test_queued_revival_defers_guard_without_executing_revival(self):
        for marker in ('430','341','231','429','597','772'):
            p=players();p[1]['hp']=1;p[1]['raw_buffs'].update({marker:0,'17':1});r=run_hit(p)
            self.assertEqual(r['candidate_players'][1]['hp'],-2)
            self.assertTrue(r['revival_pending']);self.assertFalse(r['target_guard_checked'])
            self.assertIn('17',r['candidate_players'][1]['raw_buffs'])

    def test_612_blocks_revival_then_guard_but_not430(self):
        for marker,pending in [('341',False),('430',True)]:
            p=players();p[1]['hp']=1;p[1]['raw_buffs'].update({marker:1,'612':0,'17':1});r=run_hit(p)
            self.assertEqual(r['revival_pending'],pending)
            self.assertEqual('17' in r['candidate_players'][1]['raw_buffs'],pending)

    def test_fully_shielded_hit_does_not_call_guard(self):
        p=players();p[1]['hp']=-2;p[1]['def']=10;p[1]['raw_buffs']['17']=1;r=run_hit(p)
        self.assertFalse(r['target_guard_checked']);self.assertIn('17',r['candidate_players'][1]['raw_buffs'])

    def test_zero_packet_does_not_check_guard(self):
        p=players();p[1]['hp']=0;p[1]['raw_buffs']['17']=1;r=run_hit(p,0)
        self.assertEqual(r['candidate_players'],p)

    def test_present_guard_not_removed_at_next_hit(self):
        p=players();p[1]['hp']=1;p[1]['raw_buffs']['17']=1
        first=run_hit(p);second=run_hit(first['candidate_players'])
        self.assertEqual(second['candidate_players'][1]['hp'],-5)
        self.assertEqual(second['candidate_players'][1]['raw_buffs']['18'],1)

    def test_sides_swap_without_changing_results(self):
        a=run_hit(src=0);b=run_hit(src=1)
        self.assertEqual(a['candidate_players'],b['candidate_players'][::-1])

    def test_prefix_packet_can_feed_hit_without_input_mutation(self):
        p=players();p[1]['def']=1;before=copy.deepcopy(p)
        prefix=prepare_normal_attack(p,actor_index=0,effective_card_id=0,next_card_id=0)
        snapshot=copy.deepcopy(prefix)
        r=resolve_normal_attack_hit(prefix['candidate_players'],prefix['pending_damage_packet'],effective_card_id=0,battle_context=CONTEXT)
        self.assertEqual(r['hp_loss'],2);self.assertEqual(p,before);self.assertEqual(prefix,snapshot)
        self.assertEqual(r['candidate_players'][0]['raw_buffs']['323'],1)

    def test_missing_context_and_unknown_effects_do_not_mutate(self):
        for mutate in (lambda p:p[1].pop('attack_context'),lambda p:p[0].pop('resonance_context'),
                       lambda p:p[1]['attack_context']['talent_ids'].append(64),
                       lambda p:p[0]['raw_buffs'].update({'14':1}),
                       lambda p:p[1]['raw_buffs'].update({'216':1}),
                       lambda p:p[1]['resonance_context'].update(selected_id=48),
                       lambda p:p[1].update(card_config_overrides={'0':{'attack':4}})):
            p=players();mutate(p);before=copy.deepcopy(p);r=run_hit(p)
            self.assertFalse(r['hit_resolved']);self.assertEqual(r['candidate_players'],before)
            self.assertEqual(r['candidate_events'],[]);self.assertEqual(p,before)

    def test_scene_unknown_or_present_is_not_assumed_noop(self):
        for ctx in (None,{},dict(CONTEXT,scene_behavior_present=True),dict(CONTEXT,default_opponents=[0,1]),dict(CONTEXT,default_opponents=[True,False])):
            self.assertFalse(run_hit(battle_context=ctx)['hit_resolved'])

    def test_other_cards_or_packet_types_rejected(self):
        self.assertFalse(run_hit(effective_card_id=1)['hit_resolved'])
        self.assertFalse(run_hit(damage=-1)['hit_resolved'])
        for key,value in [('type',1),('skip_wound_check',True),('hit_def',True),('feng_rui',1)]:
            pkt=packet();pkt[key]=value
            r=resolve_normal_attack_hit(players(),pkt,effective_card_id=0,battle_context=CONTEXT)
            self.assertFalse(r['hit_resolved'])

    def test_no_missing_def_or_max_hp_defaults(self):
        for key in ('def','max_hp'):
            p=players();del p[1][key]
            with self.assertRaises(IncompleteCombatState):run_hit(p)

    def test_bad_numeric_state_rejected(self):
        for key,value in [('def',-1),('max_hp',True),('hp',1_000_001)]:
            p=players();p[1][key]=value
            with self.assertRaises(IncompleteCombatState):run_hit(p)
        with self.assertRaises(IncompleteCombatState):run_hit(src=True)
        with self.assertRaises(IncompleteCombatState):run_hit(game_mode=1)

    def test_over_max_hp_is_out_of_scope(self):
        p=players();p[1]['hp']=21;self.assertFalse(run_hit(p)['hit_resolved'])

    def test_counter_overflow_does_not_mutate_input(self):
        p=players();p[1]['def']=1;p[0]['raw_buffs']['303']=1_000_000;before=copy.deepcopy(p)
        with self.assertRaises(IncompleteCombatState):run_hit(p)
        self.assertEqual(p,before)

    def test_existing_counters_accumulate_and_signed_zero_removal(self):
        p=players();p[0]['raw_buffs'].update({'303':-1,'302':4});p[1]['raw_buffs'].update({'409':2,'351':5})
        r=run_hit(p);a,b=r['candidate_players']
        self.assertNotIn('303',a['raw_buffs']);self.assertEqual(a['raw_buffs']['302'],7)
        self.assertEqual(b['raw_buffs'],{'409':3,'351':8})

    def test_all_outputs_remain_ineligible_for_action_or_labels(self):
        r=run_hit()
        for key in ('state_committed','action_completed','action_phase_reply_available','server_parity_verified','training_label_allowed','settlement_allowed'):
            self.assertFalse(r[key])
        self.assertNotIn('resolved',r);self.assertNotIn('action_result',r)
        self.assertFalse(load_hit_contract()['complete_card_execution_available'])


if __name__ == '__main__':
    unittest.main()
