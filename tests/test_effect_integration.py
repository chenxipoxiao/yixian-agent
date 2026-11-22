from copy import deepcopy
import unittest

from yixian.effects import EffectEngine
from yixian.match_flow import FlowRules, ScriptedFlowAgent, run_match


def opponents(fates=None, season=None):
    return [{'id':f'opponent-{i}', 'rounds':{r:{'cards':[111011], 'level':1, 'exp':0,
             'fates':list(fates or []), 'season_choices':list(season or []),
             'talent_counters':{'105':1}, 'life':100} for r in (1,2)}} for i in range(7)]


class EffectIntegrationTests(unittest.TestCase):
    def test_start_qi_is_temporary_and_policy_can_toggle(self):
        class ToggleAgent(ScriptedFlowAgent):
            def choose_effect_toggles(self, observation, available_effects):
                return [{'effect_id':1001,'enabled':observation['round'] != 2}]
        seen=[]
        def capture(left,right,number,seed):
            if 'agent' in (left['id'],right['id']):
                seen.append((number,left['qi'],right['qi']))
            return {'winner':None}
        result=run_match(opponents(),agent=ToggleAgent(),resolver=capture,effect_engine=EffectEngine(),
                         rules=FlowRules(max_rounds=3),self_season_choices=[1001])
        self.assertEqual(seen,[(1,2,2),(2,0,0),(3,2,2)])
        self.assertNotIn('qi',result['players'][0])

    def test_replay_refresh_cannot_refill_consumed_guard(self):
        fixtures=opponents([105]); original=deepcopy(fixtures)
        def lose_target(left,right,*args):
            if left['id']=='opponent-0':return {'winner':1,'life_damage':20}
            if right['id']=='opponent-0':return {'winner':0,'life_damage':20}
            return {'winner':None}
        result=run_match(fixtures,resolver=lose_target,effect_engine=EffectEngine(),rules=FlowRules(max_rounds=3))
        losses=[e['life_damage'] for e in result['journal'] if e['phase']=='settlement' and e['loser']=='opponent-0']
        self.assertEqual(losses,[0,20,20])
        self.assertEqual(result['players'][1]['effect_state']['talent_105_remaining'],0)
        self.assertEqual(fixtures,original)

    def test_stacked_modifiers_settle_once_and_guard_persists(self):
        def lose_self(left,right,*args):
            if left['id']=='agent':return {'winner':1,'life_damage':33}
            if right['id']=='agent':return {'winner':0,'life_damage':33}
            return {'winner':None}
        result=run_match(opponents(season=[2011]),resolver=lose_self,effect_engine=EffectEngine(),
                         rules=FlowRules(max_rounds=2),self_fates=[45,105])
        losses=[e['life_damage'] for e in result['journal'] if e['phase']=='settlement']
        self.assertEqual(losses,[0,16])
        self.assertEqual(result['players'][0]['life'],84)
        self.assertEqual(result['players'][0]['effect_state']['talent_105_remaining'],0)

    def test_reward_overflow_is_available_before_next_battle_then_cleaned(self):
        def win_self(left,right,*args):
            if left['id']=='agent':return {'winner':0,'life_damage':10}
            if right['id']=='agent':return {'winner':1,'life_damage':10}
            return {'winner':None}
        result=run_match(opponents(),resolver=win_self,effect_engine=EffectEngine(),
                         rules=FlowRules(initial_rerolls=25,max_rounds=2),self_season_choices=[2011])
        starts=[e['resources']['rerolls'] for e in result['journal'] if e['phase']=='self_resources']
        self.assertEqual(starts,[25,26])
        expirations=[e for e in result['journal'] if e['phase']=='reroll_overflow_expired']
        self.assertEqual([(e['round'],e['before'],e['after']) for e in expirations],[(2,26,25)])
        self.assertEqual(result['players'][0]['rerolls'],26)

    def test_recorded_rerolls_cannot_erase_simulated_opponent_rewards(self):
        fixtures=opponents(season=[2011])
        for opponent in fixtures:
            for state in opponent['rounds'].values():state['rerolls']=1
        def target_wins(left,right,*args):
            if left['id']=='opponent-0':return {'winner':0,'life_damage':1}
            if right['id']=='opponent-0':return {'winner':1,'life_damage':1}
            return {'winner':None}
        result=run_match(fixtures,resolver=target_wins,effect_engine=EffectEngine(),rules=FlowRules(max_rounds=2))
        refresh=[e for e in result['journal'] if e['phase']=='opponent_refresh' and e['player']=='opponent-0']
        self.assertEqual(refresh[1]['after']['rerolls'],5)
        self.assertEqual(result['players'][1]['rerolls'],9)
