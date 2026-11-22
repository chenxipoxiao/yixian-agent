"""Original BattleResult preparation projection, never a policy observation.

v5 is already used for flag hand bindings. This v6 stores a separate receipt;
it does not retag the old v21/v77 raw projection or alter previous contexts.
"""
from copy import deepcopy
from .full_battle_v45 import digest_json, snapshot_binding

FIELD = 'original_preparation_v6'
REVIEW_SHA = 'd62ebede259df653ccfa352feb94794b561685a41525dbc113f98d4b018c0bc6'
ENGRAVINGS = {13001, 13003, 13004, 13006, 13007, 13008, 13009, 13013, 13016, 13019}
SWITCHES = {
    'wild_dance_switch': {1002}, 'sound_control_switch': {1003, 1005, 1007},
    'killing_sound_switch': {1006}, 'upgrade_sound_switch': {1009},
}
GRIDS = ENGRAVINGS | {13015, 5001, 5009}
SUPPORTED = GRIDS | {1010} | set.union(*SWITCHES.values())


def require(condition, reason):
    if not condition:
        raise ValueError('original_preparation_v6:' + reason)


def integer_ids(value):
    return (isinstance(value, list) and all(type(x) is int for x in value)
            and len(value) == len(set(value)))


def bind_preparation(turn, source, row, context):
    require(source.get('split') == row.get('split') == 'train', 'training_sources_only')
    require(source['raw_sha256'] == row['source']['raw_sha256'] == context['source_raw_sha256'], 'raw_source')
    require(source['game_id'] == row['game_id'] == context['game_id'], 'game')
    require(turn.get('round') == row['round'], 'round')
    require(FIELD not in context, 'already_bound')
    require(context['game_mode'] == 3 and context['season_mec'] == 10, 'mode')
    receipt = {'schema': FIELD, 'record_id': row['id'], 'game_id': row['game_id'],
        'round': row['round'], 'source_raw_sha256': source['raw_sha256'],
        'archive': source['archive'], 'member': source['member'],
        'source_path': 'RecentBattleInfo.roundStats[round].p1/p2.privateData.xianMoData.tempDatas',
        'reader_review_sha256': REVIEW_SHA, 'snapshot_sha256': snapshot_binding(row, context),
        'environment_only': True, 'policy_observation_allowed': False,
        'counterfactual_reuse_allowed': False, 'players': []}
    for index, slot in enumerate(('p1', 'p2')):
        require(row['players'][index]['snapshot_slot'] == context['players'][index]['snapshot_slot'] == slot, 'seat')
        owner = row['players'][index]['candidate_start']['xian_mo_strategies']
        start = turn[slot]['publicData']['lastRoundData']
        require(integer_ids(owner) and start.get('xianMoStrategies') == owner, 'start_ownership')
        private = turn[slot].get('privateData')
        season = private.get('xianMoData') if isinstance(private, dict) else None
        require(isinstance(season, dict) and isinstance(season.get('tempDatas'), dict), 'complete_map_required')
        selected = season.get('strategies')
        require(isinstance(selected, list) and all(isinstance(v, dict) for v in selected), 'private_ownership_required')
        selected = [v.get('selected') for v in selected]
        require(integer_ids(selected) and set(selected) == set(owner), 'private_ownership_mismatch')
        temp = season['tempDatas']; ids = sorted(SUPPORTED.intersection(owner))
        present = {str(x): deepcopy(temp[str(x)]) for x in ids if str(x) in temp}
        for key, value in present.items():
            require(type(value) is int and -(2**31) <= value < 2**31, 'invalid_value')
            require(int(key) not in GRIDS or 0 <= value < 8, 'invalid_grid')
        receipt['players'].append({'snapshot_slot': slot, 'start_owned_ids': list(owner),
            'selected_strategy_ids': ids, 'present_values': present,
            'absent_keys': sorted(str(x) for x in ids if str(x) not in temp),
            'complete_temp_map_present': True, 'complete_temp_map_sha256': digest_json(temp),
            'private_ownership_matches_start': True})
    result = deepcopy(context); result[FIELD] = receipt
    return result


