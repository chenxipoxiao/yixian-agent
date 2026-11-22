"""Flower Dance water-use history, preserving the frozen start compiler."""
import hashlib,json
from pathlib import Path
from . import full_battle_v90r2 as previous
from . import full_battle_v80 as core
from .combat_compiler_view_v81 import isolated_compiler,compiler_modules
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-flower-history-v91.json'
PROOF_SHA='3e07302be00c8eb7a4c9a6984808c52e8a16818dfb027c72ee95e4c31ff06594'
BRIDGE=ROOT/'tools/full_battle_bridge_v91.mjs'
UnresolvedBattle=previous.UnresolvedBattle
catalogue=previous.catalogue
derive_start_initiative=previous.derive_start_initiative
def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('flower_v91:evidence_changed')
    facts=json.loads(raw)
    for p,h in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('flower_v91:source_changed:'+p)
    return facts
def compile_start(row,**kwargs):
    extension_contract()
    return previous.compile_start(row,**kwargs)
def simulate_batch(battles,*,timeout=90):
    extension_contract()
    # Validate each versioned extension once; do not mutate ancestor globals.
    for module in compiler_modules(previous).values():
        contract=vars(module).get('extension_contract')
        if contract is not None:contract()
    result=isolated_compiler(core,runtime_bridge=BRIDGE).simulate_batch(battles,timeout=timeout)
    result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v91',
      'flower_history_evidence_sha256':PROOF_SHA,'training_label_allowed':False}
    return result
