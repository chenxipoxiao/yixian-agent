"""Add explicit start hands to selected environment contexts, without fallback.

This is a replay diagnostic projection, not a policy observation encoder. The
caller must verify member bytes and equality with the frozen v2 projection.
"""
from copy import deepcopy

CONTRACT = 'selected-start-hands-v178-with-dream-echo-no-current-private-fallback'
FIELDS = {'clouds_rain_hand', 'element_flag_hand', 'dream_echo_hand'}


def add_start_hands(turn, source, row, context, requests):
    if source.get('split') != 'train' or row.get('split') != 'train':
        raise ValueError('Only selected training views are allowed')
    if (row.get('source') != source or context.get('source_raw_sha256') != source.get('raw_sha256')
            or context.get('game_id') != source.get('game_id') or row.get('game_id') != source.get('game_id')
            or turn.get('round') != row.get('round')):
        raise ValueError('Start hand source/round binding mismatch')
    if context.get('scope') != 'environment_calibration_only_not_policy_observation':
        raise ValueError('Hands must remain environment-only')
    if not requests or len(requests) != len({(r['player_index'], r['required_field']) for r in requests}):
        raise ValueError('Require unique explicit hand requests')
    result = deepcopy(context)
    for request in requests:
        i, field = request['player_index'], request['required_field']
        if type(i) is not int or i not in (0, 1) or field not in FIELDS:
            raise ValueError('Unsupported hand request')
        if request['record_id'] != row['id'] or request['source_raw_sha256'] != source['raw_sha256']:
            raise ValueError('Request belongs to another source or record')
        if field in result['players'][i]:
            raise ValueError('Refuse to replace an existing hand receipt')
        slot = ('p1', 'p2')[i]
        if row['players'][i]['snapshot_slot'] != slot or result['players'][i]['snapshot_slot'] != slot:
            raise ValueError('Player slot mismatch')
        start = turn[slot]['publicData'].get('lastRoundData')
        if not isinstance(start, dict) or not isinstance(start.get('handCards'), list):
            raise ValueError('Explicit start hand required; no other field is a fallback')
        hand = start['handCards']
        if len(hand) > 256 or any(type(c) is not int for c in hand):
            raise ValueError('Invalid start hand card IDs')
        if len(hand) != context['players'][i]['hand_count']:
            raise ValueError('Start hand count differs from frozen context')
        board = row['players'][i]['candidate_start']['board']
        if start.get('usedCards') != board:
            raise ValueError('Start board differs from frozen row')
        if field == 'dream_echo_hand' and not set(board).intersection({349, 10349}):
            raise ValueError('Dream Echo start-board consumer required')
        result['players'][i][field] = {
            'origin': 'publicData.lastRoundData.handCards',
            'source_raw_sha256': source['raw_sha256'], 'record_id': row['id'],
            'round': row['round'], 'board': deepcopy(board), 'raw_cards': deepcopy(hand),
            'environment_only': True, 'policy_observation': False,
            'training_label_allowed': False, 'projection_contract': CONTRACT,
        }
    return result
