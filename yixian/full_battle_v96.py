"""Current Crash Fist Shatter attack values over frozen v96."""
import hashlib,json
from pathlib import Path
from . import full_battle_v95 as previous
from . import full_battle_v80 as core
from .combat_compiler_view_v81 import isolated_compiler,compiler_modules
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-bow-raven-v96.json'
PROOF_SHA='2376d52efa55e907d15db8af168e90f3f98c41b575766ddd9b43b1db8c5a41da'
BRIDGE=ROOT/'tools/full_battle_bridge_v96.mjs'
UnresolvedBattle=previous.UnresolvedBattle
def catalogue():
    extension_contract()
    return previous.catalogue()

derive_start_initiative=previous.derive_start_initiative
def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('bow-raven_v96:evidence_changed')
    facts=json.loads(raw)
    for p,h in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('bow-raven_v96:source_changed:'+p)
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
    result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v96',
      'bow-raven_evidence_sha256':PROOF_SHA,'training_label_allowed':False}
    return result
