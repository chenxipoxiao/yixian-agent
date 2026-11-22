"""Bound Remnant Cloud parameters over an isolated frozen v80 compiler.

This admits an audited recorded battle, not arbitrary retained-hand rules or
counterfactual play. Original card IDs, names and source state remain intact.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from . import full_battle_v80 as previous
from . import full_battle_base_v81 as leaf
from .combat_compiler_view_v81 import isolated_compiler, compiler_modules
from .full_battle_v45 import digest_json, snapshot_binding

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / 'data/inspection/current-cloud-parameter-v81.json'
PROOF_SHA = 'd5f8ff76183b4f499eb9e418b7106f892ed85aa1e314cf1e82c0c7204bacacff'
BRIDGE = ROOT / 'tools/full_battle_bridge_v81.mjs'
UnresolvedBattle = previous.UnresolvedBattle
catalogue = previous.catalogue
derive_start_initiative = previous.derive_start_initiative
CLOUD_IDS = frozenset({1000052, 1010052, 1020052})


def extension_contract():
    raw = PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROOF_SHA:
        raise UnresolvedBattle('cloud_parameter_v81:evidence_changed')
    facts = json.loads(raw)
    for path, expected in facts['source_sha256'].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise UnresolvedBattle('cloud_parameter_v81:source_changed:' + path)
    modules = compiler_modules(previous)
    if sorted(modules) != facts['compiler_modules']:
        raise UnresolvedBattle('cloud_parameter_v81:compiler_graph_changed')
    return facts


def compile_start(row, **kwargs):
    facts = extension_contract()
    ctx = kwargs.get('combat_context')
    if not isinstance(ctx, dict) or 'cloud_sword_record' not in ctx:
        return previous.compile_start(row, **kwargs)
    binding = ctx['cloud_sword_record']
    expected = facts['admitted_records'].get(row.get('id'))
    if expected is None or binding != expected['binding']:
        raise UnresolvedBattle('cloud_parameter_v81:unaudited_record_binding')
    if any(key in ctx for key in ['typed_parameter_record', 'falling_paper_record']):
        raise UnresolvedBattle('cloud_parameter_v81:mixed_parameter_consumers')
    if snapshot_binding(row, ctx) != binding['snapshot_sha256']:
        raise UnresolvedBattle('cloud_parameter_v81:original_snapshot_mismatch')
    params = ctx.get('battle_params')
    if (not isinstance(params, list) or not params or len(params) > 256
            or any(type(x) is not int or not 0 <= x <= 2147483647 for x in params)
            or digest_json(params) != binding['stream_sha256']):
        raise UnresolvedBattle('cloud_parameter_v81:complete_stream_mismatch')
    source = row.get('battle_params_evidence')
    if (not isinstance(source, dict) or source.get('entries') != len(params)
            or source.get('sha256') != binding['stream_sha256']):
        raise UnresolvedBattle('cloud_parameter_v81:source_parameter_mismatch')
    if kwargs.get('first_player') != binding['first_player']:
        raise UnresolvedBattle('cloud_parameter_v81:initiative_binding_mismatch')
    # Ancestors consume known effects, but never change the original boards.
    boards = tuple(tuple(p['candidate_start']['board']) for p in row['players'])
    source_hash = row['source']['raw_sha256']
    record_id = row['id']

    def guard(projected, index, board):
        return (projected['id'] == record_id and projected['source']['raw_sha256'] == source_hash
                and tuple(board) == boards[index] and bool(CLOUD_IDS.intersection(board)))

    def compile_leaf(projected, **leaf_kwargs):
        return leaf.compile_start(projected, **leaf_kwargs, _cloud_record_guard=guard)

    # All ordinary effects still pass through the same frozen ancestors. No
    # card substitution, metadata renaming or process-global monkeypatching.
    view = isolated_compiler(previous, base_compile=compile_leaf)
    result = view.compile_start(row, **kwargs)
    battle = result['battle']
    tables = kwargs.get('tables') or catalogue()
    expected_cards = [[tables[1][raw] for raw in board] for board in boards]
    if expected_cards != [p['cards'] for p in battle['players']]:
        raise UnresolvedBattle('cloud_parameter_v81:original_card_identity_changed')
    if 'typed_parameters' in battle or 'falling_paper' in battle:
        raise UnresolvedBattle('cloud_parameter_v81:duplicate_parameter_handler')
    if digest_json(battle) != expected['compiled_battle_sha256']:
        raise UnresolvedBattle('cloud_parameter_v81:unaudited_compiled_start')
    battle['cloud_sword_parameters'] = {
        'stream': list(params), 'consumers': deepcopy(expected['consumers']),
        'battle_sha256': digest_json(battle), 'record_binding': deepcopy(binding),
    }
    result['cloud_parameter_context_v81'] = {
        'evidence_sha256': PROOF_SHA, 'record_conditioned': True,
        'source_snapshot_sha256': binding['snapshot_sha256'],
        'hand_source_sha256': binding['hand_source_sha256'],
        'first_player': binding['first_player'], 'card_identity_preserved': True,
        'server_hand_classifier_recovered': False, 'counterfactual_reuse_allowed': False,
        'policy_observation_allowed': False, 'training_label_allowed': False,
    }
    return result


def simulate_batch(battles, *, timeout=90):
    extension_contract()
    view = isolated_compiler(previous, runtime_bridge=BRIDGE)
    result = view.simulate_batch(battles, timeout=timeout)
    result['adapter_contract'] = {**result['adapter_contract'],
        'schema': 'complete-single-battle-diagnostic-v81', 'evidence_sha256': PROOF_SHA,
        'bound_cloud_parameter_extension': True}
    return result
