"""Bind six audited private-owner prefixes without equating state target and owner.

All other cases delegate to frozen v155. No source field is rewritten.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json

from . import website_battles_v152 as previous
from . import website_battles_v155 as frozen
from .website_battles_v151 import strategy_ids
from .website_battles_v137r2 import normalize_choice_ownership
from .website_battles_v139 import _before, digest

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / 'data/inspection/website-private-owner-v157.json'
CATALOG_SHA = '32bc6cd52f6144d3950025ea99939de8cd6d6b48c6e149fd8b97be96164f8274'
ORIGIN = previous.ORIGIN
UnresolvedBattle = previous.UnresolvedBattle
CONFLICT = 'private_vs_battle_strategy_ownership'


def require(ok, reason):
    if not ok:
        raise UnresolvedBattle('website_private_owner_v157:' + reason)


def extension_contract():
    facts = json.loads(PROOF.read_text(encoding='utf-8'))
    require(facts['catalog24_sha256'] == CATALOG_SHA, 'skip_catalog_contract_changed')
    for path, expected in facts['source_sha256'].items():
        require(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected,
                'evidence_source_changed:' + path)
    return facts


def compiler():
    extension_contract()
    return previous.compiler()


def bind_skip24_receipt(case):
    if case['row']['id'] not in extension_contract()['bindings']:
        return frozen.bind_skip24_receipt(case)
    if CONFLICT not in case['input_conflicts']:
        return case, None
    row, context = case['row'], case['combat_context']
    src = row['source'];path = Path(src['path'])
    require(hashlib.sha256(path.read_bytes()).hexdigest() == src['raw_sha256'], 'source_file_changed')
    rid, owner, before, battle = _before(str(path), src['raw_sha256'], src['step'])
    private = before.get('privatePlayer')
    require(isinstance(private, dict) and private.get('uid') == owner, 'source_private_owner_required')
    entries = private.get('selectedXianMoStrategies')
    private_ids = strategy_ids(entries)
    if 24 not in private_ids:
        return case, None
    extension_contract()
    require(case['input_conflicts'] == [CONFLICT], 'additional_input_conflicts')
    require(len(row['players']) == len(context['players']) == 2, 'two_players_required')
    cp = context['players'][0]
    require(case.get('preparation_owner_verified') is True
            and cp.get('website_hand_unknown') is False, 'verified_private_owner_required')
    require(context.get('game_mode') == 3 and context.get('season_mec') == 10,
            'context_mode_outside_scope')
    require(all(p.get('is_mirror') is False for p in context['players']), 'mirror_not_admitted')
    require(context.get('source_raw_sha256') == src['raw_sha256'], 'context_source_mismatch')
    require(row['id'] == rid + '/round' + str(row['round']) and row['game_id'] == rid
            and before['round'] == battle['round'] == row['round'], 'source_round_mismatch')
    require(before.get('gameMode') == 3 and before.get('seasonMechanic') == 10, 'source_mode_outside_scope')
    binding = extension_contract()['bindings'][row['id']]
    actual = {'source_raw_sha256': src['raw_sha256'], 'source_step': src['step'], 'round': before['round'],
              'source_record_owner_sha256': digest(owner), 'source_state_target_sha256': digest(before.get('targetUid')),
              'private_state_sha256': digest(private), 'prebattle_state_sha256': digest(before)}
    require(actual == binding, 'audited_prefix_binding_mismatch')
    require(isinstance(before.get('targetUid'), str) and before['targetUid'] != owner,
            'expected_distinct_state_target')
    matches = [m for m in battle['matchups']
               if m.get('authoritative') is True and owner in m.get('players', {})]
    require(len(matches) == 1 and len(matches[0]['players']) == 2, 'authoritative_pair_required')
    pair = matches[0]['players'];other = pair[owner].get('opponentUid')
    require(other != owner and other in pair and pair[other].get('opponentUid') == owner,
            'reciprocal_pair_required')
    require(all(p.get('innerDemon') is not True and type(p.get('lifeBefore')) is int
                and p['lifeBefore'] > 0 for p in pair.values()), 'source_mirror_or_zero_life_not_admitted')
    start = row['players'][0]['candidate_start']
    require(row['players'][0]['character_id'] == pair[owner].get('characterId')
            and start['board'] == private.get('deck') == pair[owner].get('deck'), 'source_player_mismatch')
    require(start['level'] == pair[owner].get('phase') and start['exp'] == pair[owner].get('cultivation'),
            'source_start_mismatch')
    require(start['talents'] == strategy_ids(pair[owner].get('talents')), 'ordinary_fates_changed')
    require(isinstance(private.get('hand'), list) and type(cp.get('hand_count')) is int
            and cp['hand_count'] == len(private['hand']), 'source_hand_mismatch')
    battle_ids = strategy_ids(pair[owner].get('xianMoStrategies'))
    require(start['xian_mo_strategies'] == battle_ids, 'battle_ownership_changed')
    require(24 not in battle_ids and 25 not in private_ids, 'only_absent_battle_skip24_supported')
    raw = json.loads(path.read_text(encoding='utf-8'))
    metadata = raw.get('catalog', {}).get('xianMoStrategies', {}).get('24')
    require(isinstance(metadata, dict) and metadata.get('assetKind') == 'xianMoStrategy'
            and metadata.get('id') == 24 and metadata.get('isSkip') is True
            and metadata.get('isSuanniSkip') is True and digest(metadata) == CATALOG_SHA,
            'source_skip_metadata_required')
    chosen = next(e for e in entries if e['id'] == 24)
    require('runtime' in chosen and chosen['runtime'] is None and chosen.get('locked') is False,
            'skip_runtime_unknown')
    history = chosen.get('choiceHistory', {});offers = history.get('offers')
    require(history.get('complete') is True and history.get('selected') == 24
            and type(history.get('roundOrPhase')) is int and 0 < history['roundOrPhase'] <= row['round']
            and isinstance(offers, list) and bool(offers)
            and all(isinstance(group, list) and all(type(x) is int for x in group) for group in offers)
            and any(24 in group for group in offers), 'observed_skip_selection_required')
    require(set(private_ids) - {24} == set(battle_ids), 'remaining_ownership_mismatch')
    receipt = {'origin': ORIGIN, 'source_raw_sha256': src['raw_sha256'], 'source_step': src['step'],
               'case_id': row['id'], 'player_index': 0, 'environment_only': True,
               'battle_strategy_ids': battle_ids, 'private_selected_ids': private_ids,
               'observed_suanni_skip_ids': [24], 'metadata_verified_skip_ids': [24]}
    require(cp.get('website_skip_ownership_v137r2') is None
            or cp['website_skip_ownership_v137r2'] == receipt, 'prefilled_receipt_mismatch')
    projected = deepcopy(case)
    projected['combat_context']['players'][0]['website_skip_ownership_v137r2'] = receipt
    projected = normalize_choice_ownership(projected)
    return projected, {'source_raw_sha256': src['raw_sha256'], 'source_step': src['step'],
        'private_state_sha256': digest(private), 'skip_catalog_sha256': CATALOG_SHA, 'source_skip_id': 24,
        'ordinary_fates_unchanged': True, 'battle_strategy_ids_unchanged': True,
        'obtained_fate_or_reward_replayed': False, 'training_label_allowed': False}


def compile_case(case, view, tables):
    if case['row']['id'] not in extension_contract()['bindings']:
        return frozen.compile_case(case, view, tables)
    projected, receipt = bind_skip24_receipt(case)
    result = previous.compile_case(projected, view, tables)
    if receipt is not None:
        result['website_skip_choice_v157'] = receipt
        result['website_private_owner_v157'] = {'source_binding': extension_contract()['bindings'][case['row']['id']],
            'state_target_rewritten': False, 'opponent_private_state_inferred': False, 'training_label_allowed': False}
    return result
