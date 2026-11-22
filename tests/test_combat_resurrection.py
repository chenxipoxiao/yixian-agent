from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from yixian.combat_initialization import ROOT, IncompleteCombatState
from yixian.combat_resurrection import (
    EVIDENCE, can_revive, load_resurrection_contract, resolve_resurrection,
    advance_resurrection_checkpoint,
)
from yixian.combat_action_boundaries import begin_actor_turn, advance_actor_turn, pending_request


def player(hp=10,buffs=None,**extra):
    return dict(hp=hp,max_hp=80,raw_buffs={} if buffs is None else buffs,**extra)


def context(selected=0,round_no=13,realm=4):
    return {'selected_id':selected,'round':round_no,'realm':realm}


def resolve(a,b=None,actor=0):
    return resolve_resurrection([a,player() if b is None else b],actor_index=actor)


def checkpoint(players,actor=0):
    # Explicit software-only turn-start effect fixture; not a replay action.
    s=begin_actor_turn(players,actor_index=actor,sequence_id='synthetic-resurrection-fixture')
    r=pending_request(s)
    return advance_actor_turn(s,{'request_id':r['request_id'],'input_sha256':r['input_sha256'],
                                 'resolved':True,'players':deepcopy(players)})


class ResurrectionTests(unittest.TestCase):
    def test_empty_checkpoint_resolves_without_hp_mutation(self):
        a=player(-2);r=resolve(a)
        self.assertTrue(r['resolved']);self.assertEqual(r['players'][0],a);self.assertEqual(r['events'],[])

    def test_pair_checks_active_actor_before_opponent(self):
        a=player(0,{'341':1},resonance_context=context())
        r=resolve(a,a,actor=1)
        self.assertEqual(r['visited_player_indices'],[1,0]);self.assertEqual([e['player_index'] for e in r['events']],[1,0])
        self.assertEqual([p['hp'] for p in r['players']],[15,15])

    def test_can_revive_exhaustive_marker_presence_precedence(self):
        ids=('430','612','341','231','429','597','772')
        for mask in range(128):
            buffs={v:0 for i,v in enumerate(ids) if mask & (1<<i)}
            for hp in (-1,0,1):
                expected=hp<=0 and (bool(mask&1) or (not mask&2 and bool(mask&124)))
                self.assertEqual(can_revive(player(hp,buffs)),expected,(mask,hp))

    def test_predicate_is_not_executable_effect_certification(self):
        self.assertTrue(can_revive(player(0,{'231':1})))
        self.assertFalse(resolve(player(0,{'231':1}))['resolved'])

    def test430_only_consumes_marker_and_changes_temporary_display(self):
        a=player(-3,{'430':5,'17':1},client_temp_life=20,life=70)
        r=resolve(a);p=r['players'][0]
        self.assertTrue(r['resolved']);self.assertEqual(p['client_temp_life'],15)
        self.assertEqual((p['hp'],p['max_hp'],p['life']),(-3,80,70));self.assertEqual(p['raw_buffs'],{'17':1})
        self.assertFalse(r['events'][0]['authoritative_life_settlement'])

    def test430_zero_and_negative_value_still_consumes(self):
        for value in (0,-3):
            r=resolve(player(0,{'430':value},client_temp_life=10))
            self.assertTrue(r['resolved']);self.assertEqual(r['players'][0]['client_temp_life'],10-value)
            self.assertNotIn('430',r['players'][0]['raw_buffs'])

    def test430_positive_hp_preserves_marker_and_needs_no_temp_context(self):
        a=player(1,{'430':5});r=resolve(a)
        self.assertTrue(r['resolved']);self.assertEqual(r['players'][0],a)

    def test430_missing_display_context_does_not_guess(self):
        a=player(0,{'430':1});r=resolve(a)
        self.assertFalse(r['resolved']);self.assertEqual(r['players'][0],a)
        self.assertEqual(r['blocked_reason'],'missing_client_temp_life_for430')

    def test430_runs_before612_blocker(self):
        a=player(0,{'430':3,'612':0,'341':1},client_temp_life=7)
        r=resolve(a)
        self.assertTrue(r['resolved']);self.assertEqual(r['players'][0]['client_temp_life'],4)
        self.assertEqual(r['players'][0]['raw_buffs'],{'612':0,'341':1});self.assertEqual(r['players'][0]['hp'],0)

    def test341_sets_both_hp_and_max_including_zero_hp(self):
        for hp in (0,-1,-100):
            r=resolve(player(hp,{'341':1},resonance_context=context()))
            self.assertTrue(r['resolved']);p=r['players'][0]
            self.assertEqual((p['hp'],p['max_hp']),(15,15));self.assertNotIn('341',p['raw_buffs'])

    def test341_does_not_fire_while_alive(self):
        a=player(1,{'341':1});r=resolve(a)
        self.assertTrue(r['resolved']);self.assertEqual(r['players'][0],a)

    def test341_consumes_entire_zero_negative_or_multiple_marker(self):
        for value in (0,-1,3):
            r=resolve(player(0,{'341':value},resonance_context=context()))
            self.assertEqual(r['players'][0]['hp'],15);self.assertNotIn('341',r['players'][0]['raw_buffs'])

    def test_resonance48_adds10_from_round13(self):
        for round_no in (13,14):
            r=resolve(player(0,{'341':1},resonance_context=context(48,round_no)))
            self.assertEqual((r['players'][0]['hp'],r['players'][0]['max_hp']),(25,25))
            self.assertEqual(r['events'][0]['resonance48_bonus'],10)

    def test_resonance48_before_effect_round_does_not_add10(self):
        r=resolve(player(0,{'341':1},resonance_context=context(48,12)))
        self.assertEqual(r['players'][0]['hp'],15)

    def test_other_explicit_resonance_does_not_add10(self):
        r=resolve(player(0,{'341':1},resonance_context=context(47)))
        self.assertEqual(r['players'][0]['hp'],15)

    def test_missing_resonance_is_unknown_not_absent(self):
        for ctx in (None,{}, {'selected_id':0}, {'selected_id':48,'round':13}):
            a=player(0,{'341':1},resonance_context=ctx);r=resolve(a)
            self.assertFalse(r['resolved']);self.assertEqual(r['players'][0],a)
            self.assertEqual(r['blocked_reason'],'missing_explicit_resonance_context_for341')

    def test_malformed_resonance_rejected(self):
        for ctx in (context(True),context(48,0),context(48,13,7),context(48,'13')):
            with self.assertRaises(IncompleteCombatState):resolve(player(0,{'341':1},resonance_context=ctx))

    def test_missing_max_hp_blocks341(self):
        a=player(0,{'341':1},resonance_context=context());del a['max_hp']
        r=resolve(a);self.assertFalse(r['resolved']);self.assertEqual(r['players'][0],a)

    def test341_precedes_other_markers_and_preserves_them_when_alive(self):
        buffs={'341':1,'231':2,'429':1,'597':1,'772':1}
        r=resolve(player(0,buffs,resonance_context=context()))
        self.assertTrue(r['resolved']);self.assertEqual(r['players'][0]['raw_buffs'],{k:v for k,v in buffs.items() if k!='341'})

    def test_later_lethal_damage_cannot_reuse_consumed341(self):
        first=resolve(player(0,{'341':1,'231':2},resonance_context=context()))
        later=first['players'][0];later['hp']=-2
        result=resolve(later)
        self.assertFalse(result['resolved']);self.assertEqual(result['blocked_reason'],'unsupported_reached_resurrection_buff:231')

    def test_each_reached_unsupported_marker_blocks(self):
        for buff in ('231','429','597','772'):
            a=player(0,{buff:0});r=resolve(a)
            self.assertFalse(r['resolved']);self.assertEqual(r['players'][0],a)
            self.assertEqual(r['blocked_reason'],'unsupported_reached_resurrection_buff:'+buff)

    def test_unsupported_marker_order_matches_client(self):
        r=resolve(player(0,{'772':1,'429':1,'231':1,'597':1}))
        self.assertEqual(r['blocked_reason'],'unsupported_reached_resurrection_buff:231')

    def test612_suppresses_later_effects_without_missing_context_error(self):
        a=player(0,{'612':-1,'341':1,'231':1});r=resolve(a)
        self.assertTrue(r['resolved']);self.assertEqual(r['players'][0],a);self.assertFalse(can_revive(a))

    def test_opponent_unsupported_effect_rolls_back_actor_mutation(self):
        a=player(0,{'341':1},resonance_context=context());b=player(0,{'231':1})
        r=resolve(a,b)
        self.assertFalse(r['resolved']);self.assertEqual(r['players'],[a,b]);self.assertEqual(r['events'],[])
        self.assertFalse(r['mutations_committed']);self.assertEqual(r['blocked_player_index'],1)

    def test430_is_not_consumed_when_later_resurrection_is_unresolved(self):
        a=player(0,{'430':1,'341':1},client_temp_life=10);r=resolve(a)
        self.assertFalse(r['resolved']);self.assertEqual(r['players'][0],a)

    def test_input_and_output_are_independent(self):
        a=player(0,{'341':1},resonance_context=context(),other={'keep':[1]});old=deepcopy(a)
        r=resolve(a);self.assertEqual(a,old);r['players'][0]['other']['keep'].append(2)
        self.assertEqual(a,old)

    def test_repeat_checkpoint_does_not_reapply_effect(self):
        a=player(0,{'341':1},resonance_context=context());r=resolve(a)
        second=resolve_resurrection(r['players'],actor_index=0)
        self.assertEqual(second['players'],r['players']);self.assertEqual(second['events'],[])

    def test_scope_actor_and_budget_rejected(self):
        for kwargs in ({'actor_index':True},{'actor_index':2},{'actor_index':0,'game_mode':16},
                       {'actor_index':0,'max_passes':0},{'actor_index':0,'max_passes':True}):
            with self.assertRaises(IncompleteCombatState):resolve_resurrection([player(),player()],**kwargs)

    def test_display_overflow_or_wrong_type_rejected_without_input_mutation(self):
        for value in (True,2**31-1):
            a=player(0,{'430':-1},client_temp_life=value);old=deepcopy(a)
            with self.assertRaises(IncompleteCombatState):resolve(a)
            self.assertEqual(a,old)

    def test_resurrection_saves17_before_death_check(self):
        a=player(0,{'341':1,'17':1},resonance_context=context());s=checkpoint([a,player()])
        r=advance_resurrection_checkpoint(s);n=r['state']
        self.assertEqual(n['phase'],'action_execution');self.assertEqual(n['players'][0]['hp'],15)
        self.assertEqual(n['players'][0]['raw_buffs'],{'17':1})
        self.assertEqual(len(r['resurrection']['events']),1)

    def test_absent_resurrection_allows_later17_check(self):
        r=advance_resurrection_checkpoint(checkpoint([player(0,{'17':1}),player()]))
        self.assertEqual(r['state']['players'][0]['raw_buffs'],{'18':1})
        self.assertEqual(r['state']['players'][0]['hp'],0)

    def test612_does_not_suppress_separate_death_guard(self):
        r=advance_resurrection_checkpoint(checkpoint([player(0,{'341':1,'612':1,'17':1}),player()]))
        self.assertEqual(r['state']['players'][0]['raw_buffs'],{'341':1,'612':1,'18':1})

    def test_unresolved_handler_does_not_run_death_check(self):
        s=checkpoint([player(0,{'341':1,'17':1}),player()]);r=advance_resurrection_checkpoint(s)
        self.assertFalse(r['resurrection']['resolved']);self.assertEqual(r['state']['players'],s['players'])
        self.assertEqual(r['state']['phase'],s['phase']);self.assertEqual(r['state']['completed_hooks'],s['completed_hooks'])
        self.assertEqual(pending_request(r['state']),pending_request(s))

    def test_all_five_resurrection_phase_interfaces_accept_handler(self):
        s=checkpoint([player(),player()])
        for phase in ('resurrection_after_turn_start','resurrection_after_successful_action',
                      'resurrection_after_chase_effects','resurrection_before_turn_end','resurrection_after_turn_end'):
            fixture=deepcopy(s);fixture['phase']=phase
            result=advance_resurrection_checkpoint(fixture)
            self.assertTrue(result['resurrection']['resolved']);self.assertEqual(result['state']['completed_hooks'],2)

    def test_non_resurrection_phase_rejected(self):
        s=begin_actor_turn([player(),player()],actor_index=0,sequence_id='fixture')
        with self.assertRaises(IncompleteCombatState):advance_resurrection_checkpoint(s)

    def test_no_training_winner_or_settlement_claim(self):
        for a in (player(0),player(0,{'341':1}),player(0,{'341':1},resonance_context=context())):
            r=resolve(a)
            self.assertFalse(r['training_label_allowed']);self.assertFalse(r['settlement_allowed'])
            self.assertFalse(r['server_parity_verified']);self.assertFalse(r['complete_resurrection_rules'])
            self.assertIsNone(r['winner_index'])

    def test_contract_is_serializable_and_pins_supported_scope(self):
        c=load_resurrection_contract();json.dumps(c,allow_nan=False)
        self.assertEqual(c['implemented_effect_buffs'],[430,612,341])
        self.assertEqual(c['talent139_hp'],15);self.assertEqual(c['resonance48']['bonus_hp'],10)
        self.assertFalse(c['complete_resurrection_rules']);self.assertFalse(c['training_label_allowed'])

    def test_evidence_change_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/EVIDENCE;path.parent.mkdir(parents=True);path.write_text('{}')
            with self.assertRaises(ValueError):load_resurrection_contract(Path(tmp))


if __name__=='__main__':unittest.main()
