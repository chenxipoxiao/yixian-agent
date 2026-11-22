"""Five realm forms of Dream Overwhelming Force over the frozen v130 input chain."""
import hashlib
import json
from pathlib import Path
from . import full_battle_v130 as previous
from . import full_battle_v80 as core
from .combat_compiler_view_v81 import isolated_compiler, compiler_modules

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT/'data/inspection/current-dream-overwhelming-force-v136.json'
PROOF_SHA = '821f99435c29f231c0f30add989a00a47aca7ac171da50ab568457c7d9a557f5'
BRIDGE = ROOT/'tools/full_battle_bridge_web_v136.mjs'
UnresolvedBattle = previous.UnresolvedBattle
derive_start_initiative = previous.derive_start_initiative


def extension_contract():
    raw = PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROOF_SHA:
        raise UnresolvedBattle('dream_force_v136:evidence_changed')
    facts = json.loads(raw)
    for name, expected in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
            raise UnresolvedBattle('dream_force_v136:source_changed:' + name)
    return facts


def catalogue():
    facts = extension_contract()
    cards, mapping, talents, season = previous.catalogue()
    for c in facts['cards']:
        if c['raw_id'] in mapping or c['runtime_id'] in mapping.values():
            raise UnresolvedBattle('dream_force_v136:alias_collision')
        if cards.get(c['raw_id']) != c['config']:
            raise UnresolvedBattle('dream_force_v136:configuration_mismatch')
        mapping[c['raw_id']] = c['runtime_id']
    return cards, mapping, talents, season


def compile_start(row, **kwargs):
    extension_contract()
    if 'tables' not in kwargs:
        kwargs['tables'] = catalogue()
    return previous.compile_start(row, **kwargs)


def simulate_batch(battles, *, timeout=90):
    extension_contract()
    for module in compiler_modules(previous).values():
        contract = vars(module).get('extension_contract')
        if contract is not None:
            contract()
    result = isolated_compiler(core, runtime_bridge=BRIDGE).simulate_batch(battles, timeout=timeout)
    result['adapter_contract'] = {**result['adapter_contract'],
        'schema':'complete-single-battle-diagnostic-v136',
        'dream_force_evidence_sha256':PROOF_SHA,'training_label_allowed':False}
    return result
