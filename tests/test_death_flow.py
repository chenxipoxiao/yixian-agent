import unittest
from yixian.effects import EffectEngine
from yixian.match_flow import FlowRules, run_match


def opponents(fate=65):
    return [{'id':f'other-{i}', 'rounds':{r:{'cards':[22], 'level':5, 'exp':56,
             'fates':[fate] if i==0 else [], 'talent_counters':{str(fate):1},
             'hand_cards':[], 'max_physique':96} for r in (1,2)}} for i in range(7)]


def target_loses(left,right,number,seed):
    if number == 1:
        if left['id']=='other-0':return {'winner':1,'life_damage':200}
        if right['id']=='other-0':return {'winner':0,'life_damage':200}
    return {'winner':None}


class DeathFlowTests(unittest.TestCase):
    def test_guard_precedes_death_and_does_not_consume_it(self):
        engine=EffectEngine()
        loser=engine.initialize_player({'life':10,'rerolls':1,'fates':[7,105]},newly_acquired_fates=(7,105))
        result=engine.settle({'rerolls':0},loser,20)
        self.assertEqual(result['life_damage'],0)
        self.assertEqual(result['loser']['effect_state']['death_fate_remaining']['7'],1)

    def test_death_rewards_persist_past_replay_refresh(self):
        result=run_match(opponents(),resolver=target_loses,effect_engine=EffectEngine(),rules=FlowRules(max_rounds=2))
        target=result['players'][1]
        self.assertEqual(target['life'],1)
        self.assertEqual(target['hand_cards'],[12])
        self.assertEqual(target['exp'],59)  # 56 - 1 cost + two round grants.
        self.assertEqual(target['effect_state']['death_fate_remaining']['65'],0)

    def test_unavailable_death_draw_blocks_future_rounds(self):
        result=run_match(opponents(83),resolver=target_loses,effect_engine=EffectEngine(),rules=FlowRules(max_rounds=4))
        self.assertEqual(result['rounds'],1)
        self.assertTrue(result['truncated'])
        self.assertFalse(result['policy_training_allowed'])
        self.assertEqual(result['unresolved_effect_actions'][0]['effect_id'],83)
        self.assertEqual(result['players'][1]['life'],1)
        self.assertEqual(result['players'][1]['exp'],51)
        self.assertEqual(result['players'][1]['hand_cards'],[])

    def test_explicit_validated_draw_provider_resumes_normal_flow(self):
        def draw(request):
            return [{'card_id':i+1,'element':element,'realm':4} for i,element in enumerate(request['elements'])]
        result=run_match(opponents(83),resolver=target_loses,effect_engine=EffectEngine(),
                         rules=FlowRules(max_rounds=2),draw_five_elements=draw)
        self.assertEqual(result['rounds'],2)
        self.assertEqual(result['unresolved_effect_actions'],[])
        self.assertEqual(result['players'][1]['hand_cards'],[1,2,3,4,5])


if __name__=='__main__': unittest.main()
