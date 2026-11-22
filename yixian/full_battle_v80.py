"""Original-snapshot parameter binding and explicit inactive vase slots.

Frozen v79r2 remains the fast path. The fallback resolves only two compiler
projection errors; it does not infer random parameters or unread card effects.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from . import full_battle_v79r2 as previous
from . import full_battle_v45 as paper
from . import full_battle_v13 as vase

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / 'data/inspection/current-start-context-v80.json'
PROOF_SHA = 'e94f16d0bcd04badf52585ea6233b959388c1c4ad57c5af95d643c55240b47c9'
UnresolvedBattle = previous.UnresolvedBattle
catalogue = previous.catalogue
derive_start_initiative = previous.derive_start_initiative


def extension_contract():
    raw = PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROOF_SHA:
        raise UnresolvedBattle('Start context evidence changed')
    facts = json.loads(raw)
    for path, digest in facts['source_sha256'].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise UnresolvedBattle('Start context source changed:' + path)
    return facts


def _original_paper_binding(row, context):
    """Validate the raw start before ancestor compilers consume ownership IDs."""
    owned = []
    for player in row['players']:
        choices = player['candidate_start'].get('xian_mo_strategies')
        if (not isinstance(choices, list) or any(type(x) is not int for x in choices)
                or len(choices) != len(set(choices))):
            raise UnresolvedBattle('start_context_v80:unique_explicit_season_choices_required')
        owned.append(16024 in choices)
    if not any(owned) or 'typed_parameter_record' in context:
        return None
    binding = context.get('falling_paper_record')
    if binding != {'snapshot_sha256': paper.snapshot_binding(row, context),
                   'scope': 'unchanged_recorded_battle_only'}:
        raise UnresolvedBattle('falling_paper_snapshot_binding_mismatch')
    params = context.get('battle_params')
    if not isinstance(params, list) or len(params) != sum(owned):
        raise UnresolvedBattle('falling_paper_other_parameter_consumers_unresolved')
    if any(type(x) is not int or x not in range(4) for x in params):
        raise UnresolvedBattle('falling_paper_invalid_branch')
    evidence = row.get('battle_params_evidence')
    if (not isinstance(evidence, dict) or evidence.get('entries') != len(params)
            or evidence.get('sha256') != paper.digest_json(params)):
        raise UnresolvedBattle('falling_paper_source_parameter_mismatch')
    return {'owners': owned, 'stream': list(params),
            'snapshot_sha256': binding['snapshot_sha256']}


def _vase_projection(row, context, tables, facts):
    cards, mapping, _, _ = tables
    entries = []
    for index, (player, ctx) in enumerate(zip(row['players'], context['players'])):
        start = player['candidate_start']
        fates = start.get('talents')
        if (not isinstance(fates, list) or any(type(x) is not int for x in fates)
                or len(fates) != len(set(fates))):
            raise UnresolvedBattle('start_context_v80:unique_explicit_talents_required')
        if 199 not in fates:
            continue
        stored = vase._params(ctx, 'privateTalentDatas', '199')
        if len(stored) not in (0, 3):
            raise UnresolvedBattle('Explicit three vase slots required')
        if not any(value not in mapping or value not in cards for value in stored):
            continue  # Preserve every already supported compiler output.
        if set(start['xian_mo_strategies']) & {23058, 7085}:
            raise UnresolvedBattle('start_context_v80:vase_season_interaction_unresolved')
        if any(value not in cards for value in stored):
            raise UnresolvedBattle('start_context_v80:unknown_vase_raw_card')
        if stored[0] not in mapping:
            raise UnresolvedBattle('start_context_v80:vase_first_slot_unmapped')
        inactive = [i for i in (1, 2) if stored[i] not in mapping]
        if any(stored[i] not in facts['reviewed_inactive_vase_raw_ids'] for i in inactive):
            raise UnresolvedBattle('start_context_v80:unreviewed_inactive_vase_card')
        # null here means omitted non-read runtime channel, NOT unknown raw state.
        # All three exact raw IDs remain in the explicit projection receipt.
        native = [mapping[value] if value and value in mapping else None for value in stored]
        entries.append({'player_index': index, 'raw_slots': list(stored),
                        'read_slot_indices': [0], 'omitted_runtime_slot_indices': inactive,
                        'native_cards': native})
    return entries


def compile_start(row, **kwargs):
    facts = extension_contract()
    context = kwargs.get('combat_context')
    if (not isinstance(context, dict) or not isinstance(row.get('players'), list)
            or len(row['players']) != 2 or len(context.get('players', [])) != 2):
        raise UnresolvedBattle('start_context_v80:two_explicit_start_players_required')
    binding = _original_paper_binding(row, context)
    try:
        return previous.compile_start(row, **kwargs)
    except UnresolvedBattle as error:
        if str(error) not in {'falling_paper_snapshot_binding_mismatch', 'Unmapped vase card context'}:
            raise
        reason = str(error)
    if 'typed_parameter_record' in context:
        raise UnresolvedBattle('start_context_v80:typed_stream_projection_not_admitted')
    tables = kwargs.get('tables') or catalogue()
    entries = _vase_projection(row, context, tables, facts)
    if not binding and not entries:
        raise UnresolvedBattle(reason)
    projected = deepcopy(row)
    for entry in entries:
        start = projected['players'][entry['player_index']]['candidate_start']
        start['talents'] = [value for value in start['talents'] if value != 199]
    if binding:
        for player in projected['players']:
            start = player['candidate_start']
            start['xian_mo_strategies'] = [value for value in start['xian_mo_strategies'] if value != 16024]
    result = previous.compile_start(projected, **{**kwargs, 'tables': tables})
    for entry in entries:
        index = entry['player_index']
        extra = {'five_elements_pure_vase_stacks': 1,
                 'five_elements_pure_vase_cards': entry['native_cards']}
        target = result['battle']['players'][index]
        if any(key in target for key in extra):
            raise UnresolvedBattle('start_context_v80:duplicate_vase_effect')
        target.update(deepcopy(extra))
        result['current_fate_context']['players'][index]['native_fields'].update(deepcopy(extra))
        result['effect_players'][index]['fates'] = deepcopy(row['players'][index]['candidate_start']['talents'])
    if binding:
        battle = result['battle']
        if 'falling_paper' in battle or 'typed_parameters' in battle:
            raise UnresolvedBattle('start_context_v80:duplicate_parameter_handler')
        # Bind the final compiled payload, after every versioned start projection.
        battle['falling_paper'] = {'owners': binding['owners'], 'stream': binding['stream'],
                                   'battle_sha256': paper.digest_json(battle)}
        for i, player in enumerate(row['players']):
            result['effect_players'][i]['season_choices'] = deepcopy(player['candidate_start']['xian_mo_strategies'])
        result['falling_paper_context'] = {
            'evidence_sha256': paper.PROOF_SHA, 'record_conditioned': True,
            'snapshot_sha256': binding['snapshot_sha256'],
            'full_parameter_stream_sha256': paper.digest_json(binding['stream']),
            'other_rng_allowed': False, 'policy_observation_allowed': False,
            'counterfactual_reuse_allowed': False, 'exchange_reward_authoritative': False,
            'training_label_allowed': False}
    result['start_context_v80'] = {
        'evidence_sha256': PROOF_SHA, 'original_snapshot_verified_before_projection': binding is not None,
        'vase_projections': entries, 'fallback_reason': reason,
        'inactive_slots_inferred': False, 'acquisition_rewards_reapplied': False,
        'policy_observation_allowed': False, 'training_label_allowed': False}
    return result


def simulate_batch(battles, *, timeout=90):
    extension_contract()
    result = previous.simulate_batch(battles, timeout=timeout)
    result['adapter_contract'] = {**result['adapter_contract'],
        'schema': 'complete-single-battle-diagnostic-v80', 'evidence_sha256': PROOF_SHA,
        'compiled_original_snapshot_extension': True}
    return result
