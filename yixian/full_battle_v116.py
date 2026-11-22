"""Lightning Repeat three grades over the frozen v115 compiler."""
import hashlib,json
from pathlib import Path
from . import full_battle_v115 as previous
from . import full_battle_v80 as core
from .combat_compiler_view_v81 import isolated_compiler,compiler_modules
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-lightning-repeat-v116.json'
PROOF_SHA='74ea1d178f6c35aa6fd5c4f68d69c1062f9adacb634644224512568f0843c51b'
BRIDGE=ROOT/'tools/full_battle_bridge_v116.mjs'
UnresolvedBattle=previous.UnresolvedBattle
def catalogue():
    facts=extension_contract();cards,mapping,talents,season=previous.catalogue()
    for c in facts['cards']:
        if c['raw_id'] in mapping or c['runtime_id'] in mapping.values():raise UnresolvedBattle('lightning_repeat_v116:mapping_collision')
        mapping[c['raw_id']]=c['runtime_id']
    return cards,mapping,talents,season
derive_start_initiative=previous.derive_start_initiative
def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('lightning_repeat_v116:evidence_changed')
    facts=json.loads(raw)
    for p,h in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('lightning_repeat_v116:source_changed:'+p)
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
    result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v116',
      'lightning_repeat_evidence_sha256':PROOF_SHA,'training_label_allowed':False}
    return result
