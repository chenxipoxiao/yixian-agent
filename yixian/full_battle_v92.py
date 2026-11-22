"""Two source-derived Dream families over the frozen v91 compiler."""
import hashlib,json
from pathlib import Path
from . import full_battle_v91 as previous
from . import full_battle_v80 as core
from .combat_compiler_view_v81 import isolated_compiler,compiler_modules
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-dream-intent-water-v92.json'
PROOF_SHA='ddab310cc13e925d219c7efa52c812170ba86a36077e867b2fa2aa6cd0d3ac49'
BRIDGE=ROOT/'tools/full_battle_bridge_v92.mjs'
UnresolvedBattle=previous.UnresolvedBattle
def catalogue():
    facts=extension_contract();cards,mapping,talents,season=previous.catalogue()
    for c in facts['cards']:
        if c['raw_id'] in mapping or c['runtime_id'] in mapping.values():raise UnresolvedBattle('dream_v92:mapping_collision')
        mapping[c['raw_id']]=c['runtime_id']
    return cards,mapping,talents,season
derive_start_initiative=previous.derive_start_initiative
def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('dream_intent_water_v92:evidence_changed')
    facts=json.loads(raw)
    for p,h in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('dream_intent_water_v92:source_changed:'+p)
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
    result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v92',
      'dream_intent_water_evidence_sha256':PROOF_SHA,'training_label_allowed':False}
    return result
