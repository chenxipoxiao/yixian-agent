"""Explicit mirror snapshots, with no substitution of a current/live opponent.

Mirrors retain their recorded board, level, private preparation context and
ownership. The extension only replaces the frozen base's mirror admission
guard. Missing markers and every other admission check remain strict.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
from . import full_battle_v128 as previous
from . import full_battle_v80 as core
from . import full_battle_base_v129 as leaf
from .combat_compiler_view_v81 import isolated_compiler, compiler_modules
from .full_battle_v45 import digest_json, snapshot_binding

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / 'data/inspection/current-mirror-context-v129.json'
PROOF_SHA = '81f5c2621e22cbef08ce23313c5308f8694d851f4cfa25e4f72792d72237642e'
BRIDGE = ROOT / 'tools/full_battle_bridge_v129.mjs'
UnresolvedBattle = previous.UnresolvedBattle
catalogue = previous.catalogue
derive_start_initiative = previous.derive_start_initiative


def extension_contract():
    raw = PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROOF_SHA:
        raise UnresolvedBattle('mirror_v129:evidence_changed')
    facts = json.loads(raw)
    for name, value in facts['source_sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != value:
            raise UnresolvedBattle('mirror_v129:source_changed:' + name)
    return facts


def mirror_flags(context):
    players = context.get('players') if isinstance(context, dict) else None
    if not isinstance(players, list) or len(players) != 2:
        raise UnresolvedBattle('mirror_v129:two_explicit_contexts_required')
    flags = [p.get('is_mirror') for p in players]
    if any(type(v) is not bool for v in flags):
        raise UnresolvedBattle('mirror_v129:explicit_boolean_markers_required')
    return flags


def compile_mirror_start(row, **kwargs):
    """Unbound opening compiler; no random outcome or terminal fields read."""
    context = kwargs.get('combat_context')
    flags = mirror_flags(context)
    if not any(flags):
        return previous.compile_start(row, **kwargs)
    for player in context['players']:
        if player.get('source_fields', {}).get('is_mirror') != 'publicData.isMirror':
            raise UnresolvedBattle('mirror_v129:marker_provenance_required')
    # Private module view; the old compiler and every original input stay intact.
    result = isolated_compiler(previous, base_compile=leaf.compile_start).compile_start(row, **kwargs)
    if [p['is_mirror'] for p in result['effect_players']] != flags:
        raise UnresolvedBattle('mirror_v129:marker_not_preserved')
    # Also available when a supported nested executor generates a civet card.
    result['battle']['civet'] = {'is_mirror': list(flags)}
    result['battle']['mirror_context'] = {'is_mirror': list(flags)}
    result['mirror_context_v129'] = {
        'is_mirror': list(flags), 'original_snapshot_preserved': True,
        'current_or_future_opponent_substituted': False,
        'round_source': 'original_battle_result_round',
        'authoritative_mirror_destiny_mutated': False,
        'match_continuation_allowed': False, 'training_label_allowed': False,
    }
    return result


def compile_start(row, **kwargs):
    flags = mirror_flags(kwargs.get('combat_context'))
    if not any(flags):
        return previous.compile_start(row, **kwargs)
    facts = extension_contract()
    result = compile_mirror_start(row, **kwargs)
    result['mirror_context_v129']['evidence_sha256'] = PROOF_SHA
    context = kwargs['combat_context']
    stream = context.get('battle_params')
    if not isinstance(stream, list) or any(type(x) is not int for x in stream):
        raise UnresolvedBattle('mirror_v129:explicit_parameter_sequence_required')
    if stream:
        expected = facts['random_bindings'].get(row.get('id'))
        if expected is None:
            raise UnresolvedBattle('mirror_v129:unaudited_random_record')
        binding = expected['binding']
        evidence = row.get('battle_params_evidence', {})
        if (snapshot_binding(row, context) != binding['snapshot_sha256']
                or digest_json(stream) != binding['stream_sha256']
                or evidence.get('entries') != len(stream)
                or evidence.get('sha256') != binding['stream_sha256']):
            raise UnresolvedBattle('mirror_v129:original_snapshot_and_stream_required')
        battle = result['battle']
        if (digest_json(battle) != expected['compiled_battle_sha256']
                or battle['first_player'] != binding['first_player']
                or any('parameter' in k or k == 'falling_paper' for k in battle)):
            raise UnresolvedBattle('mirror_v129:original_compiled_start_required')
        battle['replay_parameters'] = {
            'stream': list(stream), 'battle_sha256': digest_json(battle),
            'record_binding': deepcopy(binding),
        }
    return result


def simulate_batch(battles, *, timeout=90):
    extension_contract()
    for module in compiler_modules(previous).values():
        contract = vars(module).get('extension_contract')
        if contract is not None:
            contract()
    result = isolated_compiler(core, runtime_bridge=BRIDGE).simulate_batch(battles, timeout=timeout)
    result['adapter_contract'] = {**result['adapter_contract'],
        'schema': 'complete-single-battle-diagnostic-v129',
        'mirror_evidence_sha256': PROOF_SHA, 'training_label_allowed': False}
    return result
