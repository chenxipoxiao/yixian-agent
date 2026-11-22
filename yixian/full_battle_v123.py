"""7120 force capacity and palm consumption; original-source checks stay intact."""
from copy import deepcopy
from pathlib import Path
from types import FunctionType
import hashlib,json
from . import full_battle_v122r2 as previous
from . import full_battle_v80 as core
from .full_battle_base_v123 import compile_start as compile_7120_leaf
from .combat_compiler_view_v81 import isolated_compiler,compiler_modules
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-upper-ancient-v123.json'
PROOF_SHA='f13f829354c296ac72ee222d4d4af3a137c71113807481b7ce6b1ae313157f8f'
BRIDGE=ROOT/'tools/full_battle_bridge_v123.mjs'
UnresolvedBattle=previous.UnresolvedBattle
catalogue=previous.catalogue
derive_start_initiative=previous.derive_start_initiative
def extension_contract():
 raw=PROOF.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('upper_ancient_v123:evidence_changed')
 facts=json.loads(raw)
 for n,h in facts['source_sha256'].items():
  if hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('upper_ancient_v123:source_changed:'+n)
 return facts
def owns_upper_ancient(row):
 return any(7120 in p['candidate_start'].get('xian_mo_strategies',[]) for p in row['players'])
def compile_start(row,**kwargs):
 extension_contract()
 if not owns_upper_ancient(row):return previous.compile_start(row,**kwargs)
 return compile_owned_start(row,**kwargs)
def compile_owned_start(row,**kwargs):
 owners=[]
 for p in row['players']:
  ids=p['candidate_start'].get('xian_mo_strategies')
  if not isinstance(ids,list) or any(type(x) is not int for x in ids) or len(ids)!=len(set(ids)):raise UnresolvedBattle('upper_ancient_v123:explicit_unique_ownership_required')
  owners.append(7120 in ids)
 if 'cloud_sword_record' in (kwargs.get('combat_context') or {}):raise UnresolvedBattle('upper_ancient_v123:cloud_leaf_combination_pending')
 # Rebind the narrowly changed leaf to private globals. Subsequent isolated
 # ancestors retain their PERMANENT_FIELDS changes and all original row bindings.
 view=isolated_compiler(previous);leaf=compiler_modules(view)['yixian.full_battle']
 fn=FunctionType(compile_7120_leaf.__code__,vars(leaf),'compile_start',compile_7120_leaf.__defaults__)
 fn.__kwdefaults__=deepcopy(compile_7120_leaf.__kwdefaults__);leaf.compile_start=fn
 result=view.compile_start(row,**kwargs)
 if result['context'].get('resonance_selected')!=0:raise UnresolvedBattle('upper_ancient_v123:no_resonance_required')
 result['battle']['upper_ancient']={'players':owners}
 result['upper_ancient_context_v123']={'evidence_sha256':PROOF_SHA,'original_start_preserved':True,'opening_force_preadded':False,'training_label_allowed':False}
 return result
def simulate_batch(battles,*,timeout=90):
 extension_contract()
 for module in compiler_modules(previous).values():
  contract=vars(module).get('extension_contract')
  if contract is not None:contract()
 result=isolated_compiler(core,runtime_bridge=BRIDGE).simulate_batch(battles,timeout=timeout)
 result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v123','upper_ancient_evidence_sha256':PROOF_SHA,'training_label_allowed':False}
 return result
