"""Replay snapshots for flow tests; no inferred cross-perspective identities."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import json
import random

from .season import SeasonCatalog

ROOT = Path(__file__).resolve().parents[1]


def load_rounds(path):
    with Path(path).open(encoding='utf-8') as stream:
        rows = [json.loads(line) for line in stream if line.strip()]
    if not rows:
        raise ValueError('No replay rounds')
    if any(r.get('season_mec') != 10 or r.get('game_mode') != 3 for r in rows):
        raise ValueError('Flow pool requires Hundred Schools ranked records')
    return rows


def build_flow_pool(rows, *, seed=0):
    """Select one human snapshot trajectory from each of eight source games.

    A source replay's anonymous player alias is scoped to that file. We never
    merge aliases across perspectives. Missing future rounds will be carried
    explicitly by the flow runner; the result is not a learned opponent policy.
    """
    levels = json.loads((ROOT/'data/local/2026-11-06/tables/LevelConfig.json').read_text(encoding='utf-8'))
    hp = {r['level']: r['baseMaxHp'] for r in levels}
    tracks = {}
    for row in rows:
        for player in row['players']:
            if player.get('is_ai') is not False or not player.get('player_key'):
                continue
            key = (row['game_id'], player['player_key'])
            track = tracks.setdefault(key, {'id': player['player_key'], 'game_id': row['game_id'],
                'character_id': player['character_id'], 'rounds': {}, 'offers': {}, 'source': row['source'],
                'version': row['source_rules_version'], 'identity_consistent': True})
            if track['character_id'] != player['character_id']:
                track['identity_consistent'] = False
            state = player['start_snapshot']
            if not state.get('board') or state.get('level') not in hp:
                continue
            snapshot = {'cards': state['board'], 'character_id': player['character_id'],
                        'hand_cards': state.get('hand', []), 'is_ai': player.get('is_ai'),
                        'career': player['career'], 'level': state['level'], 'exp': state.get('exp', 0),
                        'life': state.get('destiny'), 'extra_max_hp': state.get('extra_max_hp_modifier', 0),
                        'max_hp': hp[state['level']] + state.get('extra_max_hp_modifier', 0),
                        'fates': state.get('talents', []), 'source_record_id': row['id'],
                        'season_choices': state.get('xian_mo_strategies', []),
                        'talent_counters': state.get('talentTempDatas', {}),
                        'season_temp_datas': player.get('season_snapshot', {}).get('temp_datas', {}),
                        'season_temp_data_timing': 'current_replay_snapshot_not_independently_verified',
                        'snapshot_timing_verified': False}
            for raw, field in (('10023','physique'),('10024','max_physique')):
                if raw in state.get('permanentBuffTempDatas', {}):
                    snapshot[field] = state['permanentBuffTempDatas'][raw]
            track['rounds'][str(row['round'])] = snapshot
            for offer in row['season_candidate_observations']:
                if offer['player_key'] == player['player_key'] and offer['kind'] == 'strategy':
                    # Keep the earliest supplied candidate set; chosen result is
                    # intentionally omitted from the eventual agent request.
                    track['offers'].setdefault(offer['offer_round_id'], offer)
    by_game = defaultdict(list)
    for track in tracks.values():
        if track['identity_consistent'] and '1' in track['rounds'] and len(track['rounds']) >= 8:
            by_game[track['game_id']].append(track)
    if len(by_game) < 8:
        raise ValueError(f'Need eight source games with usable human trajectories; found {len(by_game)}')
    chosen = []
    for game_id in sorted(by_game):
        choices = sorted(by_game[game_id], key=lambda t: (-len(t['rounds']), -len(t['offers']), t['id']))
        chosen.append(choices[0])
    rng = random.Random(seed)
    rng.shuffle(chosen)
    opponents, own_template = chosen[:7], chosen[7]
    catalog = SeasonCatalog.from_local()
    season_offers = {}
    for round_number, offer in sorted(own_template['offers'].items()):
        pending = offer['pending_ids']
        valid = [value for value in pending if value in catalog.strategies and catalog.strategies[value].get('isAvailable') is True]
        pools = {catalog.strategies[value].get('npc') for value in valid}
        skip_ids = [value for value in pending if value not in catalog.strategies]
        if not valid or len(pools) != 1 or len(skip_ids) > 1:
            continue
        item = {'npc_id': pools.pop(), 'candidates': valid + skip_ids,
                'source': own_template['source'], 'source_observed_at_round': offer['observed_at_round'],
                'candidate_generation': 'externally_supplied_replay_snapshot', 'effects_applied': False}
        if skip_ids:
            item['skip_id'] = skip_ids[0]
        season_offers[round_number] = [item]
    return {'opponents': [{key:track[key] for key in ('id','rounds','source','game_id','version')} for track in opponents],
            'self_template': own_template, 'season_offers': season_offers,
            'selection_seed': seed, 'unique_source_games': 8,
            'scope': 'flow_test_opponent_snapshots', 'training_allowed': False,
            'selection_bias': 'Small convenience sample; longest observed trajectory per source game; not population calibrated.'}
