from copy import deepcopy
import json
import unittest

from yixian.replays import game_key, normalize_replay


def sample():
    def player(uid):
        return {'publicData': {'uid': uid, 'username': 'private name', 'characterId': 1000001,
                              'career': 1, 'sect': 1, 'isAI': False, 'life': 92, 'exp': 7,
                              'lastRoundData': {'life': 100, 'exp': 6, 'usedCards': [123, 0, 456],
                                                'handCards': [987], 'unlockGrids': 3}},
                'privateData': {'uid': 'do-not-trust-private-uid', 'usedCards': [123, 0, 456, 0, 0, 0, 0, 0],
                                'handCards': [987, 654], 'username': 'do not copy',
                                'talentDatas': {'123': {'count': 2, 'username': 'hidden'}},
                                'xianMoData': {'strategies': [{'id': 1, 'pendings': [8001, 8002, 24], 'selected': 8001}],
                                              'npcDisplayDatas': [{'id': 8, 'round': 1}], 'counters': {'8001': 1}}}}
    return {'code': 1, 'data': {'gameId': 'shared-game', 'uid': 'not-in-battle', 'version': '001.0008.0005',
                              'seasonMec': 10, 'gameMode': 3, 'isDaoXinRank': True,
                              'roundStats': [{'round': 1, 'p1': player('alice'), 'p2': player('bob'),
                                              'winerId': 'bob', 'firstPlayerId': 'alice',
                                              'lifeDamage': -8, 'hpDelta': -23}]}}


class ReplayTests(unittest.TestCase):
    def test_snapshot_times_are_separate_and_destiny_is_not_hp(self):
        result = normalize_replay(sample(), {'artifact': 'fixture.json'})[0]
        p = result['players'][0]
        self.assertEqual(p['start_snapshot']['destiny'], 100)
        self.assertEqual(p['after_snapshot']['destiny'], 92)
        self.assertNotIn('hp', p['start_snapshot'])
        self.assertEqual(p['start_snapshot']['board'], [123, 0, 456])
        self.assertEqual(len(p['private_snapshot']['board']), 8)
        self.assertEqual(p['start_snapshot']['hand'], [987])
        self.assertEqual(p['private_snapshot']['hand'], [987, 654])
        self.assertFalse(result['simulator_input_verified'])
        self.assertFalse(result['policy_observation_verified'])
        self.assertNotIn('battle', result)

    def test_perspective_mismatch_does_not_assign_self_or_unknown_win(self):
        data = sample()
        result = normalize_replay(data, {'artifact': 'fixture.json'})[0]
        self.assertFalse(result['claimed_perspective_present'])
        self.assertEqual(result['outcome']['winner_snapshot_slot'], 'p2')
        self.assertFalse(result['perspective_identity_verified'])
        data['data']['roundStats'][0]['winerId'] = 'stranger'
        result = normalize_replay(data, {'artifact': 'fixture.json'})[0]
        self.assertEqual(result['outcome']['status'], 'unresolved')
        self.assertIsNone(result['outcome']['winner_snapshot_slot'])
        data['data']['roundStats'][0]['p2']['publicData']['uid'] = 'alice'
        data['data']['roundStats'][0]['winerId'] = 'alice'
        self.assertEqual(normalize_replay(data, {'artifact': 'x'})[0]['outcome']['status'], 'unresolved')

    def test_perspectives_group_by_whole_game_not_filename_or_uid(self):
        first = sample()
        second = deepcopy(first)
        second['data']['uid'] = 'bob'
        a = normalize_replay(first, {'artifact': 'p0.json'})[0]
        b = normalize_replay(second, {'artifact': 'p7.json'})[0]
        self.assertEqual(a['game_id'], b['game_id'])
        self.assertNotEqual(a['id'], b['id'])
        self.assertNotEqual(a['players'][0]['player_key'], b['players'][0]['player_key'])
        self.assertEqual(a['players'][0]['player_key_scope'], 'source_replay_record')
        self.assertEqual(a['game_id'], game_key('shared-game'))
        with self.assertRaises(ValueError):
            normalize_replay(first, {'artifact': 'x', 'whole_game_id': game_key('wrong-game')})

    def test_names_cosmetics_and_untrusted_keys_not_projected(self):
        row = normalize_replay(sample(), {'artifact': 'x', 'secret': 'do-not-copy'})[0]
        text = json.dumps(row)
        for secret in ('private name', 'do not copy', 'do-not-trust-private-uid', 'alice', 'bob', 'do-not-copy', 'hidden'):
            self.assertNotIn(secret, text)
        self.assertEqual(row['players'][0]['private_snapshot']['talentDatas'], {'123': {'count': 2}})

    def test_cumulative_season_options_only_emit_first_seen_or_changed(self):
        data = sample()
        first = data['data']['roundStats'][0]
        second = deepcopy(first); second['round'] = 2
        third = deepcopy(first); third['round'] = 3
        third['p1']['privateData']['xianMoData']['strategies'][0]['selected'] = 8002
        data['data']['roundStats'] += [second, third]
        rows = normalize_replay(data, {'artifact': 'x'})
        self.assertEqual([len(r['season_candidate_observations']) for r in rows], [2, 0, 1])
        changed = rows[2]['season_candidate_observations'][0]
        self.assertEqual(changed['pending_ids'], [8001, 8002, 24])
        self.assertEqual(changed['selected_id'], 8002)
        self.assertEqual(changed['observation_kind'], 'changed')
        self.assertEqual(changed['first_seen_at_round'], 1)
        self.assertFalse(changed['pre_action_state_available'])

    def test_unknown_or_out_of_order_source_is_rejected(self):
        data = sample()
        with self.assertRaises(ValueError):
            normalize_replay(data, {})
        with self.assertRaises(ValueError):
            normalize_replay({'data': {}}, {'artifact': 'x'})
        data['data']['roundStats'].append(deepcopy(data['data']['roundStats'][0]))
        with self.assertRaises(ValueError):
            normalize_replay(data, {'artifact': 'x'})


if __name__ == '__main__':
    unittest.main()
