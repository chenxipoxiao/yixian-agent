"""Current Diligent Sword timing and Chase Wind values, with frozen starts."""
import hashlib,json
from pathlib import Path
from . import full_battle_v89 as previous
from . import full_battle_v80 as core
from .combat_compiler_view_v81 import isolated_compiler,compiler_modules
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-diligent-chasewind-v90r2.json'
PROOF_SHA='e096f7a9357acd23fed8a715fe7cbc4ab113126eb61f82cbda87630b677ef9d1'
BRIDGE=ROOT/'tools/full_battle_bridge_v90r2.mjs'
UnresolvedBattle=previous.UnresolvedBattle
catalogue=previous.catalogue
derive_start_initiative=previous.derive_start_initiative
def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('diligent_v90r2:evidence_changed')
    facts=json.loads(raw)
    for p,h in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('diligent_v90r2:source_changed:'+p)
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
    result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v90r2',
      'diligent_chasewind_evidence_sha256':PROOF_SHA,'training_label_allowed':False}
    return result
