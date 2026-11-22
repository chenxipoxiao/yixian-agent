"""Normalize raw replay snapshots as evidence, never as verified agent inputs.

HF replay files contain round snapshots, not every draw/move/swap action. The
archive's claimed perspective can disagree with the players in a round. Player
identities below are snapshot identifiers, not verified seats across perspectives.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib

from .research import canonical_json

SCHEMA_VERSION = 1
SOURCE_FIELDS = ('dataset', 'revision', 'archive', 'archive_sha256', 'member',
                 'raw_sha256', 'artifact')
STATE_SCALARS = {
    'life': 'destiny', 'extraMaxHp': 'extra_max_hp_modifier', 'exp': 'exp',
    'level': 'level', 'unlockGrids': 'unlocked_slots',
    'replaceCardChance': 'rerolls', 'replaceCardChanceLimit': 'reroll_limit',
    'winRoundCount': 'won_rounds', 'loseRoundCount': 'lost_rounds',
    'qiYun': 'qi_yun', 'daoYun': 'dao_yun',
}
STATE_ARRAYS = {
    'usedCards': 'board', 'handCards': 'hand', 'talents': 'talents',
    'usedKeYinCards': 'used_keyin_cards', 'fateStrategies': 'fate_strategies',
    'xianMoStrategies': 'xian_mo_strategies',
}
STATE_MAPS = ('talentTempDatas', 'permanentBuffTempDatas', 'talentDatas',
              'privateTalentDatas', 'FZJXCareers', 'deckCardCount', 'resonanceTalentFlags')
NUMERIC_OBJECT_KEYS = frozenset({'id', 'count', 'counter', 'value', 'level', 'round',
                               'type', 'selected', 'pendings', 'used', 'expire',
                               'effectiveCounter', 'types', 'refreshTalentLevels'})
LIMITATIONS = [
    'Round snapshots are not an action-by-action decision trajectory.',
    'data.uid is a claimed perspective only; p1/p2 are snapshot slots, not stable seats.',
    'lastRoundData is treated as a candidate round-start snapshot based on community documentation, pending game validation.',
    'Public/private current snapshots may contain post-decision or post-battle values.',
    'life is destiny, not combat HP; hpDelta does not establish initial combat HP.',
    'Raw game card IDs, starting combat state and current-season effects are not mapped or verified for yisim.',
    'Cumulative candidate/selection snapshots are evidence only, not behavior-cloning observations.',
]


def game_key(raw_game_id: str) -> str:
    """Group every perspective of the same source game without publishing its ID."""
    if not isinstance(raw_game_id, str) or not raw_game_id.strip():
        raise ValueError('data.gameId must be a nonempty string')
    return 'hf-game-' + hashlib.sha256(raw_game_id.encode('utf-8')).hexdigest()


def _player_key(game_id: str, raw_uid, record_digest: str) -> str | None:
    if not isinstance(raw_uid, str) or not raw_uid:
        return None
    # A record-player-N alias is not proven stable across replay perspectives.
    # Scope it to the source record; only the whole-game group is cross-record.
    payload = canonical_json([game_id, record_digest, raw_uid]).encode('utf-8')
    return 'player-' + hashlib.sha256(payload).hexdigest()


def _numeric_projection(value):
    # Dynamic rule maps are indexed by numeric config IDs. Do not copy arbitrary
    # strings, usernames, cosmetic metadata, URLs or unknown nested fields.
    if type(value) in (int, float, bool) or value is None:
        return value
    if isinstance(value, list):
        return [_numeric_projection(v) for v in value if not isinstance(v, str)]
    if isinstance(value, dict):
        return {k: _numeric_projection(v) for k, v in value.items()
                if isinstance(k, str) and (k.lstrip('-').isdigit() or k in NUMERIC_OBJECT_KEYS)
                and not isinstance(v, str)}
    return None


def _state(snapshot) -> dict:
    if snapshot is None:
        return {}
    if not isinstance(snapshot, dict):
        raise ValueError('A player state snapshot must be an object')
    result = {}
    for raw, normalized in STATE_SCALARS.items():
        if raw in snapshot:
            value = snapshot[raw]
            if type(value) not in (int, float):
                raise ValueError(f'State field {raw} must be numeric')
            result[normalized] = value
    for raw, normalized in STATE_ARRAYS.items():
        if raw in snapshot:
            value = snapshot[raw]
            if not isinstance(value, list) or any(type(v) is not int for v in value):
                raise ValueError(f'State field {raw} must be a list of raw numeric config IDs')
            result[normalized] = list(value)  # 0 is an empty slot, not a missing value.
    for field in STATE_MAPS:
        if field in snapshot:
            result[field] = _numeric_projection(snapshot[field])
    return result


def _candidate_blocks(private_data):
    season = private_data.get('xianMoData', {})
    if not isinstance(season, dict):
        raise ValueError('xianMoData must be an object')
    blocks = season.get('strategies', [])
    if not isinstance(blocks, list):
        raise ValueError('xianMoData.strategies must be an array')
    result = [('strategy', item) for item in blocks]
    if 'suanNiSelectionData' in season:
        result.append(('suanni', season['suanNiSelectionData']))
    return season, result


def _season_observations(private_data, player_key, round_number, cache):
    season, blocks = _candidate_blocks(private_data)
    observations = []
    for kind, raw in blocks:
        if not isinstance(raw, dict) or type(raw.get('id')) is not int:
            raise ValueError('Season candidate blocks need an integer round/event id')
        pending = raw.get('pendings', [])
        if not isinstance(pending, list) or any(type(v) is not int for v in pending):
            raise ValueError('Season pendings must be numeric config IDs')
        selected = raw.get('selected')
        if selected is not None and type(selected) is not int:
            raise ValueError('Season selected ID must be numeric or absent')
        item = {'player_key': player_key, 'kind': kind, 'offer_round_id': raw['id'],
                'pending_ids': list(pending), 'selected_id': selected,
                'selected_in_candidates': selected in pending if selected is not None else False,
                'cumulative_snapshot': True, 'pre_action_state_available': False,
                'policy_observation_verified': False}
        # Do not merge identities absent from a snapshot. Known IDs deduplicate
        # repeated cumulative entries only within this one replay perspective.
        key = (player_key, kind, raw['id']) if player_key else None
        digest = canonical_json(item)
        prior = cache.get(key) if key is not None else None
        if prior is not None and prior['digest'] == digest:
            continue
        item.update({'observed_at_round': round_number,
                     'first_seen_at_round': prior['first_seen'] if prior else round_number,
                     'observation_kind': 'changed' if prior else 'first_seen'})
        observations.append(item)
        if key is not None:
            cache[key] = {'digest': digest, 'first_seen': item['first_seen_at_round']}
    state = {'counters': _numeric_projection(season.get('counters', {})),
             'temp_datas': _numeric_projection(season.get('tempDatas', {})),
             'npc_display_data': []}
    schedule = season.get('npcDisplayDatas', [])
    if not isinstance(schedule, list):
        raise ValueError('npcDisplayDatas must be an array')
    for npc in schedule:
        if not isinstance(npc, dict) or any(type(npc.get(k)) is not int for k in ('id', 'round')):
            raise ValueError('NPC displays need integer id and round')
        state['npc_display_data'].append({'id': npc['id'], 'round': npc['round']})
    return state, observations


def normalize_replay(record: Mapping, source: Mapping) -> list[dict]:
    """Convert a raw replay to per-round research evidence with explicit limits.

    ``source`` requires artifact and can include dataset/revision/archive/member
    and hashes. If supplied, whole_game_id must match game_key(data.gameId).
    This intentionally returns no ``battle`` or ``observation`` key compatible
    with the learner, preventing accidental treatment as calibrated inputs.
    """
    if not isinstance(record, Mapping) or not isinstance(record.get('data'), dict):
        raise ValueError('Replay needs a data object')
    canonical_json(record)
    if not isinstance(source, Mapping) or not isinstance(source.get('artifact'), str) or not source['artifact'].strip():
        raise ValueError('Replay evidence needs source.artifact')
    canonical_json(source)
    data = record['data']
    group = game_key(data.get('gameId'))
    if source.get('whole_game_id', group) != group:
        raise ValueError('Supplied whole_game_id differs from data.gameId')
    version = data.get('version')
    if not isinstance(version, str) or not version:
        raise ValueError('Replay needs its original version string')
    for name in ('seasonMec', 'gameMode'):
        if type(data.get(name)) is not int:
            raise ValueError(f'Replay needs integer {name}')
    rounds = data.get('roundStats')
    if not isinstance(rounds, list):
        raise ValueError('Replay needs roundStats array')
    provenance = {key: deepcopy(source[key]) for key in SOURCE_FIELDS if key in source}
    provenance['whole_game_id'] = group
    replay_digest = hashlib.sha256(canonical_json(record).encode('utf-8')).hexdigest()
    provenance['normalized_input_sha256'] = replay_digest
    claimed_player = _player_key(group, data.get('uid'), replay_digest)
    results, season_cache = [], {}
    previous_round = 0
    for index, raw_round in enumerate(rounds):
        if not isinstance(raw_round, dict) or type(raw_round.get('round')) is not int or raw_round['round'] < 1:
            raise ValueError('Each round snapshot needs a positive integer round')
        number = raw_round['round']
        if number <= previous_round:
            raise ValueError('roundStats must advance in chronological round order')
        previous_round = number
        players, candidates = [], []
        for slot in ('p1', 'p2'):
            raw_player = raw_round.get(slot)
            if not isinstance(raw_player, dict):
                raise ValueError('Each battle snapshot needs p1 and p2 objects')
            public, private = raw_player.get('publicData', {}), raw_player.get('privateData', {})
            if not isinstance(public, dict) or not isinstance(private, dict):
                raise ValueError('publicData/privateData must be objects')
            player_id = _player_key(group, public.get('uid'), replay_digest)
            season_state, newly_seen = _season_observations(private, player_id, number, season_cache)
            candidates.extend(newly_seen)
            player = {'snapshot_slot': slot, 'player_key': player_id,
                      'player_key_scope': 'source_replay_record',
                      'character_id': public.get('characterId'), 'career': public.get('career'),
                      'sect': public.get('sect'), 'is_ai': public.get('isAI'),
                      'start_snapshot': _state(public.get('lastRoundData')),
                      'after_snapshot': _state(public), 'private_snapshot': _state(private),
                      'season_snapshot': season_state,
                      'start_snapshot_timing': 'candidate_round_start_from_community_documentation',
                      'snapshot_timing_verified': False, 'policy_observation_verified': False}
            for key in ('character_id', 'career', 'sect'):
                if player[key] is not None and type(player[key]) is not int:
                    raise ValueError(f'Player {key} must be a numeric configuration id')
            if player['is_ai'] is not None and type(player['is_ai']) is not bool:
                raise ValueError('isAI must be boolean when provided')
            players.append(player)
        identities = [p['player_key'] for p in players]
        unique_identities = all(identities) and len(set(identities)) == 2
        winner = _player_key(group, raw_round.get('winerId'), replay_digest)
        first = _player_key(group, raw_round.get('firstPlayerId'), replay_digest)
        outcome = {'status': 'recorded_winner' if unique_identities and winner in identities else 'unresolved',
                   'winner_player_key': winner, 'first_player_key': first,
                   'winner_snapshot_slot': players[identities.index(winner)]['snapshot_slot']
                   if unique_identities and winner in identities else None,
                   'first_player_snapshot_slot': players[identities.index(first)]['snapshot_slot']
                   if unique_identities and first in identities else None,
                   'simulator_comparison_ready': False}
        for raw, normalized in (('hpDelta', 'recorded_hp_delta'), ('lifeDamage', 'recorded_destiny_damage'),
                                ('huiHeCount', 'recorded_turn_count'), ('battleTime', 'recorded_battle_time')):
            if raw in raw_round:
                if type(raw_round[raw]) not in (int, float):
                    raise ValueError(f'Round result {raw} must be numeric')
                outcome[normalized] = raw_round[raw]
        result = {'schema_version': SCHEMA_VERSION, 'id': f'replay-{replay_digest}-round-{index}',
                  'evidence': 'real_game', 'provenance_verified': False, 'source': deepcopy(provenance),
                  'game_id': group, 'source_rules_version': version,
                  'season_mec': data['seasonMec'], 'game_mode': data['gameMode'],
                  'is_dao_xin_rank': data.get('isDaoXinRank'), 'round': number,
                  'claimed_perspective_player_key': claimed_player,
                  'claimed_perspective_present': bool(claimed_player and claimed_player in identities),
                  'perspective_identity_verified': False, 'players': players, 'outcome': outcome,
                  'season_candidate_observations': candidates,
                  'simulator_input_verified': False, 'policy_observation_verified': False,
                  'scope': 'raw_replay_snapshot_evidence_only', 'limitations': list(LIMITATIONS)}
        for raw, normalized in (('beginTs', 'begin_ts'), ('endTs', 'end_ts')):
            if raw in data and type(data[raw]) is int:
                result[normalized] = data[raw]
        canonical_json(result)
        results.append(result)
    return results
