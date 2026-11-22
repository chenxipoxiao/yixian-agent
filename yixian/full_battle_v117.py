"""Ordered205 before763 over the frozen v116 compiler."""
import hashlib,json
from pathlib import Path
from . import full_battle_v116 as previous
from . import full_battle_v80 as core
from .combat_compiler_view_v81 import isolated_compiler,compiler_modules
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-lightning-interleaving-v117.json'
PROOF_SHA='1defeae5b1ad72ba29f11a1efd865712c8f87ce60b75f18fa4fc4f81afc279c9'
BRIDGE=ROOT/'tools/full_battle_bridge_v117.mjs'
UnresolvedBattle=previous.UnresolvedBattle
def catalogue():
    extension_contract()
    return previous.catalogue()
derive_start_initiative=previous.derive_start_initiative
def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('lightning_interleaving_v117:evidence_changed')
    facts=json.loads(raw)
    for p,h in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('lightning_interleaving_v117:source_changed:'+p)
    return facts
def compile_start(row,**kwargs):
    extension_contract()
    if 'tables' not in kwargs:kwargs['tables']=catalogue()
    return previous.compile_start(row,**kwargs)
def simulate_batch(battles,*,timeout=90):
    extension_contract()
    # Validate each versioned extension once; do not mutate ancestor globals.
    for module in compiler_modules(previous).values():
        contract=vars(module).get('extension_contract')
        if contract is not None:contract()
    result=isolated_compiler(core,runtime_bridge=BRIDGE).simulate_batch(battles,timeout=timeout)
    result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v117',
      'lightning_interleaving_evidence_sha256':PROOF_SHA,'training_label_allowed':False}
    return result
