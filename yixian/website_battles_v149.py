"""Bind owner1009 to the exact website preparation switch.

Only the input boundary is extended. The existing shared tail upgrade and
combat scheduler stay frozen; opponent private values are never inferred.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json

from . import website_battles_v147 as previous
from .website_battles_v139 import _before, digest
from .website_battles_v132 import replace_function
from .combat_compiler_view_v81 import compiler_modules

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / 'data/inspection/website-owner-upgrade-sound-v149.json'
PROOF_SHA = '24c516b29463457c7efeb4f6d8c12758459b19a4cb880a2a6c047a9e0fbf8d6c'
ORIGIN = previous.ORIGIN
UnresolvedBattle = previous.UnresolvedBattle


def require(ok, reason):
    if not ok:
        raise UnresolvedBattle('website_upgrade_v149:' + reason)


def extension_contract():
    require(hashlib.sha256(PROOF.read_bytes()).hexdigest() == PROOF_SHA,
            'evidence_changed')
    facts = json.loads(PROOF.read_text(encoding='utf-8'))
    for path, expected in facts['source_sha256'].items():
        require(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected,
                'evidence_source_changed:' + path)
    return facts


def compiler():
    extension_contract()
    view = previous.compiler()
    target = compiler_modules(view)['yixian.full_battle_v41']
    replace_function(target, 'compile_start', [
        ('privateData.xianMoData:preparation_switch', ORIGIN)])
    return view


def source_ids(entries):
    require(isinstance(entries, list)
            and all(isinstance(e, dict) and type(e.get('id')) is int for e in entries),
            'explicit_strategy_entries_required')
    ids = [e['id'] for e in entries]
    require(len(ids) == len(set(ids)), 'duplicate_source_strategies')
    return ids


def validate_owner_switch(case):
    row, context = case['row'], case['combat_context']
    require(len(row['players']) == len(context['players']) == 2, 'two_players_required')
    require(context['players'][1].get('upgrade_sound_switch') is None,
            'opponent_private_switch_not_observed')
    start = row['players'][0]['candidate_start']
    cp = context['players'][0]
    if 1009 not in start['xian_mo_strategies']:
        require(cp.get('upgrade_sound_switch') is None, 'switch_without_ownership')
        return None
    extension_contract()
    require(case.get('preparation_owner_verified') is True
            and cp.get('website_hand_unknown') is False, 'verified_private_owner_required')
    require(all(p.get('is_mirror') is False for p in context['players']), 'mirror_not_admitted')
    src = row['source']
    require(context.get('source_raw_sha256') == src['raw_sha256'], 'context_source_mismatch')
    path = Path(src['path'])
    require(hashlib.sha256(path.read_bytes()).hexdigest() == src['raw_sha256'], 'source_file_changed')
    rid, owner, before, battle = _before(str(path), src['raw_sha256'], src['step'])
    require(row['id'] == rid + '/round' + str(row['round'])
            and before['round'] == battle['round'] == row['round'], 'source_round_mismatch')
    require(before.get('gameMode') == 3 and before.get('seasonMechanic') == 10,
            'source_mode_outside_scope')
    require(before.get('targetUid') == owner, 'source_owner_mismatch')
    matches = [m for m in battle['matchups']
               if m.get('authoritative') is True and owner in m.get('players', {})]
    require(len(matches) == 1 and len(matches[0]['players']) == 2, 'unique_authoritative_pair_required')
    pair = matches[0]['players']
    opponent = pair[owner].get('opponentUid')
    require(opponent != owner and opponent in pair
            and pair[opponent].get('opponentUid') == owner, 'reciprocal_pair_required')
    private = before.get('privatePlayer')
    require(isinstance(private, dict) and private.get('uid') == owner, 'source_private_owner_required')
    require(row['players'][0]['character_id'] == pair[owner].get('characterId'),
            'source_character_mismatch')
    require(private.get('deck') == start['board'] == pair[owner].get('deck'), 'source_board_mismatch')
    entries = private.get('selectedXianMoStrategies')
    ids = source_ids(entries)
    require(ids == start['xian_mo_strategies'] == source_ids(pair[owner].get('xianMoStrategies')),
            'source_ownership_mismatch')
    chosen = next(e for e in entries if e['id'] == 1009)
    require(type(chosen.get('locked')) is bool, 'explicit_private_switch_required')
    value = cp.get('website_strategy_parameters', {}).get('1009')
    require(type(value) is int and value in (0, 1) and value == int(chosen['locked']),
            'parameter_conflict_or_missing')
    receipt = {'origin': ORIGIN, 'source_raw_sha256': src['raw_sha256'],
               'source_step': src['step'], 'case_id': row['id'], 'player_index': 0,
               'environment_only': True, 'selected_strategy_ids': [1009],
               'temp_data': {'1009': value}, 'private_state_sha256': digest(private)}
    require(cp.get('upgrade_sound_switch') is None or cp['upgrade_sound_switch'] == receipt,
            'prefilled_receipt_mismatch')
    return receipt


def compile_case(case, view, tables):
    receipt = validate_owner_switch(case)
    if receipt is None:
        return previous.compile_case(case, view, tables)
    projected = deepcopy(case)
    projected['combat_context']['players'][0]['upgrade_sound_switch'] = receipt
    result = previous.compile_case(projected, view, tables)
    require(result['battle']['upgrade_sound']['players'][0]['enabled']
            == (receipt['temp_data']['1009'] == 0), 'compiled_switch_mismatch')
    require(result['battle']['upgrade_sound']['raw_boards']
            == [p['candidate_start']['board'] for p in case['row']['players']],
            'compiled_original_boards_changed')
    result['website_owner_upgrade_v149'] = {
        'evidence_sha256': PROOF_SHA, 'source_check': receipt,
        'source_field': 'privatePlayer.selectedXianMoStrategies[id=1009].locked',
        'battle_summary_locked_used': False, 'persistent_boards_changed': False,
        'training_label_allowed': False}
    return result
