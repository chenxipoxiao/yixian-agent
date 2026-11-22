from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from yixian.combat_attack_calculation import (
    prepare_normal_attack,load_attack_calculation_contract,EVIDENCE,
)
from yixian.combat_initialization import ROOT,IncompleteCombatState


def players(actor_buffs=None,target_buffs=None):
    return [{'hp':30,'max_hp':40,'def':7,'raw_buffs':dict(buffs or {}),
             'attack_context':{'complete':True,'fate_strategy_ids':[],
                               'xianmo_strategy_ids':[],'talent_ids':[],'keyin_type_ids':[]},
             'resonance_context':{'selected_id':0,'round':13,'realm':4}}
            for buffs in (actor_buffs,target_buffs)]


def calculate(p=None,**kwargs):
    options={'actor_index':0,'effective_card_id':0,'next_card_id':0};options.update(kwargs)
    return prepare_normal_attack(players() if p is None else p,**options)


class AttackCalculationTests(unittest.TestCase):
    def test_contract_is_prefix_only(self):
        c=load_attack_calculation_contract();self.assertEqual(c['base_attack'],3)
        for key in ('full_attack_execution_available','complete_card_execution_available',
                    'server_parity_verified','training_label_allowed','settlement_allowed'):
            self.assertIs(c[key],False)

    def test_modified_evidence_is_rejected(self):
        with TemporaryDirectory() as directory:
            p=Path(directory)/EVIDENCE;p.parent.mkdir(parents=True)
            p.write_bytes((ROOT/EVIDENCE).read_bytes()+b' ')
            with self.assertRaises(ValueError):load_attack_calculation_contract(directory)

    def test_normal_attack_packet_is3_without_hp_loss(self):
        p=players();r=calculate(p)
        self.assertTrue(r['calculation_prepared']);self.assertEqual(r['pending_damage_packet']['damage'],3)
        self.assertEqual(r['pending_damage_packet']['next_handler'],'ApplyDamage')
        self.assertEqual(r['candidate_players'][1]['hp'],30)
        self.assertEqual(r['candidate_players'][1]['def'],7)

    def test_every_attack_prepares_four_ordered_counters(self):
        r=calculate()
        self.assertEqual([(e['player_index'],e['buff_id']) for e in r['candidate_events']],
                         [(0,323),(0,333),(0,493),(1,326)])
        self.assertEqual(r['candidate_players'][0]['raw_buffs'],{'323':1,'333':1,'493':1})
        self.assertEqual(r['candidate_players'][1]['raw_buffs'],{'326':1})

    def test_old_counters_accumulate_without_round_reset(self):
        r=calculate(players({'323':1,'333':2,'493':3},{'326':4}))
        self.assertEqual(r['candidate_players'][0]['raw_buffs'],{'323':2,'333':3,'493':4})
        self.assertEqual(r['candidate_players'][1]['raw_buffs']['326'],5)

    def test_signed_counter_update_matches_nonpositive_removal(self):
        r=calculate(players({'323':-1,'333':-2,'493':0},{'326':0}))
        self.assertEqual(r['candidate_players'][0]['raw_buffs'],{'493':1})
        self.assertEqual(r['candidate_players'][1]['raw_buffs']['326'],1)

    def test_sword_intent_adds_and_records_without_consuming(self):
        r=calculate(players({'6':5,'306':2}))
        self.assertEqual(r['pending_damage_packet']['damage'],8)
        self.assertEqual(r['candidate_players'][0]['raw_buffs']['6'],5)
        self.assertEqual(r['candidate_players'][0]['raw_buffs']['306'],5)

    def test_nonpositive_sword_intent_removes_record_only(self):
        for value in (0,-1):
            r=calculate(players({'6':value,'306':7}))
            self.assertEqual(r['pending_damage_packet']['damage'],3+value)
            self.assertNotIn('306',r['candidate_players'][0]['raw_buffs'])
            self.assertEqual(r['candidate_players'][0]['raw_buffs']['6'],value)

    def test_absent_sword_intent_does_not_clear_prior_record(self):
        r=calculate(players({'306':7}))
        self.assertEqual(r['candidate_players'][0]['raw_buffs']['306'],7)

    def test_additive_components_precede_reduction(self):
        r=calculate(players({'6':5,'212':4,'2':2,'103':6}))
        self.assertEqual(r['arithmetic']['after_additive'],14)
        self.assertEqual(r['pending_damage_packet']['damage'],8)

    def test_reduction_clamps_to_one_without_spending_stacks(self):
        r=calculate(players({'103':100}))
        self.assertEqual(r['pending_damage_packet']['damage'],1)
        self.assertEqual(r['candidate_players'][0]['raw_buffs']['103'],100)

    def test_reduction_is_skipped_when_additive_not_above_one(self):
        for added,expected in [(-2,1),(-3,0),(-5,-2)]:
            r=calculate(players({'2':added,'103':-10}))
            self.assertEqual(r['pending_damage_packet']['damage'],expected)

    def test_iron_bone_uses_fixed_five_not_buff_stacks(self):
        for value in (-1,0,1,9):
            r=calculate(players({'2':10},{'9':value}))
            self.assertEqual(r['pending_damage_packet']['damage'],8)
            self.assertEqual(r['candidate_players'][1]['raw_buffs']['9'],value)

    def test_iron_bone_clamps_before_percent(self):
        r=calculate(players({'101':1},{'9':1,'12':1}))
        self.assertEqual(r['arithmetic']['after_iron_bone9'],1)
        self.assertEqual(r['pending_damage_packet']['damage'],1)

    def test_vulnerability_and_weakness_add_rates(self):
        r=calculate(players({'2':7,'101':3},{'102':2}))
        self.assertEqual(r['arithmetic']['combined_percent'],100)
        self.assertEqual(r['pending_damage_packet']['damage'],10)

    def test_weakness_vulnerability_and_qiandun_combination(self):
        r=calculate(players({'2':7,'101':1},{'102':1,'12':1}))
        self.assertEqual(r['arithmetic']['combined_percent'],60)
        self.assertEqual(r['pending_damage_packet']['damage'],6)

    def test_zero_count_presence_still_activates_percentage_effects(self):
        r=calculate(players({'2':7,'101':0},{'102':0,'12':0}))
        self.assertEqual(r['pending_damage_packet']['damage'],6)

    def test_custom440_rates_use_correct_player(self):
        r=calculate(players({'2':7,'101':1,'440':25},{'102':1,'440':75}))
        self.assertEqual(r['arithmetic']['combined_percent'],150)
        self.assertEqual(r['pending_damage_packet']['damage'],15)

    def test_custom440_without_weakness_or_vulnerability_is_inert(self):
        self.assertEqual(calculate(players({'440':100},{'440':100}))['pending_damage_packet']['damage'],3)

    def test322_presence_suppresses_only_actor_weakness(self):
        r=calculate(players({'2':7,'101':1,'322':0},{'102':1,'12':1}))
        self.assertEqual(r['pending_damage_packet']['damage'],10)
        other=calculate(players({'2':7,'101':1},{'322':1}))
        self.assertEqual(other['pending_damage_packet']['damage'],6)

    def test_positive_attack_truncates_after_combined_percent(self):
        for own,enemy,expected in [({'101':1},{},1),({}, {'102':1},4),
                                   ({'2':4,'101':1},{},4),({'2':4},{'102':1},9)]:
            self.assertEqual(calculate(players(own,enemy))['pending_damage_packet']['damage'],expected)

    def test_negative_multiplier_becomes_zero_then_minimum_one(self):
        r=calculate(players({'101':1,'440':200}))
        self.assertEqual(r['arithmetic']['combined_percent'],0)
        self.assertEqual(r['pending_damage_packet']['damage'],1)

    def test_nonpositive_attack_is_not_forced_to_one_by_percent(self):
        for bonus,expected in [(-3,0),(-4,-1)]:
            r=calculate(players({'2':bonus,'101':1},{'102':1,'12':1}))
            self.assertEqual(r['pending_damage_packet']['damage'],expected)
            self.assertEqual(len(r['candidate_events']),4)

    def test_int32_product_overflow_blocks_without_candidate_costs(self):
        p=players({'2':1_000_000},{'102':1,'440':1_000_000})
        r=calculate(p)
        self.assertFalse(r['calculation_prepared']);self.assertIn('overflow',r['blocked_reason'])
        self.assertEqual(r['candidate_players'],p);self.assertEqual(r['candidate_events'],[])

    def test_missing_context_on_either_side_stays_unknown(self):
        for index in (0,1):
            for key in ('attack_context','resonance_context'):
                p=players();del p[index][key];self.assertFalse(calculate(p)['calculation_prepared'])

    def test_incomplete_context_or_selection_not_silently_zeroed(self):
        for key in ('complete','talent_ids','fate_strategy_ids','xianmo_strategy_ids','keyin_type_ids'):
            p=players();del p[0]['attack_context'][key];self.assertFalse(calculate(p)['calculation_prepared'])
        for index in (0,1):
            p=players();p[index]['resonance_context']['selected_id']=7
            self.assertFalse(calculate(p)['calculation_prepared'])

    def test_nonempty_effect_lists_block_instead_of_ignoring(self):
        for index in (0,1):
            for key in ('talent_ids','fate_strategy_ids','xianmo_strategy_ids','keyin_type_ids'):
                p=players();p[index]['attack_context'][key]=[25]
                r=calculate(p);self.assertFalse(r['calculation_prepared']);self.assertEqual(r['candidate_players'],p)

    def test_unknown_or_out_of_scope_buffs_block_even_at_zero(self):
        for value in (0,1):
            for buff in (3,4,8,16,669,729,999999):
                p=players({str(buff):value});r=calculate(p)
                self.assertFalse(r['calculation_prepared']);self.assertEqual(r['candidate_events'],[])

    def test_other_cards_and_special_adjacent_cards_block(self):
        for card in (16,1000039,2**31-1):
            self.assertFalse(calculate(effective_card_id=card)['calculation_prepared'])
        for card in (10030077,10040077,2**31-1):
            self.assertFalse(calculate(next_card_id=card)['calculation_prepared'])
        self.assertTrue(calculate(next_card_id=16)['calculation_prepared'])

    def test_dynamic_override_blocks(self):
        p=players();p[0]['card_config_overrides']={'attack':100}
        self.assertFalse(calculate(p)['calculation_prepared'])

    def test_invalid_types_modes_and_context_values_reject(self):
        for kwargs in ({'actor_index':True},{'actor_index':2},{'effective_card_id':True},
                       {'next_card_id':None},{'game_mode':1}):
            with self.assertRaises(IncompleteCombatState):calculate(**kwargs)
        p=players();p[0]['attack_context']['talent_ids']=[True]
        with self.assertRaises(IncompleteCombatState):calculate(p)

    def test_unbounded_counter_cannot_produce_invalid_state(self):
        with self.assertRaises(IncompleteCombatState):calculate(players({'323':1_000_000}))

    def test_candidate_is_detached_and_input_never_mutates(self):
        p=players({'6':5});before=deepcopy(p);r=calculate(p)
        self.assertEqual(p,before)
        r['candidate_players'][0]['raw_buffs']['6']=100
        self.assertEqual(p,before)

    def test_right_actor_keeps_fixed_player_slots(self):
        p=players({}, {'2':7});r=calculate(p,actor_index=1)
        self.assertEqual(r['pending_damage_packet']['damage'],10)
        self.assertEqual(r['pending_damage_packet']['source_index'],1)
        self.assertEqual(r['pending_damage_packet']['target_index'],0)
        self.assertEqual(r['candidate_players'][0]['raw_buffs'],{'326':1})

    def test_damage_defense_and_guard_are_left_for_later_handlers(self):
        p=players({'17':1},{'18':1});p[1].update(hp=-3,**{'def':2})
        r=calculate(p)
        self.assertEqual(r['candidate_players'][1]['hp'],-3)
        self.assertEqual(r['candidate_players'][1]['def'],2)
        self.assertEqual(r['candidate_players'][1]['raw_buffs']['18'],1)
        self.assertEqual(r['candidate_players'][0]['raw_buffs']['17'],1)

    def test_no_completed_card_or_training_label_can_be_claimed(self):
        r=calculate()
        for k in ('state_committed','hp_loss_resolved','action_completed','action_phase_reply_available',
                  'server_parity_verified','training_label_allowed','settlement_allowed'):
            self.assertIs(r[k],False)
        self.assertNotIn('resolved',r);self.assertIsNone(r['winner_index'])

    def test_digest_binds_all_inputs(self):
        a=calculate();b=calculate(next_card_id=16)
        c=calculate(players({'2':1}))
        self.assertEqual(a['input_sha256'],calculate()['input_sha256'])
        self.assertEqual(len({a['input_sha256'],b['input_sha256'],c['input_sha256']}),3)


if __name__=='__main__':unittest.main()
