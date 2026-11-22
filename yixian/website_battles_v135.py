"""Source-bound neutral stored-card metadata, without executable-card admission."""
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import hashlib
import json

from . import website_battles_v133 as previous
from .website_battles_v132 import web_params
from .combat_compiler_view_v81 import compiler_modules

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / 'data/inspection/current-vase-metadata-v135.json'
PROOF_SHA = '5836d0d4901897869c2b01a103dc0d6f3ce9745fd4d8602c7226b1edff70b208'
ORIGIN = previous.ORIGIN
UnresolvedBattle = previous.UnresolvedBattle
METADATA_ID = 9000007


@lru_cache(maxsize=1)
def facts():
    raw = PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROOF_SHA:
        raise UnresolvedBattle('website_vase_metadata:evidence_changed')
    value = json.loads(raw)
    for path, expected in value['source_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != expected:
            raise UnresolvedBattle('website_vase_metadata:source_changed:' + path)
    if value['metadata_only_raw_id'] != METADATA_ID or any(
            name in value['card_name'] for name in value['element_name_fragments']):
        raise UnresolvedBattle('website_vase_metadata:not_neutral_name')
    return value


def _validate_receipt(row, context, seat, slots):
    ctx = context['players'][seat]
    start = row['players'][seat]['candidate_start']
    receipt = ctx.get('vase_metadata_receipt')
    expected = {'origin': ORIGIN, 'source_raw_sha256': row['source']['raw_sha256'],
                'source_step': row['source']['step'], 'case_id': row['id'],
                'player_index': seat, 'raw_slots': slots, 'environment_only': True}
    if receipt != expected or seat != 0 or ctx.get('website_hand_unknown') is not False:
        raise UnresolvedBattle('website_vase_metadata:source_bound_private_owner_required')
    if set(start['xian_mo_strategies']) & {7085, 23058} or 309 in start['fate_strategies']:
        raise UnresolvedBattle('website_vase_metadata:extra_reader_not_admitted')


def compiler():
    proof = facts()
    view = previous.compiler()
    module = compiler_modules(view)['yixian.full_battle_v80']
    original = module._vase_projection

    def projection(row, context, tables, old_facts):
        cards, mapping, _, _ = tables
        needs_new = any(199 in p['candidate_start']['talents'] and
                        METADATA_ID in web_params(ctx, 'privateTalentDatas', '199')
                        for p, ctx in zip(row['players'], context['players']))
        if not needs_new:
            return original(row, context, tables, old_facts)
        entries = []
        for seat, (player, ctx) in enumerate(zip(row['players'], context['players'])):
            start = player['candidate_start']
            fates = start.get('talents')
            if (not isinstance(fates, list) or any(type(x) is not int for x in fates)
                    or len(fates) != len(set(fates))):
                raise UnresolvedBattle('website_vase_metadata:unique_explicit_talents_required')
            if 199 not in fates:
                continue
            slots = web_params(ctx, 'privateTalentDatas', '199')
            if len(slots) not in (0, 3):
                raise UnresolvedBattle('Explicit three vase slots required')
            if all(value in mapping and value in cards for value in slots):
                continue
            if METADATA_ID not in slots:
                # Delegate every unrelated legacy projection without widening it.
                old = original({'players': [player]}, {'players': [ctx]}, tables, old_facts)
                for entry in old:
                    entry['player_index'] = seat
                entries.extend(old)
                continue
            _validate_receipt(row, context, seat, slots)
            if any(value not in cards for value in slots):
                raise UnresolvedBattle('website_vase_metadata:unknown_raw_card')
            if cards[METADATA_ID]['name'] != proof['card_name']:
                raise UnresolvedBattle('website_vase_metadata:card_name_changed')
            if slots[0] not in mapping and slots[0] != METADATA_ID:
                raise UnresolvedBattle('start_context_v80:vase_first_slot_unmapped')
            allowed_inactive = set(old_facts['reviewed_inactive_vase_raw_ids']) | {METADATA_ID}
            if any(slots[i] not in mapping and slots[i] not in allowed_inactive for i in (1, 2)):
                raise UnresolvedBattle('start_context_v80:unreviewed_inactive_vase_card')
            native = [mapping[value] if value and value in mapping else None for value in slots]
            entries.append({'player_index': seat, 'raw_slots': list(slots), 'read_slot_indices': [0],
                            'omitted_runtime_slot_indices': [i for i, value in enumerate(slots) if value not in mapping],
                            'native_cards': native, 'metadata_evidence_sha256': PROOF_SHA,
                            'first_slot_known_non_element': slots[0] == METADATA_ID,
                            'card_body_admitted': False})
        return entries

    module._vase_projection = projection
    return view


def compile_case(case, view, tables):
    receipts = []
    for seat, (player, ctx) in enumerate(zip(case['row']['players'], case['combat_context']['players'])):
        if 199 not in player['candidate_start']['talents']:
            continue
        slots = web_params(ctx, 'privateTalentDatas', '199')
        if METADATA_ID not in slots:
            continue
        if case.get('preparation_owner_verified') is not True:
            raise UnresolvedBattle('website_vase_metadata:unverified_owner')
        _validate_receipt(case['row'], case['combat_context'], seat, slots)
        receipts.append(deepcopy(ctx['vase_metadata_receipt']))
    result = previous.compile_case(case, view, tables)
    if receipts:
        result['website_vase_metadata_v135'] = {'evidence_sha256': PROOF_SHA, 'receipts': receipts,
            'card_body_admitted': False, 'raw_slots_preserved': True, 'training_label_allowed': False}
    return result
