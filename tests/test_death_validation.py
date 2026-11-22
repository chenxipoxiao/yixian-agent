from copy import deepcopy
import unittest

from yixian.death_validation import audit_death_fate_records


def record(fate=65):
    return {'id': 'view1', 'game_id': 'game1', 'round': 11, 'dataset_split': 'test',
            'players': [{'snapshot_slot': 'p1', 'is_ai': False,
                         'start_snapshot': {'talents': [fate], 'talentTempDatas': {str(fate): 1},
                                            'destiny': 2, 'exp': 56, 'hand': [], 'board': []},
                         'after_snapshot': {'talentTempDatas': {str(fate): 0}, 'destiny': 1, 'exp': 55},
                         'private_snapshot': {'hand': [12]}}]}


class DeathValidationTests(unittest.TestCase):
    def test_observable_65_rewards_checked_but_no_claim_raw_damage(self):
        result = audit_death_fate_records([record()], [])
        self.assertEqual(result['observable_mismatches'], 0)
        self.assertEqual(result['observable_checks'], 3)
        self.assertTrue(result['test_split_used_for_diagnosis'])
        self.assertFalse(result['server_damage_reconstructed'])
        self.assertFalse(result['usable_for_policy_training'])

    def test_card_destiny_changes_excluded_without_reverse_engineering_life(self):
        row = record(154)
        row['players'][0]['start_snapshot']['board'] = [10433]
        row['outcome'] = {'recorded_destiny_damage': -15}
        result = audit_death_fate_records([row], [{'id': 10433, 'name': '狸之力',
                                                 'description_preview': '[命元]+6'}])
        self.assertEqual(result['counts_by_effect']['154']['excluded_triggers'], 1)
        self.assertEqual(result['observable_checks'], 0)

    def test_bad_reward_is_reported_not_silently_accepted(self):
        row = record()
        row['players'][0]['after_snapshot']['exp'] = 56
        result = audit_death_fate_records([row], [])
        self.assertEqual(result['observable_mismatches'], 1)

    def test_views_counted_as_views_not_unique_players(self):
        first, second = record(), deepcopy(record())
        second['id'] = 'view2'
        result = audit_death_fate_records([first, second], [])
        self.assertEqual(result['whole_games_seen'], 1)
        self.assertEqual(result['counts_by_effect']['65']['checked_triggers'], 2)
        self.assertTrue(result['counts_are_snapshot_views_not_independent_players'])


if __name__ == '__main__':
    unittest.main()
