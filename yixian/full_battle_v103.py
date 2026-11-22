"""Current7076 positive recovery/maxHP; preserve all prior nonowner paths."""
from copy import deepcopy
import hashlib,json
from pathlib import Path
from . import full_battle_v102 as previous
from . import full_battle_v80 as core
from .combat_compiler_view_v81 import isolated_compiler,compiler_modules
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-positive-growth-v103.json'
PROOF_SHA='f2851ebda4cf6b3405bcd3a27aa74ce241629d10ccdefa7fdfa3fe9c9fa6ce71'
BRIDGE=ROOT/'tools/full_battle_bridge_v103.mjs'
UnresolvedBattle=previous.UnresolvedBattle
catalogue=previous.catalogue
derive_start_initiative=previous.derive_start_initiative
def extension_contract():
 raw=PROOF.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('positive_growth_v103:evidence_changed')
 facts=json.loads(raw)
 for n,h in facts['source_sha256'].items():
  if hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('positive_growth_v103:source_changed:'+n)
 return facts
def owns_growth(row):
 return any(7076 in p['candidate_start'].get('xian_mo_strategies',[]) for p in row['players'])
def compile_start(row,**kwargs):
 extension_contract()
 if not owns_growth(row):return previous.compile_start(row,**kwargs)
 return compile_growth_start(row,**kwargs)
def compile_growth_start(row,**kwargs):
 projected=deepcopy(row);owners=[]
 for p in projected['players']:
  start=p['candidate_start'];ids=start.get('xian_mo_strategies');fates=start.get('fate_strategies')
  if not isinstance(ids,list) or any(type(x) is not int for x in ids) or len(ids)!=len(set(ids)):raise UnresolvedBattle('positive_growth_v103:explicit_unique_ownership_required')
  owned=7076 in ids;owners.append(owned)
  if owned:
   if 7053 in ids:raise UnresolvedBattle('positive_growth_v103:yan_qi_combination_pending')
   if not isinstance(fates,list) or 394 in fates:raise UnresolvedBattle('positive_growth_v103:fate394_combination_pending')
   start['xian_mo_strategies']=[x for x in ids if x!=7076]
 result=previous.compile_start(projected,**kwargs)
 if result['context'].get('resonance_selected')!=0:raise UnresolvedBattle('positive_growth_v103:no_resonance_required')
 result['battle']['positive_growth']={'players':owners}
 for i,p in enumerate(row['players']):result['effect_players'][i]['season_choices']=deepcopy(p['candidate_start']['xian_mo_strategies'])
 result['positive_growth_context_v103']={'evidence_sha256':PROOF_SHA,'origin':'candidate_start.xian_mo_strategies','opening_hp_preadded':False,'acquisition_rewards_reapplied':False,'training_label_allowed':False}
 return result
def simulate_batch(battles,*,timeout=90):
 extension_contract()
 for module in compiler_modules(previous).values():
  contract=vars(module).get('extension_contract')
  if contract is not None:contract()
 result=isolated_compiler(core,runtime_bridge=BRIDGE).simulate_batch(battles,timeout=timeout)
 result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v103','evidence_sha256':PROOF_SHA,'training_label_allowed':False}
 return result
