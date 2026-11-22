"""Original engraving slots13002/13017, additive over frozen v6/v7 receipts."""
from copy import deepcopy
from . import combat_start_context_bindings_v6 as legacy
from .full_battle_v45 import digest_json, snapshot_binding

FIELD = 'original_engraving_slots_v8'


def require(ok, reason):
    if not ok:
        raise ValueError('original_engraving_slots_v8:' + reason)


def bind_engraving_slots(turn, source, row, context, legacy_expected):
    legacy.validate_receipt(row, context, legacy_expected)
    require(FIELD not in context, 'already_bound')
    require(source.get('split') == row['split'] == 'train', 'training_sources_only')
    require(source['raw_sha256'] == row['source']['raw_sha256'] == context['source_raw_sha256'], 'raw_source')
    require(source['game_id'] == row['game_id'] == context['game_id'], 'game')
    require(turn.get('round') == row['round'], 'round')
    old = context[legacy.FIELD]
    require(source['archive'] == old['archive'] and source['member'] == old['member'], 'member')
    receipt = {'schema': FIELD, 'record_id': row['id'], 'game_id': row['game_id'], 'round': row['round'],
        'source_raw_sha256': source['raw_sha256'], 'archive': source['archive'], 'member': source['member'],
        'snapshot_sha256': snapshot_binding(row, context), 'legacy_receipt_sha256': digest_json(old),
        'reader_review_sha256': legacy.REVIEW_SHA,
        'source_path': 'RecentBattleInfo.roundStats[round].p1/p2.privateData.xianMoData.tempDatas',
        'environment_only': True, 'policy_observation_allowed': False, 'counterfactual_reuse_allowed': False, 'players': []}
    for index, slot in enumerate(('p1', 'p2')):
        owned = row['players'][index]['candidate_start']['xian_mo_strategies']
        require(row['players'][index]['snapshot_slot'] == context['players'][index]['snapshot_slot'] == slot, 'seat')
        require(turn[slot]['publicData']['lastRoundData'].get('xianMoStrategies') == owned, 'start_ownership')
        private = turn[slot].get('privateData'); season = private.get('xianMoData') if isinstance(private, dict) else None
        require(isinstance(season, dict) and isinstance(season.get('tempDatas'), dict), 'complete_map_required')
        selected = season.get('strategies')
        require(isinstance(selected, list) and all(isinstance(x, dict) for x in selected), 'private_ownership_required')
        selected = [x.get('selected') for x in selected]
        require(legacy.integer_ids(selected) and set(selected) == set(owned), 'private_ownership_mismatch')
        temp = season['tempDatas']; temp_hash = digest_json(temp)
        require(temp_hash == old['players'][index]['complete_temp_map_sha256'], 'legacy_map_mismatch')
        ids = sorted({13002,13017}.intersection(owned))
        present = {str(x): temp[str(x)] for x in ids if str(x) in temp}
        require(all(type(v) is int and 0 <= v < 8 for v in present.values()), 'invalid_value')
        receipt['players'].append({'snapshot_slot': slot, 'start_owned_ids': list(owned),
            'selected_strategy_ids': ids, 'present_values': present,
            'absent_keys': [str(x) for x in ids if str(x) not in temp],
            'complete_temp_map_present': True, 'complete_temp_map_sha256': temp_hash,
            'private_ownership_matches_start': True})
    require(any(p['selected_strategy_ids'] for p in receipt['players']), 'owner_required')
    result = deepcopy(context); result[FIELD] = receipt
    return result


def validate_receipt(row, context, expected, legacy_expected):
    require(isinstance(context, dict) and isinstance(context.get(FIELD), dict), 'receipt_required')
    receipt = context[FIELD]
    require(digest_json(receipt) == expected['receipt_sha256'], 'receipt_not_frozen')
    plain = deepcopy(context); del plain[FIELD]
    legacy.validate_receipt(row, plain, legacy_expected)
    old = plain[legacy.FIELD]
    require(receipt['schema'] == FIELD and receipt['reader_review_sha256'] == legacy.REVIEW_SHA, 'source_contract')
    require(receipt['legacy_receipt_sha256'] == digest_json(old) == expected['legacy_receipt_sha256'], 'legacy_receipt_changed')
    require(receipt['record_id'] == row['id'] and receipt['game_id'] == row['game_id'] == context['game_id']
            and receipt['round'] == row['round'] and receipt['source_raw_sha256'] == row['source']['raw_sha256'] == context['source_raw_sha256'], 'record_binding')
    require(receipt['archive'] == old['archive'] and receipt['member'] == old['member'], 'member')
    require(receipt['snapshot_sha256'] == snapshot_binding(row, context) == expected['snapshot_sha256'], 'start_changed')
    require(row['split'] == 'train' and receipt['environment_only'] is True
            and receipt['policy_observation_allowed'] is False and receipt['counterfactual_reuse_allowed'] is False, 'scope')
    require(len(receipt['players']) == 2, 'both_players_required')
    switches = []
    for index, p in enumerate(receipt['players']):
        owned = row['players'][index]['candidate_start']['xian_mo_strategies']; ids = sorted({13002,13017}.intersection(owned))
        require(p['snapshot_slot'] == row['players'][index]['snapshot_slot'] == context['players'][index]['snapshot_slot'], 'seat')
        require(p['start_owned_ids'] == owned and p['selected_strategy_ids'] == ids, 'ownership')
        require(p['complete_temp_map_present'] is True and p['private_ownership_matches_start'] is True
                and p['complete_temp_map_sha256'] == old['players'][index]['complete_temp_map_sha256'], 'complete_map_required')
        present = p['present_values']; absent = p['absent_keys']
        require(isinstance(present, dict) and isinstance(absent, list) and absent == sorted(set(absent))
                and not set(present).intersection(absent) and set(present).union(absent) == {str(x) for x in ids}, 'key_presence')
        require(all(type(v) is int and 0 <= v < 8 for v in present.values()), 'invalid_value')
        switches.append(None if not ids else {'origin': 'privateData.xianMoData.tempDatas:original_engraving_slots',
            'source_raw_sha256': row['source']['raw_sha256'], 'environment_only': True,
            'selected_strategy_ids': ids, 'temp_data': deepcopy(present)})
    require(any(s is not None for s in switches), 'owner_required')
    return plain, switches


def validate_additions(rows, old_contexts, new_contexts, selected, legacy_admitted):
    require(set(old_contexts) == set(new_contexts), 'record_set')
    stripped = deepcopy(new_contexts); admitted = {}
    for row in rows:
        rid = row['id']; ctx = stripped[rid]
        if FIELD not in ctx:
            require(rid not in selected, 'selected_receipt_missing'); continue
        require(rid in selected and FIELD not in old_contexts[rid], 'only_selected_additions')
        receipt = ctx[FIELD]
        expected = {k: receipt[k] for k in ['snapshot_sha256', 'legacy_receipt_sha256']}
        expected['receipt_sha256'] = digest_json(receipt)
        validate_receipt(row, ctx, expected, legacy_admitted[rid]); admitted[rid] = expected
        del ctx[FIELD]
    require(stripped == old_contexts and set(admitted) == set(selected), 'other_context_changed')
    return admitted
