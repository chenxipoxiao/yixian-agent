"""Source-bound receipt for an observed Suanni skip choice.

The v137r2 choice classifier already exists. This adapter obtains its receipt
from the immediately preceding private source state, without changing effects,
ordinary fate25, battle ownership, unknown opponent state or earlier adapters.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json

from . import website_battles_v149 as previous
from .website_battles_v139 import _before, digest

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / 'data/inspection/website-skip-choice-v151.json'
ORIGIN = previous.ORIGIN
UnresolvedBattle = previous.UnresolvedBattle
CONFLICT = 'private_vs_battle_strategy_ownership'


def require(ok, reason):
    if not ok:
        raise UnresolvedBattle('website_skip_v151:' + reason)


def extension_contract():
    facts = json.loads(PROOF.read_text(encoding='utf-8'))
    require(facts['catalog25_sha256'] ==
            '10abb0acd7a4970edbb413d5ffe2f1baa7a475b1e8219eb43a00c707d55f5ae2',
            'skip_catalog_contract_changed')
    for path, expected in facts['source_sha256'].items():
        require(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected,
                'evidence_source_changed:' + path)
    return facts


def compiler():
    extension_contract()
    return previous.compiler()


def strategy_ids(entries):
    require(isinstance(entries, list) and all(
        isinstance(e, dict) and type(e.get('id')) is int for e in entries),
        'explicit_strategy_entries_required')
    result = [e['id'] for e in entries]
    require(len(result) == len(set(result)), 'duplicate_strategy_ids')
    return result


def bind_skip_receipt(case):
    if CONFLICT not in case['input_conflicts']:
        return case, None
    # Other conflicts are not normalized by this extension.
    require(case['input_conflicts'] == [CONFLICT], 'additional_input_conflicts')
    facts = extension_contract()
    row, context = case['row'], case['combat_context']
    require(len(row['players']) == len(context['players']) == 2, 'two_players_required')
    cp = context['players'][0]
    require(case.get('preparation_owner_verified') is True
            and cp.get('website_hand_unknown') is False, 'verified_private_owner_required')
    require(context.get('game_mode') == 3 and context.get('season_mec') == 10,
            'context_mode_outside_scope')
    require(all(p.get('is_mirror') is False for p in context['players']), 'mirror_not_admitted')
    src = row['source']
    require(context.get('source_raw_sha256') == src['raw_sha256'], 'context_source_mismatch')
    path = Path(src['path'])
    require(hashlib.sha256(path.read_bytes()).hexdigest() == src['raw_sha256'], 'source_file_changed')
    raw = json.loads(path.read_text(encoding='utf-8'))
    metadata = raw.get('catalog', {}).get('xianMoStrategies', {}).get('25')
    require(isinstance(metadata, dict) and metadata.get('assetKind') == 'xianMoStrategy'
            and metadata.get('isSkip') is True and metadata.get('isSuanniSkip') is True
            and digest(metadata) == facts['catalog25_sha256'], 'source_skip_metadata_required')
    rid, owner, before, battle = _before(str(path), src['raw_sha256'], src['step'])
    require(row['id'] == rid + '/round' + str(row['round']) and row['game_id'] == rid
            and before['round'] == battle['round'] == row['round'], 'source_round_mismatch')
    require(before.get('gameMode') == 3 and before.get('seasonMechanic') == 10,
            'source_mode_outside_scope')
    require(before.get('targetUid') == owner, 'source_owner_mismatch')
    matches = [m for m in battle['matchups']
               if m.get('authoritative') is True and owner in m.get('players', {})]
    require(len(matches) == 1 and len(matches[0]['players']) == 2, 'authoritative_pair_required')
    pair = matches[0]['players']
    opponent = pair[owner].get('opponentUid')
    require(opponent != owner and opponent in pair
            and pair[opponent].get('opponentUid') == owner, 'reciprocal_pair_required')
    private = before.get('privatePlayer')
    require(isinstance(private, dict) and private.get('uid') == owner, 'source_private_owner_required')
    start = row['players'][0]['candidate_start']
    require(row['players'][0]['character_id'] == pair[owner].get('characterId'), 'source_character_mismatch')
    require(private.get('deck') == start['board'] == pair[owner].get('deck'), 'source_board_mismatch')
    require(start['level'] == pair[owner].get('phase')
            and start['exp'] == pair[owner].get('cultivation'), 'source_start_mismatch')
    require(start['talents'] == strategy_ids(pair[owner].get('talents')), 'ordinary_fates_changed')
    require(isinstance(private.get('hand'), list) and type(cp.get('hand_count')) is int
            and cp['hand_count'] == len(private['hand']), 'source_hand_mismatch')
    entries = private.get('selectedXianMoStrategies')
    private_ids = strategy_ids(entries)
    battle_ids = strategy_ids(pair[owner].get('xianMoStrategies'))
    require(start['xian_mo_strategies'] == battle_ids, 'battle_ownership_changed')
    require(25 in private_ids and 25 not in battle_ids and 24 not in private_ids,
            'only_absent_battle_skip25_supported')
    chosen = next(e for e in entries if e['id'] == 25)
    require('runtime' in chosen and chosen['runtime'] is None
            and chosen.get('locked') is False, 'skip_runtime_unknown')
    history = chosen.get('choiceHistory', {})
    offers = history.get('offers')
    require(history.get('complete') is True and history.get('selected') == 25
            and type(history.get('roundOrPhase')) is int
            and 0 < history['roundOrPhase'] <= row['round']
            and isinstance(offers, list) and bool(offers)
            and all(isinstance(group, list) and all(type(x) is int for x in group) for group in offers)
            and any(25 in group for group in offers), 'observed_skip_selection_required')
    require(set(private_ids) - {25} == set(battle_ids), 'remaining_ownership_mismatch')
    receipt = {'origin': ORIGIN, 'source_raw_sha256': src['raw_sha256'],
               'source_step': src['step'], 'case_id': row['id'], 'player_index': 0,
               'environment_only': True, 'battle_strategy_ids': battle_ids,
               'private_selected_ids': private_ids, 'observed_suanni_skip_ids': [25],
               'metadata_verified_skip_ids': [25]}
    require(cp.get('website_skip_ownership_v137r2') is None
            or cp['website_skip_ownership_v137r2'] == receipt, 'prefilled_receipt_mismatch')
    projected = deepcopy(case)
    projected['combat_context']['players'][0]['website_skip_ownership_v137r2'] = receipt
    return projected, {'source_raw_sha256': src['raw_sha256'], 'source_step': src['step'],
                       'private_state_sha256': digest(private), 'skip_catalog_sha256': digest(metadata),
                       'source_skip_id': 25, 'ordinary_fates_unchanged': True,
                       'battle_strategy_ids_unchanged': True, 'training_label_allowed': False}


def compile_case(case, view, tables):
    projected, receipt = bind_skip_receipt(case)
    result = previous.compile_case(projected, view, tables)
    if receipt is not None:
        result['website_skip_choice_v151'] = receipt
    return result