def validate_receipt(row, context, expected):
    require(isinstance(context, dict) and isinstance(context.get(FIELD), dict), 'receipt_required')
    value = context[FIELD]
    require(digest_json(value) == expected['receipt_sha256'], 'receipt_not_frozen')
    require(value['reader_review_sha256'] == REVIEW_SHA and value['schema'] == FIELD, 'source_contract')
    require(value['record_id'] == row['id'] and value['game_id'] == row['game_id'] == context['game_id']
            and value['round'] == row['round']
            and value['source_raw_sha256'] == row['source']['raw_sha256'] == context['source_raw_sha256'], 'record_binding')
    require(value['snapshot_sha256'] == snapshot_binding(row, context) == expected['snapshot_sha256'], 'start_changed')
    require(row['split'] == 'train' and value['environment_only'] is True
            and value['policy_observation_allowed'] is False and value['counterfactual_reuse_allowed'] is False, 'scope')
    require(len(value['players']) == len(row['players']) == len(context['players']) == 2, 'both_players_required')
    values = []
    for index, player in enumerate(value['players']):
        owner = row['players'][index]['candidate_start']['xian_mo_strategies']
        require(integer_ids(owner) and player['start_owned_ids'] == owner, 'ownership')
        require(player['snapshot_slot'] == row['players'][index]['snapshot_slot']
                == context['players'][index]['snapshot_slot'], 'seat')
        ids = sorted(SUPPORTED.intersection(owner)); present = player['present_values']; absent = player['absent_keys']
        require(player['selected_strategy_ids'] == ids and player['complete_temp_map_present'] is True
                and player['private_ownership_matches_start'] is True, 'complete_owned_map_required')
        require(isinstance(present, dict) and isinstance(absent, list) and absent == sorted(set(absent))
                and not set(present).intersection(absent)
                and set(present).union(absent) == {str(x) for x in ids}, 'key_presence')
        for key, number in present.items():
            require(type(number) is int and -(2**31) <= number < 2**31, 'invalid_value')
            require(int(key) not in GRIDS or 0 <= number < 8, 'invalid_grid')
        values.append({x: present.get(str(x), 0) for x in ids})
    return values


def validate_additions(rows, old, new, selected):
    require(set(old) == set(new), 'record_set')
    stripped = deepcopy(new); admitted = {}
    for row in rows:
        rid = row['id']; ctx = stripped[rid]
        if FIELD not in ctx:
            require(rid not in selected, 'selected_receipt_missing')
            continue
        require(rid in selected and FIELD not in old[rid], 'only_selected_additions')
        receipt = ctx[FIELD]
        expected = {'receipt_sha256': digest_json(receipt), 'snapshot_sha256': receipt['snapshot_sha256']}
        validate_receipt(row, ctx, expected); admitted[rid] = expected
        del ctx[FIELD]
    require(stripped == old and set(admitted) == set(selected), 'other_context_changed')
    return admitted


def project_legacy_inputs(row, context, values):
    """Translate validated v6 data, without manufacturing a v77 source hash."""
    projected = deepcopy(row); ctx = deepcopy(context); ctx.pop(FIELD)
    ashes = [[], []]; disabled = []
    for index, player in enumerate(projected['players']):
        owned = player['candidate_start']['xian_mo_strategies']; cp = ctx['players'][index]
        seat = values[index]
        for field, supported in SWITCHES.items():
            ids = sorted(set(owned) & supported)
            if not ids: continue
            entry = {'origin': 'privateData.xianMoData:preparation_switch',
                'source_raw_sha256': row['source']['raw_sha256'], 'environment_only': True,
                'selected_strategy_ids': ids, 'temp_data': {str(x): seat[x] for x in ids}}
            require(field not in cp or cp[field] == entry, 'legacy_switch_conflict')
            cp[field] = entry
        ids = sorted(set(owned) & ENGRAVINGS)
        if ids:
            entry = {'origin': 'privateData.xianMoData.tempDatas:preparation_grid_selection',
                'selected_strategy_ids': ids, 'slots': {str(x): seat[x] for x in ids}}
            require('season_engraving_input' not in cp or cp['season_engraving_input'] == entry, 'legacy_grid_conflict')
            cp['season_engraving_input'] = entry
        ids = sorted(set(owned) & {5001, 5009})
        if ids:
            entry = {'origin': 'privateData.xianMoData.tempDatas:complete_preparation_grid_map',
                'source_raw_sha256': row['source']['raw_sha256'], 'environment_only': True,
                'selected_strategy_ids': ids, 'temp_data': {str(x): seat[x] for x in ids}}
            require('carefree_grid_input' not in cp or cp['carefree_grid_input'] == entry, 'legacy_carefree_conflict')
            cp['carefree_grid_input'] = entry
        if 1010 in owned:
            require(seat[1010] != 0, 'active1010_not_implemented'); disabled.append(index)
        if 13015 in owned: ashes[index].append({'strategy_id': 13015, 'slot': seat[13015]})
        player['candidate_start']['xian_mo_strategies'] = [x for x in owned if x not in (1010, 13015)]
    return projected, ctx, ashes, disabled
