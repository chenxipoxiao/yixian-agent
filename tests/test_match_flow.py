from copy import deepcopy
import json
import unittest

from yixian.match_flow import FlowRules, ScriptedFlowAgent, run_match


def opponents():
    return [{'id': f'opponent-{i}', 'source': {'kind': 'test_fixture', 'game_id': f'game-{i}'},
             'rounds': {1: {'cards': [101+i, 0], 'character_id': 200+i, 'career': 1,
                            'level': 1, 'exp': i, 'life': 999, 'hand_cards': ['HIDDEN-HAND']},
                        5: {'cards': ['FUTURE-CARD'], 'level': 3, 'exp': 30, 'life': 999}}}
            for i in range(7)]


def unresolved(left, right, round_number, seed):
    return {'winner': None}


class RecordingAgent(ScriptedFlowAgent):
    def __init__(self):
        self.observations = []
        self.season_offers = []

    def choose_profession(self, observation, options):
        self.observations.append(deepcopy(observation))
        return super().choose_profession(observation, options)

    def arrange(self, observation, cards):
        self.observations.append(deepcopy(observation))
        return list(reversed(cards))

    def choose_season(self, observation, offer):
        self.season_offers.append(deepcopy(offer))
        self.observations.append(deepcopy(observation))
        return super().choose_season(observation, offer)


