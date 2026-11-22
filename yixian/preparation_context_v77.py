"""Bound evidence for present preparation maps; missing source maps stay unknown."""
from copy import deepcopy

FIELD = 'preparation_map_v77'
ORIGIN = 'privateData.xianMoData.tempDatas:complete_preparation_map_projection'
SUPPORTED = {1010, 13007, 13015, 13016}
PROJECTION_SHA = 'e3a1bae42f3e06d3463db29e08bd2e3ce1484c00847ae3aa95f4c103af185a4d'


def required_ids(owner, previous_player):
    choices = owner['candidate_start']['xian_mo_strategies']
    slots = previous_player.get('season_engraving_input', {}).get('slots', {})
    return sorted(x for x in SUPPORTED.intersection(choices)
                  if x in (1010, 13015) or str(x) not in slots)


def validate_entry(row, index, value, expected):
    keys = {'origin', 'selected_strategy_ids', 'present_values', 'absent_keys',
            'complete_temp_map_present', 'source_projection_sha256',
            'source_raw_sha256', 'environment_only', 'record_id', 'round', 'snapshot_slot'}
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError('preparation_v77:explicit_projection_required')
    owner = row['players'][index]
    if (value['origin'] != ORIGIN or value['complete_temp_map_present'] is not True
            or value['environment_only'] is not True
            or value['source_projection_sha256'] != PROJECTION_SHA
            or value['source_raw_sha256'] != row['source']['raw_sha256']
            or value['record_id'] != row['id'] or value['round'] != row['round']
            or value['snapshot_slot'] != owner['snapshot_slot']):
        raise ValueError('preparation_v77:unbound_or_incomplete_source')
    ids = value['selected_strategy_ids']
    if not expected or ids != expected or any(type(x) is not int for x in ids):
        raise ValueError('preparation_v77:ownership_mismatch')
    present, absent = value['present_values'], value['absent_keys']
    if (not isinstance(present, dict) or not isinstance(absent, list)
            or any(type(x) is not str for x in absent)
            or sorted(set(absent)) != absent
            or set(present) & set(absent)
            or set(present) | set(absent) != {str(x) for x in ids}):
        raise ValueError('preparation_v77:incomplete_key_presence')
    for key, v in present.items():
        if type(v) is not int or not -(2**31) <= v < 2**31:
            raise ValueError('preparation_v77:invalid_value')
        if key != '1010' and not 0 <= v < 8:
            raise ValueError('preparation_v77:invalid_grid')
    # Only after validating an explicitly present complete map may the client
    # GetFuMoGrid / IsSwitchActive missing-key path supply its documented zero.
    return {int(k): present[k] if k in present else 0 for k in map(str, ids)}


def validate_additions(rows, old, new, selected):
    if set(old) != set(new):
        raise ValueError('Context record set changed')
    projected = deepcopy(new)
    added = []
    for row in rows:
        rid = row['id']
        if not isinstance(projected[rid].get('players'), list) or len(projected[rid]['players']) != 2:
            raise ValueError('Both context players required')
        for i, player in enumerate(projected[rid]['players']):
            if FIELD not in player:
                continue
            if FIELD in old[rid]['players'][i] or rid not in selected:
                raise ValueError('Only new targeted preparation entries allowed')
            value = player.pop(FIELD)
            if projected[rid].get('engraving_source_projection_sha256') != PROJECTION_SHA:
                raise ValueError('Preparation projection source changed')
            validate_entry(row, i, value, required_ids(row['players'][i], old[rid]['players'][i]))
            added.append({'record_id': rid, 'player_index': i})
    if projected != old or not added:
        raise ValueError('Only additive bound preparation_map_v77 is allowed')
    return added
