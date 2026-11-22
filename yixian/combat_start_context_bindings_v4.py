"""Original-record paper-opening binding; no new RNG or battle rules."""
from copy import deepcopy
from .full_battle_v45 import digest_json, snapshot_binding


def bind_paper_opening(row, context):
    if row.get('split') != 'train' or row.get('source', {}).get('split') != 'train':
        raise ValueError('Only frozen training-source diagnostics are allowed')
    if context.get('source_raw_sha256') != row['source']['raw_sha256'] or context.get('game_id') != row['game_id']:
        raise ValueError('Original source binding required')
    if 'falling_paper_record' in context or 'typed_parameter_record' in context:
        raise ValueError('Refuse to replace an existing parameter binding')
    owners = []
    for p in row['players']:
        choices = p['candidate_start'].get('xian_mo_strategies')
        if not isinstance(choices, list) or any(type(x) is not int for x in choices) or len(choices) != len(set(choices)):
            raise ValueError('Explicit unique opening ownership required')
        owners.append(16024 in choices)
    if not any(owners): raise ValueError('No paper opening owner')
    stream = context.get('battle_params')
    if not isinstance(stream, list) or not stream or any(type(x) is not int for x in stream):
        raise ValueError('Explicit integer parameter stream required')
    evidence = row.get('battle_params_evidence', {})
    if evidence.get('entries') != len(stream) or evidence.get('sha256') != digest_json(stream):
        raise ValueError('Parameter evidence mismatch')
    result = deepcopy(context)
    result['falling_paper_record'] = {'snapshot_sha256': snapshot_binding(row, context),
                                     'scope': 'unchanged_recorded_battle_only'}
    # The existing compiler still rejects streams containing any additional
    # consumer, invalid branch or unsupported state. Binding does not admit it.
    return result
