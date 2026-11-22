"""Wood patrol and original-record selected-card readers over frozen v129r3."""
from copy import deepcopy
from pathlib import Path
import hashlib, json
from . import full_battle_v129r3 as previous
from . import full_battle_v80 as core
from .combat_compiler_view_v81 import isolated_compiler, compiler_modules
from .full_battle_v45 import digest_json, snapshot_binding

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / 'data/inspection/current-mirror-card-consumers-v130.json'
PROOF_SHA = '86f5d71698bde147f85bcb519bfa8f3b7a992481537dbd72996cc9c900f89cb5'
BRIDGE = ROOT / 'tools/full_battle_bridge_v130.mjs'
UnresolvedBattle = previous.UnresolvedBattle
derive_start_initiative = previous.derive_start_initiative

def extension_contract():
    raw = PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROOF_SHA:
        raise UnresolvedBattle('card_consumers_v130:evidence_changed')
    facts = json.loads(raw)
    for name, digest in facts['source_sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise UnresolvedBattle('card_consumers_v130:source_changed:' + name)
    return facts

def catalogue():
    facts = extension_contract()
    cards, mapping, talents, season = previous.catalogue()
    for c in facts['cards']:
        if c['raw_id'] in mapping or c['runtime_id'] in mapping.values():
            raise UnresolvedBattle('card_consumers_v130:alias_collision')
        mapping[c['raw_id']] = c['runtime_id']
    return cards, mapping, talents, season

def compile_start(row, **kwargs):
    facts = extension_contract()
    if 'tables' not in kwargs:
        kwargs['tables'] = catalogue()
    expected = facts['random_bindings'].get(row.get('id'))
    if expected is None:
        return previous.compile_start(row, **kwargs)
    ctx = kwargs.get('combat_context')
    binding = expected['binding']
    if not isinstance(ctx, dict) or snapshot_binding(row, ctx) != binding['snapshot_sha256']:
        raise UnresolvedBattle('card_consumers_v130:original_snapshot_required')
    stream = ctx.get('battle_params')
    if (not isinstance(stream, list) or not stream or any(type(v) is not int for v in stream)
            or digest_json(stream) != binding['stream_sha256']):
        raise UnresolvedBattle('card_consumers_v130:original_stream_required')
    evidence = row.get('battle_params_evidence', {})
    if evidence.get('entries') != len(stream) or evidence.get('sha256') != binding['stream_sha256']:
        raise UnresolvedBattle('card_consumers_v130:source_parameter_evidence_required')
    result = previous.compile_mirror_start(row, **kwargs)
    result['mirror_context_v129']['evidence_sha256'] = previous.PROOF_SHA
    battle = result['battle']
    if (digest_json(battle) != expected['compiled_battle_sha256']
            or battle['first_player'] != binding['first_player']
            or any('parameter' in k or k == 'falling_paper' for k in battle)):
        raise UnresolvedBattle('card_consumers_v130:original_compiled_start_required')
    battle['replay_parameters'] = {
        'stream': list(stream), 'battle_sha256': digest_json(battle),
        'record_binding': deepcopy(binding)}
    return result

def simulate_batch(battles, *, timeout=90):
    extension_contract()
    for module in compiler_modules(previous).values():
        contract = vars(module).get('extension_contract')
        if contract is not None:
            contract()
    result = isolated_compiler(core, runtime_bridge=BRIDGE).simulate_batch(battles, timeout=timeout)
    result['adapter_contract'] = {**result['adapter_contract'],
        'schema': 'complete-single-battle-diagnostic-v130',
        'card_consumer_evidence_sha256': PROOF_SHA, 'training_label_allowed': False}
    return result
