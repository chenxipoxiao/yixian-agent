"""Known Enlightenment Elixir names in the vase's first-slot name reader.

Only the activation metadata is projected. Stored raw IDs and source receipts
remain intact; neither a playable-card alias nor refining rewards are added.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json

from . import website_battles_v151 as previous
from .website_battles_v132 import web_params
from .website_battles_v139 import _before, digest
from .combat_compiler_view_v81 import compiler_modules

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / 'data/inspection/website-vase-nonelement-v152.json'
METADATA_IDS = frozenset((2000015, 2010015, 2020015))
FRAGMENTS = ('金灵', '木灵', '水灵', '火灵', '土灵')
ORIGIN = previous.ORIGIN
UnresolvedBattle = previous.UnresolvedBattle


def require(ok, reason):
    if not ok:
        raise UnresolvedBattle('website_vase_v152:' + reason)


def extension_contract():
    facts = json.loads(PROOF.read_text(encoding='utf-8'))
    require(set(map(int, facts['metadata_cards'])) == METADATA_IDS, 'metadata_contract_changed')
    require(facts['element_name_fragments'] == list(FRAGMENTS), 'name_reader_changed')
    for path, expected in facts['source_sha256'].items():
        require(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected,
                'evidence_source_changed:' + path)
    for card in facts['metadata_cards'].values():
        require(card['name'] == '悟道丹' and not any(s in card['name'] for s in FRAGMENTS),
                'not_reviewed_neutral_name')
    return facts


def affected_seats(row, context):
    seats = []
    for seat, (p, cp) in enumerate(zip(row['players'], context['players'])):
        if 199 not in p['candidate_start']['talents']:
            continue
        slots = web_params(cp, 'privateTalentDatas', '199')
        if slots and slots[0] in METADATA_IDS:
            seats.append(seat)
    return seats


def expected_receipt(row, seat, slots):
    return {'origin': ORIGIN, 'source_raw_sha256': row['source']['raw_sha256'],
            'source_step': row['source']['step'], 'case_id': row['id'],
            'player_index': seat, 'raw_slots': slots, 'environment_only': True,
            'read_slot_indices': [0], 'metadata_only': True}


def validate_source(case):
    row, context = case['row'], case['combat_context']
    seats = affected_seats(row, context)
    if not seats:
        return []
    extension_contract()
    require(seats == [0], 'owner_private_storage_required')
    require(case.get('preparation_owner_verified') is True
            and context['players'][0].get('website_hand_unknown') is False,
            'verified_owner_required')
    require(all(p.get('is_mirror') is False for p in context['players']), 'mirror_not_admitted')
    start = row['players'][0]['candidate_start']
    require(not (set(start['xian_mo_strategies']) & {7085, 23058})
            and 309 not in start['fate_strategies'], 'extra_reader_not_admitted')
    require(context.get('game_mode') == 3 and context.get('season_mec') == 10,
            'context_mode_outside_scope')
    src = row['source'];path = Path(src['path'])
    require(context.get('source_raw_sha256') == src['raw_sha256'], 'context_source_mismatch')
    require(hashlib.sha256(path.read_bytes()).hexdigest() == src['raw_sha256'], 'source_file_changed')
    rid, owner, before, battle = _before(str(path), src['raw_sha256'], src['step'])
    require(row['id'] == rid + '/round' + str(row['round']) and row['game_id'] == rid
            and before['round'] == battle['round'] == row['round'], 'source_round_mismatch')
    require(before.get('gameMode') == 3 and before.get('seasonMechanic') == 10
            and before.get('targetUid') == owner, 'source_scope_mismatch')
    matches = [m for m in battle['matchups']
               if m.get('authoritative') is True and owner in m.get('players', {})]
    require(len(matches) == 1 and len(matches[0]['players']) == 2, 'authoritative_pair_required')
    pair = matches[0]['players'];other = pair[owner].get('opponentUid')
    require(other != owner and other in pair and pair[other].get('opponentUid') == owner,
            'reciprocal_pair_required')
    require(all(not p.get('innerDemon') and type(p.get('lifeBefore')) is int
                and p['lifeBefore'] > 0 for p in pair.values()), 'source_mirror_not_admitted')
    private = before.get('privatePlayer')
    require(isinstance(private, dict) and private.get('uid') == owner, 'source_private_owner_required')
    require(row['players'][0]['character_id'] == pair[owner].get('characterId')
            and start['board'] == private.get('deck') == pair[owner].get('deck'), 'source_player_mismatch')
    require(start['talents'] == previous.strategy_ids(pair[owner].get('talents'))
            and start['xian_mo_strategies'] == previous.strategy_ids(pair[owner].get('xianMoStrategies'))
            and start['fate_strategies'] == previous.strategy_ids(pair[owner].get('fateStrategies')),
            'source_ownership_mismatch')
    slots = web_params(context['players'][0], 'privateTalentDatas', '199')
    stored = private.get('cardStorage', {}).get('199')
    require(isinstance(stored, list) and len(stored) == 3
            and all(type(x) is int and x >= 0 for x in stored) and slots == stored,
            'source_storage_mismatch')
    receipt = expected_receipt(row, 0, slots)
    supplied = context['players'][0].get('vase_nonelement_receipt_v152')
    require(supplied is None or supplied == receipt, 'prefilled_receipt_mismatch')
    return [{'receipt': receipt, 'private_state_sha256': digest(private)}]


def extend_projection(original, proof):
    """Keep all unrelated per-call season projections in the frozen reader."""
    def projection(row, context, tables, old_facts):
        seats = affected_seats(row, context)
        if not seats:
            return original(row, context, tables, old_facts)
        require(seats == [0], 'owner_private_storage_required')
        cards, mapping, _, _ = tables
        seat = 0;cp = context['players'][seat];start = row['players'][seat]['candidate_start']
        slots = web_params(cp, 'privateTalentDatas', '199')
        require(len(slots) == 3, 'explicit_three_slots_required')
        require(cp.get('vase_nonelement_receipt_v152') == expected_receipt(row, seat, slots)
                and cp.get('website_hand_unknown') is False, 'source_receipt_required')
        require(not (set(start['xian_mo_strategies']) & {7085, 23058})
                and 309 not in start['fate_strategies'], 'extra_reader_not_admitted')
        require(all(raw in cards for raw in slots), 'unknown_raw_card')
        for raw in slots:
            if raw in METADATA_IDS:
                require(cards[raw]['name'] == proof['metadata_cards'][str(raw)]['name'], 'card_name_changed')
        require(slots[0] not in mapping, 'new_executable_mapping_requires_review')
        allowed = set(old_facts['reviewed_inactive_vase_raw_ids']) | METADATA_IDS
        require(all(slots[i] in mapping or slots[i] in allowed for i in (1, 2)),
                'unreviewed_inactive_card')
        projected = deepcopy(row)
        projected['players'][seat]['candidate_start']['talents'] = [x for x in start['talents'] if x != 199]
        entries = original(projected, context, tables, old_facts)
        require(all(e['player_index'] != seat for e in entries), 'duplicate_vase_projection')
        entries.append({'player_index': seat, 'raw_slots': list(slots), 'read_slot_indices': [0],
                        'omitted_runtime_slot_indices': [i for i, raw in enumerate(slots) if raw not in mapping],
                        'native_cards': [mapping[raw] if raw and raw in mapping else None for raw in slots],
                        'first_slot_known_non_element': True, 'metadata_only_raw_id': slots[0],
                        'metadata_evidence_sha256': hashlib.sha256(PROOF.read_bytes()).hexdigest(),
                        'card_body_admitted': False})
        return sorted(entries, key=lambda e: e['player_index'])
    return projection


def compiler():
    proof = extension_contract();view = previous.compiler();modules = compiler_modules(view)
    module = modules['yixian.full_battle_v124']
    module._website_vase_projection = extend_projection(module._website_vase_projection, proof)
    # The same reader must survive both direct v80 and nested v124 views.
    base = modules['yixian.full_battle_v80']
    base._vase_projection = extend_projection(base._vase_projection, proof)
    return view


def compile_case(case, view, tables):
    checks = validate_source(case)
    if not checks:
        return previous.compile_case(case, view, tables)
    projected = deepcopy(case)
    for check in checks:
        receipt = check['receipt']
        projected['combat_context']['players'][receipt['player_index']]['vase_nonelement_receipt_v152'] = receipt
    result = previous.compile_case(projected, view, tables)
    result['website_vase_nonelement_v152'] = {'source_checks': checks,
        'raw_slots_preserved': True, 'card_body_admitted': False, 'refining_rewards_applied': False,
        'training_label_allowed': False, 'source_version_certified': False}
    return result