class MatchFlowTests(unittest.TestCase):
    def test_growth_occurs_after_combat_with_health_from_level_table(self):
        observed = []
        def capture(left, right, round_number, seed):
            for player in (left, right):
                if player['id'] == 'agent':
                    observed.append((round_number, player['exp'], player['max_hp'], player['level']))
            return {'winner': None}
        result = run_match(opponents(), rules=FlowRules(max_rounds=3, exp_gain_per_round=6), resolver=capture,
                           self_cards=[1, 2, 0], normal_fate_offers={2: [101, 102]})
        self.assertEqual(observed, [(1, 0, 40, 1), (2, 6, 42, 1), (3, 12, 49, 2)])
        own = result['players'][0]
        self.assertEqual((own['exp'], own['max_hp'], own['rerolls']), (18, 51, 9))
        self.assertEqual(own['fates'], [101])
        phases = [e['phase'] for e in result['journal'] if e['round'] == 3]
        self.assertLess(phases.index('ascend'), phases.index('choose_fate'))
        self.assertLess(phases.index('choose_fate'), phases.index('arrange'))
        self.assertLess(phases.index('settlement_unresolved'), phases.index('round_growth'))

    def test_replay_life_never_overwrites_simulated_damage(self):
        result = run_match(opponents(), rules=FlowRules(max_rounds=4),
                           resolver=lambda *args: {'winner': 0, 'life_damage': 7})
        expected = {p['id']: 100 for p in result['players']}
        for event in result['journal']:
            if event['phase'] == 'opponent_refresh':
                self.assertEqual(event['before']['life'], expected[event['player']])
                self.assertEqual(event['after']['life'], expected[event['player']])
                self.assertEqual(event['recorded_life_ignored'], 999)
            elif event['phase'] == 'settlement':
                expected[event['loser']] -= 7
                self.assertEqual(event['life_after'], expected[event['loser']])
        self.assertEqual({p['id']: p['life'] for p in result['players']}, expected)

    def test_reroll_schedule_grants_next_round_values_and_caps(self):
        rules = FlowRules(initial_rerolls=3, max_rounds=12,
                          reroll_grants_by_round=(3, 1, 2, 2, 3, 3, 3, 3, 3, 4))
        result = run_match(opponents(), rules=rules, resolver=unresolved)
        starts = [e['resources']['rerolls'] for e in result['journal'] if e['phase'] == 'self_resources']
        self.assertEqual(starts[:5], [3, 4, 6, 8, 11])
        self.assertEqual(starts[9:], [25, 25, 25])
        grants = [e['next_round_reroll_grant'] for e in result['journal'] if e['phase'] == 'round_growth']
        self.assertEqual(grants[:4], [1, 2, 2, 3])
        self.assertEqual(grants[8:], [4, 4, 4, 4])

    def test_elimination_and_ranks_finish_an_eight_player_match(self):
        result = run_match(opponents(), rules=FlowRules(max_rounds=10),
                           resolver=lambda *args: {'winner': 0, 'life_damage': 100}, seed=42)
        self.assertTrue(result['terminated'])
        self.assertFalse(result['truncated'])
        self.assertEqual(result['rounds'], 3)
        self.assertEqual(result['battle_count'], 7)
        self.assertEqual(sorted(p['rank'] for p in result['players']), list(range(1, 9)))
        self.assertEqual(sum(p['alive'] for p in result['players']), 1)
        eliminated = set()
        for event in result['journal']:
            if event['phase'] == 'elimination':
                eliminated.add(event['player'])
            elif event['phase'] == 'matchmaking':
                participants = sum(event['pairs'], [])
                self.assertFalse(eliminated.intersection(participants))

    def test_odd_survivors_get_one_bye_without_repeated_pairing(self):
        def one_elimination(left, right, round_number, seed):
            if round_number == 1 and left['id'] == 'opponent-0':
                return {'winner': 1, 'life_damage': 100}
            if round_number == 1 and right['id'] == 'opponent-0':
                return {'winner': 0, 'life_damage': 100}
            return {'winner': None}
        result = run_match(opponents(), resolver=one_elimination, rules=FlowRules(max_rounds=2))
        second = next(e for e in result['journal'] if e['phase'] == 'matchmaking' and e['round'] == 2)
        self.assertEqual(len(second['pairs']), 3)
        self.assertIsNotNone(second['bye'])
        seats = sum(second['pairs'], []) + [second['bye']]
        self.assertEqual(len(seats), len(set(seats)))
        self.assertEqual(len(seats), 7)
        self.assertNotIn('opponent-0', seats)

    def test_player_observation_excludes_hidden_and_future_data(self):
        policy = RecordingAgent()
        seen_battles = []
        def capture(left, right, *args):
            seen_battles.append((left, right))
            return {'winner': None}
        run_match(opponents(), agent=policy, rules=FlowRules(max_rounds=3), resolver=capture, self_cards=[1, 2, 0],
                  season_offers={1: [{'npc_id': 8, 'candidates': [24, 8001, 8002], 'skip_id': 24,
                                      'selected': 8002, 'source': {'future_result': 'SECRET-FUTURE'}}]})
        text = json.dumps(policy.observations + policy.season_offers)
        self.assertNotIn('HIDDEN-HAND', text)
        self.assertNotIn('FUTURE-CARD', text)
        self.assertNotIn('SECRET-FUTURE', text)
        self.assertNotIn('seed', text)
        self.assertNotIn('selected', json.dumps(policy.season_offers))
        self.assertNotIn('FUTURE-CARD', json.dumps(seen_battles))
        self.assertNotIn('HIDDEN-HAND', json.dumps(seen_battles))

    def test_three_external_season_offers_are_requested_without_fake_effects(self):
        result = run_match(opponents(), rules=FlowRules(max_rounds=12), resolver=unresolved,
                           season_offers={r: [{'npc_id': 8, 'candidates': [24, 8001], 'skip_id': 24}]
                                          for r in (1, 9, 12)})
        choices = [e for e in result['journal'] if e['phase'] == 'choose_season']
        self.assertEqual([e['round'] for e in choices], [1, 9, 12])
        self.assertTrue(all(e['receipt']['selected'] == 8001 for e in choices))
        self.assertTrue(all(not e['effects_applied'] and not e['authoritative_confirmation'] for e in choices))
        self.assertLessEqual(result['players'][0]['rerolls'], 25)
        self.assertFalse(result['current_rules_verified'])
        self.assertFalse(result['policy_training_allowed'])

    def test_truncation_does_not_assign_fake_winner_or_survivor_rank(self):
        result = run_match(opponents(), rules=FlowRules(max_rounds=2), resolver=unresolved)
        self.assertTrue(result['truncated'])
        self.assertFalse(result['terminated'])
        self.assertIsNone(result['winner'])
        self.assertTrue(all(p['rank'] is None for p in result['players']))
        self.assertTrue(all(p['life'] == 100 for p in result['players']))

    def test_input_and_seed_are_reproducible_without_mutating_fixtures(self):
        fixtures = opponents()
        copy = deepcopy(fixtures)
        a = run_match(fixtures, seed=19, self_cards=[11, 11, 0])
        b = run_match(fixtures, seed=19, self_cards=[11, 11, 0])
        self.assertEqual(a, b)
        self.assertEqual(fixtures, copy)
        self.assertTrue(a['terminated'])

    def test_invalid_actions_and_resolver_results_fail_explicitly(self):
        class BadAgent(ScriptedFlowAgent):
            def arrange(self, observation, cards):
                return [999]
        with self.assertRaises(ValueError):
            run_match(opponents(), self_cards=[1, 2], agent=BadAgent())
        for invalid in ({}, {'winner': True}, {'winner': 0, 'life_damage': -1}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                run_match(opponents(), resolver=lambda *args: invalid)
        future_only = opponents()
        future_only[0]['rounds'].pop(1)
        with self.assertRaises(ValueError):
            run_match(future_only)


if __name__ == '__main__':
    unittest.main()
