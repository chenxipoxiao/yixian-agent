"""Current Crash Fist Shatter attack values over frozen v95."""
import hashlib,json
from pathlib import Path
from . import full_battle_v94 as previous
from . import full_battle_v80 as core
from .combat_compiler_view_v81 import isolated_compiler,compiler_modules
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-shatter-v95.json'
PROOF_SHA='e3e0c5df2f32839601bd9a91c37592a83617470b3ac30cbcf5a3ebe5daa939c3'
BRIDGE=ROOT/'tools/full_battle_bridge_v95.mjs'
UnresolvedBattle=previous.UnresolvedBattle
def catalogue():
    extension_contract()
    return previous.catalogue()

derive_start_initiative=previous.derive_start_initiative
def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('shatter_v95:evidence_changed')
    facts=json.loads(raw)
    for p,h in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('shatter_v95:source_changed:'+p)
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
    result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v95',
      'shatter_evidence_sha256':PROOF_SHA,'training_label_allowed':False}
    return result
