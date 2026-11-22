"""Allow only a bound, additive flag-hand context before targeted + full checking."""
from copy import deepcopy
import json
from pathlib import Path
from . import combat_validation_batch as v1
from .combat_validation_batch import *

def validate_flag_context(rows,old,new,selected):
 if set(old)!=set(new):raise ValueError('Context record set changed')
 projected=deepcopy(new);added=[]
 for row in rows:
  rid=row['id']
  if not isinstance(projected[rid].get('players'),list) or len(projected[rid]['players'])!=2:raise ValueError('Both context players required')
  for i,p in enumerate(projected[rid]['players']):
   if 'element_flag_hand' not in p:continue
   if 'element_flag_hand' in old[rid]['players'][i]:raise ValueError('Existing hand cannot change')
   h=p.pop('element_flag_hand');board=row['players'][i]['candidate_start']['board']
   if rid not in selected or not any(c in [7000111,7010111,7020111] for c in board):raise ValueError('Hand outside targeted flag owner')
   if h.get('record_id')!=rid or h.get('round')!=row['round'] or h.get('board')!=board or h.get('source_raw_sha256')!=row['source']['raw_sha256'] or h.get('origin')!='publicData.lastRoundData.handCards' or h.get('environment_only') is not True:raise ValueError('Unbound opening hand')
   if not isinstance(h.get('raw_cards'),list) or len(h['raw_cards'])!=p['hand_count'] or any(type(c) is not int for c in h['raw_cards']):raise ValueError('Invalid opening hand')
   added.append({'record_id':rid,'player_index':i})
 if projected!=old:raise ValueError('Only additive element_flag_hand is allowed')
 if not added:raise ValueError('Expected new flag-hand context')
 return added

def create_plan(root,*,previous_context=None,**kwargs):
 if previous_context is None:return v1.create_plan(root,**kwargs)
 root=Path(root);context=Path(kwargs['context']);context=context if context.is_absolute() else root/context
 oldpath=root/previous_context
 spec={**kwargs,'context':oldpath};plan=v1.create_plan(root,**spec)
 rows,new,previous=v1.load_sources(root/plan['pilot'],context,root/plan['baseline'])
 old=json.loads(oldpath.read_text('utf8'));selection=v1.select_records(rows,new,kwargs['changes'],control_count=kwargs.get('control_count',4))
 added=validate_flag_context(rows,old,new,selection['target_record_ids'])
 plan.update(context=context.resolve().relative_to(root.resolve()).as_posix(),context_sha256=v1.digest(context),selection=selection,
  additive_context={'previous_context':previous_context,'previous_sha256':v1.digest(oldpath),'additions':added})
 if 'yixian/combat_validation_batch_v2.py' not in plan['candidate_sources']:raise ValueError('Freeze additive validator')
 return plan

def run_plan(root,plan,*,full=False):
 if 'additive_context' in plan:
  root=Path(root);a=plan['additive_context'];p=root/a['previous_context']
  if v1.digest(p)!=a['previous_sha256']:raise ValueError('Previous context changed')
  rows,new,_=v1.load_sources(root/plan['pilot'],root/plan['context'],root/plan['baseline'])
  if validate_flag_context(rows,json.loads(p.read_text('utf8')),new,plan['selection']['target_record_ids'])!=a['additions']:raise ValueError('Additive context changed')
 return v1.run_plan(root,plan,full=full)
