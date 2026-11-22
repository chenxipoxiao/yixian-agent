from copy import deepcopy
import json
import unittest

from yixian.dragon_scale_reward import REMAINING, PENDING, initialize_reward, UnknownDragonScaleReward
from yixian.effects import EffectEngine, UnknownEffectState
from yixian.match_flow import FlowRules, ScriptedFlowAgent, run_match
from yixian.post_battle import begin_post_battle_phase, resolve_post_battle_phase
from test_dragon_scale_reward import catalog


def opponents():
    return [{'id': f'opponent-{i}', 'rounds': {r: {'cards': [101], 'character_id': 1000003,
             'fates': [], 'talent_counters': {}, 'exp': 0} for r in (1, 2, 3)}} for i in range(7)]


def target_loses(target='agent', damage=30):
    def resolver(left, right, *args):
        if target == left['id']:
            return {'winner': 1, 'life_damage': damage}
        if target == right['id']:
            return {'winner': 0, 'life_damage': damage}
        return {'winner': None}
    return resolver


def flow(**kwargs):
    options = dict(rules=FlowRules(initial_life=40, max_rounds=2), self_character_id=1000003,
                   self_cards=[101], self_fates=[27], effect_engine=EffectEngine(),
                   post_battle_card_catalog=catalog(), resolver=target_loses())
    options.update(kwargs)
    fixtures = options.pop('opponents', opponents())
    return run_match(fixtures, **options)


def settled(identifier, cards, life=20):
    player = EffectEngine().initialize_player({'id': identifier, 'character_id': 1000003,
        'fates': [27], 'cards': cards, 'life': life, 'rerolls': 3}, talent_counters={})
    return initialize_reward(player, newly_acquired=True)


class PostBattlePhaseTests(unittest.TestCase):
    def test_pending_can_be_serialized_and_resolved_without_new_damage(self):
        initial = begin_post_battle_phase([settled('a', [15, 16]), settled('b', [101])], battle_id='r1-b1')
        original = deepcopy(initial)
        first = resolve_post_battle_phase(initial, catalog())
        self.assertEqual(initial, original)
        phase = first['phase']
        self.assertFalse(phase['complete_resolution'])
        self.assertEqual([p['life'] for p in phase['players']], [20, 20])
        self.assertEqual(phase['players'][1]['cards'], [10101])
        second = resolve_post_battle_phase(json.loads(json.dumps(phase)), catalog(), selected_slots={'a': 1})
        self.assertTrue(second['phase']['complete_resolution'])
        self.assertEqual(len(second['new_events']), 1)
        self.assertEqual(second['phase']['players'][0]['cards'], [15, 10016])
        self.assertEqual([p['life'] for p in second['phase']['players']], [20, 20])
        retry = resolve_post_battle_phase(second['phase'], catalog(), selected_slots={'a': 1})
        self.assertEqual(retry['phase'], second['phase'])
        self.assertEqual(retry['new_events'], [])
        with self.assertRaises(ValueError):
            resolve_post_battle_phase(second['phase'], catalog(), selected_slots={'a': 0})

    def test_completed_no_candidate_player_is_not_replayed(self):
        phase = begin_post_battle_phase([settled('a', [10101]), settled('b', [15, 16])], battle_id='r1')
        first = resolve_post_battle_phase(phase, catalog())
        self.assertEqual(len(first['new_events']), 1)
        again = resolve_post_battle_phase(first['phase'], catalog())
        self.assertEqual(again['new_events'], [])
        self.assertEqual(again['phase']['players'][0]['effect_state'][REMAINING], 1)

    def test_phase_or_metadata_edits_are_rejected(self):
        phase = begin_post_battle_phase([settled('a', [15, 16]), settled('b', [101])], battle_id='r1')
        phase = resolve_post_battle_phase(phase, catalog())['phase']
        changed = deepcopy(phase); changed['players'][0]['life'] -= 1
        with self.assertRaises(ValueError): resolve_post_battle_phase(changed, catalog())
        cards = catalog(); cards[101]['name'] = 'changed'
        with self.assertRaises(ValueError): resolve_post_battle_phase(phase, cards)

    def test_unknown_and_illegal_random_results_do_not_mutate_phase(self):
        phase = begin_post_battle_phase([settled('a', [15, 16]), settled('b', [101])], battle_id='r1')
        original = deepcopy(phase)
        for choices in ({'absent': 0}, {'a': 2}, {'a': True}):
            with self.assertRaises(ValueError): resolve_post_battle_phase(phase, catalog(), selected_slots=choices)
        self.assertEqual(phase, original)

    def test_unresolved_death_reward_blocks_phase(self):
        actor = settled('a', [101]); actor['effect_state']['death_fate_pending'] = [{'kind': 'draw'}]
        with self.assertRaises(ValueError):
            begin_post_battle_phase([actor, settled('b', [101])], battle_id='r1')


