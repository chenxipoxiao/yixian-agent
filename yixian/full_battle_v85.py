"""Versioned current values for axe, Weaken Fulu and Dragon Devours Clouds."""
import hashlib
import json
from pathlib import Path
from . import full_battle_v84 as previous
from . import full_battle_v80 as core
from .combat_compiler_view_v81 import isolated_compiler

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT/'data/inspection/current-native-card-values-v85.json'
PROOF_SHA = 'db9c8d5fe6a0317feeb0cd0204d472b45761593dee3f8ec445a130ccd95f44d3'
BRIDGE = ROOT/'tools/full_battle_bridge_v85.mjs'
UnresolvedBattle = previous.UnresolvedBattle
catalogue = previous.catalogue
derive_start_initiative = previous.derive_start_initiative

def extension_contract():
    raw = PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROOF_SHA:
        raise UnresolvedBattle('native_card_values_v85:evidence_changed')
    facts = json.loads(raw)
    for name, expected in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
            raise UnresolvedBattle('native_card_values_v85:source_changed:'+name)
    return facts

def compile_start(row, **kwargs):
    extension_contract()
    return previous.compile_start(row, **kwargs)

def simulate_batch(battles, *, timeout=90):
    extension_contract()
    previous.extension_contract()
    previous.previous.extension_contract()
    previous.previous.previous.extension_contract()
    previous.previous.previous.previous.extension_contract()
    result = isolated_compiler(core, runtime_bridge=BRIDGE).simulate_batch(battles, timeout=timeout)
    result['adapter_contract'] = {**result['adapter_contract'],
        'schema':'complete-single-battle-diagnostic-v85',
        'card_values_evidence_sha256':PROOF_SHA,
        'mortal_body_evidence_sha256':previous.PROOF_SHA,
        'training_label_allowed':False}
    return result
