"""Hand-cap preparation state and current Dream Predicament, without source rewrites."""
from copy import deepcopy
from pathlib import Path
import hashlib,json
from . import full_battle_v107 as previous
from . import full_battle_v80 as core
from .combat_compiler_view_v81 import isolated_compiler,compiler_modules
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-hand-cap-dream-v108r3.json'
PROOF_SHA='ca63bb529076460408965f61cfb2b679f10e94b11aa7ac1bd253bfa43a369451'
BRIDGE=ROOT/'tools/full_battle_bridge_v108r3.mjs'
UnresolvedBattle=previous.UnresolvedBattle
derive_start_initiative=previous.derive_start_initiative

def extension_contract():
 raw=PROOF.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('hand_cap_v108r3:evidence_changed')
 facts=json.loads(raw)
 for name,h in facts['source_sha256'].items():
  if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('hand_cap_v108r3:source_changed:'+name)
 return facts

def catalogue():
 extension_contract();cards,mapping,talents,season=previous.catalogue()
 if 348 in mapping or 'D23035' in mapping.values():raise UnresolvedBattle('hand_cap_v108r3:mapping_collision')
 mapping[348]='D23035'
 return cards,mapping,talents,season

def owns_content(row):
 return any('10044' in p['candidate_start'].get('permanentBuffTempDatas',{}) or 348 in p['candidate_start'].get('board',[]) for p in row['players'])

def compile_start(row,**kwargs):
 extension_contract()
 if not owns_content(row):return previous.compile_start(row,**kwargs)
 return compile_content_start(row,**kwargs)

def compile_content_start(row,**kwargs):
 # Keep the full original row for v6/v7 source-bound receipt checks.
 if 'tables' not in kwargs:kwargs['tables']=catalogue()
 values=[]
 for p in row['players']:
  buffs=p['candidate_start'].get('permanentBuffTempDatas')
  if not isinstance(buffs,dict):raise UnresolvedBattle('hand_cap_v108r3:explicit_permanent_map_required')
  present='10044' in buffs;value=buffs.get('10044')
  if present and (type(value) is not int or not -(2**31)<=value<2**31):raise UnresolvedBattle('hand_cap_v108r3:invalid_signed_value')
  values.append({'present':present,'value':value})
 if any(v['present'] for v in values) and isinstance(kwargs.get('combat_context'),dict) and 'cloud_sword_record' in kwargs['combat_context']:
  raise UnresolvedBattle('hand_cap_v108r3:cloud_leaf_combination_pending')
 view=isolated_compiler(previous)
 leaf=compiler_modules(view)['yixian.full_battle']
 leaf.PERMANENT_FIELDS=leaf.PERMANENT_FIELDS|{'10044'}
 result=view.compile_start(row,**kwargs)
 result['hand_cap_dream_context_v108r3']={'evidence_sha256':PROOF_SHA,'permanent10044':deepcopy(values),
  'preparation_effect_reapplied':False,'source_row_rewritten':False,'cross_round_rules_implemented':False,'training_label_allowed':False}
 return result

def simulate_batch(battles,*,timeout=90):
 extension_contract()
 for module in compiler_modules(previous).values():
  contract=vars(module).get('extension_contract')
  if contract is not None:contract()
 result=isolated_compiler(core,runtime_bridge=BRIDGE).simulate_batch(battles,timeout=timeout)
 result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v108r3','evidence_sha256':PROOF_SHA,'training_label_allowed':False}
 return result
