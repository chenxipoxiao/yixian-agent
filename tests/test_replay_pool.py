import unittest
from unittest.mock import patch
from types import SimpleNamespace
from yixian.replay_pool import build_flow_pool


def sample_rows(games=8):
    return [{'game_id':f'g{game}', 'round':number, 'source_rules_version':'v1',
             'source':{'artifact':f'view-{game}.json'}, 'id':f'g{game}-r{number}',
             'season_candidate_observations':[], 'players':[{
                'player_key':f'actor-{game}', 'is_ai':False, 'character_id':1, 'career':1,
                'start_snapshot':{'board':[10,0,20], 'level':1, 'exp':number, 'extra_max_hp_modifier':6,
                                  'destiny':40, 'hand':[99999], 'talents':[1]},
                'private_snapshot':{'hand':[77777]}}]}
            for game in range(games) for number in range(1,9)]


class ReplayPoolTests(unittest.TestCase):
    def test_one_source_game_each_and_correct_health_field(self):
        with patch('pathlib.Path.read_text', return_value='[{"level":1,"baseMaxHp":40}]'), \
             patch('yixian.replay_pool.SeasonCatalog.from_local', return_value=SimpleNamespace(strategies={})):
            pool=build_flow_pool(sample_rows(),seed=19)
        self.assertEqual(len(pool['opponents']),7)
        self.assertEqual(len({x['game_id'] for x in pool['opponents']}),7)
        self.assertNotIn(pool['self_template']['game_id'], {x['game_id'] for x in pool['opponents']})
        state=pool['opponents'][0]['rounds']['1']
        self.assertEqual(state['extra_max_hp'],6)
        self.assertEqual(state['cards'],[10,0,20])
        self.assertNotIn('hand',state)
        self.assertNotIn('private_snapshot',state)

    def test_insufficient_independent_games_rejected(self):
        with patch('pathlib.Path.read_text', return_value='[{"level":1,"baseMaxHp":40}]'):
            with self.assertRaises(ValueError):
                build_flow_pool(sample_rows(7))
