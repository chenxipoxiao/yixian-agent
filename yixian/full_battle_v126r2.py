"""v126 admission plus the source-verified350 identity in chase consumers."""
from pathlib import Path
import hashlib,json
from . import full_battle_v126 as previous
from . import full_battle_v80 as core
from .combat_compiler_view_v81 import isolated_compiler,compiler_modules
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-postbattle-chase-v126r2.json'
PROOF_SHA='44f39cf70e12323bb9aaddc96a390c3eab87f9bd4eedb0eb0b1e1063205f9d15'
BRIDGE=ROOT/'tools/full_battle_bridge_v126r2.mjs'
UnresolvedBattle=previous.UnresolvedBattle
catalogue=previous.catalogue
derive_start_initiative=previous.derive_start_initiative
compile_start=previous.compile_start
def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('postbattle_v126r2:evidence_changed')
    facts=json.loads(raw)
    for n,h in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('postbattle_v126r2:source_changed:'+n)
    return facts
def simulate_batch(battles,*,timeout=90):
    extension_contract()
    for module in compiler_modules(previous).values():
        contract=vars(module).get('extension_contract')
        if contract is not None:contract()
    result=isolated_compiler(core,runtime_bridge=BRIDGE).simulate_batch(battles,timeout=timeout)
    result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v126r2',
        'postbattle_chase_identity_evidence_sha256':PROOF_SHA,'training_label_allowed':False}
    return result
