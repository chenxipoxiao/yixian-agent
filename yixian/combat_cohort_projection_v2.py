"""Train-only combat context projection without post-battle/private fallback.

The caller verifies archive/member bytes. This projection preserves missing
start fields and keeps outcome targets separate from combat inputs.
"""
from copy import deepcopy
from .combat_calibration import project_rounds
from .order_data import VERSION


def start_context(turn, source, data):
    players=[]
    for slot in ('p1','p2'):
        public=turn[slot]['publicData'];start=public.get('lastRoundData')
        if not isinstance(start,dict):raise ValueError('Explicit lastRoundData required')
        hand=start.get('handCards')
        extensions={'origin':'publicData.lastRoundData'}
        for field,key in [('talentDatas','189'),('privateTalentDatas','199')]:
            value=start.get(field)
            extensions[field]=({key:deepcopy(value[key])} if key in value else {}) if isinstance(value,dict) else None
        players.append({'snapshot_slot':slot,'hand_count':len(hand) if isinstance(hand,list) else None,
            'hand_values_are_numeric':isinstance(hand,list) and all(type(x) is int for x in hand),
            'is_mirror':public.get('isMirror'),'public_level':public.get('level'),
            'battle_start_level':start.get('level'),'start_extensions':extensions,
            'source_fields':{'hand_count':'publicData.lastRoundData.handCards.length','is_mirror':'publicData.isMirror',
                'public_level':'publicData.level','start_extensions':'publicData.lastRoundData'}})
    return {'players':players,'battle_params':deepcopy(turn.get('battleParams')),
        'game_mode':data['gameMode'],'season_mec':data['seasonMec'],
        'source_raw_sha256':source['raw_sha256'],'game_id':source['game_id'],
        'scope':'environment_calibration_only_not_policy_observation',
        'projection_contract':'start_only_cohort_v2_no_current_private_fallback'}


def project_record(record,source):
    data=record['data']
    if (data.get('version'),data.get('gameMode'),data.get('seasonMec'))!=(VERSION,3,10):
        raise ValueError('Unsupported version/mode/season')
    rows,_=project_rounds(record,source)
    turns={turn['round']:turn for turn in data['roundStats']}
    if len(turns)!=len(data['roundStats']):raise ValueError('Duplicate round numbers')
    contexts={row['id']:start_context(turns[row['round']],source,data) for row in rows}
    if len(contexts)!=len(rows):raise ValueError('Duplicate projected record IDs')
    return rows,contexts
