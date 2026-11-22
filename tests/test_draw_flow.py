import unittest
from yixian.match_flow import FlowRules, run_match
from yixian.card_pool import create_pool
from yixian.pool_draw import make_round_draw_provider
from yixian.effects import EffectEngine


def opponents():
    return [{'id':f'p{i}','rounds':{1:{'cards':[],'exp':0,'level':1}}} for i in range(7)]


class DrawFlowTests(unittest.TestCase):
    def test_independent_remaining_pool_drives_actual_round_draws(self):
        metadata=[{'card_id':i,'name':str(i),'family':str(i),'realm':1,'category':category,
                   'copy_count':8,'replace_effect':False} for i,category in ((1,'sect'),(2,'profession'))]
        pool=create_pool(metadata,seed=19)
        provider=make_round_draw_provider(pool,lambda request,obs:{'sect':[1],'profession':[2],'combined_remaining':[1,2]}[request['pool']])
        result=run_match(opponents(),rules=FlowRules(max_rounds=2),
                         resolver=lambda *args:{'winner':None},round_draw_provider=provider)
        self.assertEqual(result['players'][0]['hand_cards'],[1,1,2,1,1,2])
        self.assertEqual(provider.snapshot()['families']['1']['remaining'],4)
        self.assertEqual(provider.snapshot()['families']['2']['remaining'],6)
        self.assertEqual(pool['families']['1']['remaining'],8)

    def test_overflow_conversion_precedes_decisions_and_balances_cultivation(self):
        calls=[]
        def draw(requests,observation):
            calls.append(observation['round'])
            return [22 for request in requests for _ in range(request['count'])]
        result=run_match(opponents(),rules=FlowRules(max_rounds=6),
                         resolver=lambda *args:{'winner':None},round_draw_provider=draw)
        self.assertEqual(calls,[1,2,3,4,5])
        self.assertEqual(len(result['players'][0]['hand_cards']),15)
        self.assertEqual(result['players'][0]['exp'],15)
        own=next(a for a in result['cultivation_accounts'] if a['player']=='agent')
        self.assertTrue(own['balanced'])
        self.assertEqual(own['closing_balance'],15)
        self.assertFalse(own['contains_unreconstructed_replay_actions'])
        gains=[e for e in result['journal'] if e['phase']=='cultivation_change' and e['reason']=='overfull_hand_missed_draws']
        self.assertEqual([(g['round'],g['delta']) for g in gains],[(6,3)])

    def test_missing_provider_does_not_claim_generated_round_cards(self):
        result=run_match(opponents(),rules=FlowRules(max_rounds=1),resolver=lambda *args:{'winner':None})
        grant=next(e for e in result['journal'] if e['phase']=='round_draws')
        self.assertFalse(grant['normal_draws_generated'])

    def test_incomplete_provider_draw_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'resolve every'):
            run_match(opponents(),rules=FlowRules(max_rounds=1),round_draw_provider=lambda *args:[22])

    def test_partial_conversion_still_draws_two_sect_cards_and_debits_pool(self):
        metadata=[{'card_id':i,'name':str(i),'family':str(i),'realm':1,'category':category,
                   'copy_count':8,'replace_effect':False} for i,category in ((1,'sect'),(2,'profession'),(3,'sect'))]
        provider=make_round_draw_provider(create_pool(metadata,seed=19),
                   lambda r,o:{'sect':[1,3],'profession':[2],'combined_remaining':[1,3,2]}[r['pool']])
        # One explicitly granted fixture card shifts the fifth-round boundary
        # to13 cards. It is a pool-neutral grant, not an inferred replay action.
        result=run_match(opponents(),rules=FlowRules(max_rounds=5),self_character_id=1000003,effect_engine=EffectEngine(),
             self_fates=[85],fate_acquisition_card_catalog={15:{'id':15,'owner':1000003,'level':4,
                  'rarity':0,'hidden':True,'obsolete':False}},
             resolver=lambda *args:{'winner':None},round_draw_provider=provider)
        fifth=next(e for e in result['journal'] if e['phase']=='round_draws' and e['round']==5)
        self.assertEqual(fifth['plan']['hand_count_at_draw_boundary'],13)
        self.assertEqual(fifth['plan']['cultivation_gain'],1)
        self.assertEqual([(r['pool'],r['count']) for r in fifth['plan']['draw_requests']],[('sect',2)])
        self.assertEqual(len(fifth['drawn_cards']),2);self.assertTrue(fifth['normal_draws_generated'])
        self.assertEqual(sum(x['remaining'] for x in provider.snapshot()['families'].values()),10)
        self.assertEqual((len(result['players'][0]['hand_cards']),result['players'][0]['exp']),(15,11))
        self.assertTrue(all(a['balanced'] for a in result['cultivation_accounts']))
        self.assertFalse(result['policy_training_allowed'])

    def test_twelfth_round_keeps_first_sect_draw_with_fifteen_card_hand(self):
        calls=[]
        def draw(requests,obs):
            calls.append(obs['round'])
            return [1 for r in requests for _ in range(r['count'])]
        result=run_match(opponents(),rules=FlowRules(max_rounds=12),
                         resolver=lambda *args:{'winner':None},round_draw_provider=draw)
        self.assertEqual(calls,[1,2,3,4,5,12])
        twelfth=next(e for e in result['journal'] if e['phase']=='round_draws' and e['round']==12)
        self.assertEqual(twelfth['plan']['hand_count_at_draw_boundary'],15)
        self.assertEqual([(r['pool'],r['count']) for r in twelfth['plan']['draw_requests']],[('sect',1)])
        self.assertEqual(twelfth['plan']['cultivation_gain'],3)
        self.assertEqual(len(result['players'][0]['hand_cards']),16)

    def test_partial_conversion_without_provider_does_not_claim_remaining_draws(self):
        result=run_match(opponents(),rules=FlowRules(max_rounds=2),
                    resolver=lambda *args:{'winner':None},draw_cards_by_round={1:[1]*13})
        second=next(e for e in result['journal'] if e['phase']=='round_draws' and e['round']==2)
        self.assertEqual(second['plan']['cultivation_gain'],1)
        self.assertEqual(second['plan']['actual_draw_count'],2)
        self.assertFalse(second['normal_draws_generated'])

    def test_explicit_draws_cannot_exceed_partially_remaining_grant(self):
        with self.assertRaisesRegex(ValueError,'overflow-adjusted'):
            run_match(opponents(),rules=FlowRules(max_rounds=2),resolver=lambda *args:{'winner':None},
                      draw_cards_by_round={1:[1]*13,2:[1]*3})


if __name__=='__main__': unittest.main()