class PostBattleFlowTests(unittest.TestCase):
    def test_cap_then_upgrade_writes_board_once_and_keeps_it_next_round(self):
        seen = []
        class Agent(ScriptedFlowAgent):
            def arrange(self, observation, cards):
                seen.append((observation['round'], list(cards)))
                return cards
        result = flow(agent=Agent(), resolver=target_loses(damage=80))
        self.assertEqual(seen, [(1, [101]), (2, [10101])])
        self.assertEqual(result['players'][0]['life'], 0)
        self.assertEqual(result['players'][0]['effect_state'][REMAINING], 0)
        losses = [e['life_damage'] for e in result['journal'] if e['phase'] == 'settlement']
        self.assertEqual(losses, [20, 20])
        rewards = [x for e in result['journal'] if e['phase'] == 'post_battle_rewards' for x in e['effects']]
        self.assertEqual(len(rewards), 1)
        self.assertFalse(result['policy_training_allowed'])

    def test_winner_also_receives_low_destiny_reward(self):
        def win(left, right, *args):
            if 'agent' not in (left['id'], right['id']): return {'winner': None}
            return {'winner': 0 if left['id'] == 'agent' else 1, 'life_damage': 1}
        result = flow(rules=FlowRules(initial_life=20, max_rounds=1), resolver=win)
        self.assertEqual(result['players'][0]['life'], 20)
        self.assertEqual(result['players'][0]['cards'], [10101])

    def test_missing_randomness_stops_before_growth_and_resumes_only_rewards(self):
        result = flow(self_cards=[15, 16])
        own = result['players'][0]
        self.assertEqual((own['life'], own['exp'], own['cards']), (20, 0, [15, 16]))
        self.assertEqual(result['fully_completed_rounds'], 0)
        self.assertTrue(result['unresolved_effect_actions'])
        self.assertIn(PENDING, own['effect_state'])
        phase = result['pending_post_battle_phase']
        resolved = resolve_post_battle_phase(phase, catalog(), selected_slots={'agent': 1})['phase']
        own_after = next(p for p in resolved['players'] if p['id'] == 'agent')
        self.assertEqual((own_after['life'], own_after['cards']), (20, [15, 10016]))
        self.assertFalse(resolved['contract']['full_match_resume_available'])
        with self.assertRaises(UnknownEffectState):
            EffectEngine().settle(own, own, 10)

    def test_environment_choice_applies_once_and_never_asks_policy(self):
        requests = []
        def environment_choice(request):
            requests.append(deepcopy(request))
            return 1
        result = flow(self_cards=[15, 16], dragon_scale_choice_provider=environment_choice)
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]['candidate_slots'], [0, 1])
        self.assertNotIn('seed', requests[0])
        self.assertEqual(result['players'][0]['cards'], [15, 10016])
        self.assertIsNone(result['pending_post_battle_phase'])

    def test_no_candidates_preserve_charge(self):
        result = flow(self_cards=[10101])
        self.assertEqual(result['players'][0]['effect_state'][REMAINING], 1)
        self.assertEqual(result['players'][0]['cards'], [10101])

    def test_opponent_upgrade_blocks_future_board_overwrite(self):
        fixtures = opponents()
        for state in fixtures[0]['rounds'].values():
            state.update(fates=[27], talent_counters={'27': 1})
        original = deepcopy(fixtures)
        result = flow(opponents=fixtures, self_fates=[], resolver=target_loses('opponent-0'))
        opponent = result['players'][1]
        self.assertEqual(opponent['cards'], [10101])
        self.assertEqual(opponent['life'], 20)
        self.assertEqual(opponent['effect_state'][REMAINING], 0)
        self.assertEqual(result['fully_completed_rounds'], 1)
        self.assertEqual(result['unresolved_effect_actions'][0]['kind'], 'counterfactual_board_continuation_required')
        self.assertFalse(any(e['phase'] == 'opponent_refresh' and e['round'] == 2 for e in result['journal']))
        self.assertEqual(fixtures, original)

    def test_later_replay_counter_cannot_refill_spent_charge(self):
        fixtures = opponents()
        for r, state in fixtures[0]['rounds'].items():
            state.update(fates=[27], talent_counters={'27': 0 if r == 1 else 1})
        result = flow(opponents=fixtures, self_fates=[], resolver=target_loses('opponent-0'))
        self.assertEqual(result['players'][1]['effect_state'][REMAINING], 0)
        self.assertEqual(result['players'][1]['cards'], [101])
        self.assertEqual(result['unresolved_effect_actions'], [])

    def test_acquired_fate_is_initialized_once(self):
        result = flow(self_fates=[], normal_fate_offers={2: [27]},
                      rules=FlowRules(initial_life=40, initial_exp=9, max_rounds=2))
        self.assertEqual(result['players'][0]['cards'], [10101])
        self.assertEqual(result['players'][0]['effect_state'][REMAINING], 0)

    def test_unknown_mirror_or_other_character_is_not_guessed(self):
        for update in ({'talent_counters': {}}, {'is_mirror': True}, {'character_id': 123}):
            fixtures = opponents()
            fixtures[0]['rounds'][1].update(fates=[27], talent_counters={'27': 1})
            fixtures[0]['rounds'][1].update(update)
            with self.assertRaises(UnknownDragonScaleReward):
                flow(opponents=fixtures, self_fates=[])

    def test_unresolved_and_truncated_results_cannot_trigger_rewards_or_damage(self):
        for outcome in ({'winner': None}, {'winner': 0, 'truncated': True}, {'winner': 1, 'terminated': False}):
            result = flow(rules=FlowRules(initial_life=20, max_rounds=1), resolver=lambda *args: outcome)
            self.assertEqual(result['players'][0]['cards'], [101])
            self.assertTrue(all(p['life'] == 20 for p in result['players']))
            self.assertFalse(any(e['phase'] == 'post_battle_rewards' for e in result['journal']))

    def test_pending_death_reward_precedes_upgrade_and_blocks_growth(self):
        result = flow(self_fates=[27, 83], rules=FlowRules(initial_life=20, initial_exp=5, max_rounds=2))
        self.assertEqual(result['players'][0]['life'], 1)
        self.assertEqual(result['players'][0]['cards'], [101])
        self.assertEqual(result['players'][0]['effect_state'][REMAINING], 1)
        self.assertIsNone(result['pending_post_battle_phase'])
        self.assertTrue(result['unresolved_effect_actions'])

    def test_metadata_and_effect_engine_are_explicit_opt_in(self):
        with self.assertRaises(ValueError): flow(effect_engine=None)
        with self.assertRaises(ValueError): flow(post_battle_card_catalog=None, dragon_scale_choice_provider=lambda _: 0)
        result = flow(post_battle_card_catalog=None)
        self.assertFalse(result['post_battle_rewards_enabled'])
        self.assertNotIn(REMAINING, result['players'][0]['effect_state'])
