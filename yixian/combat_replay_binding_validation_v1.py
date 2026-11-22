"""Review explicit record-bound FIFO additions over unchanged physical starts."""
from copy import deepcopy
import hashlib
from .combat_report_comparison_v1 import cases_equal
from .combat_validation_batch_v9 import terminal

def select_bound_records(rows, admitted, *, control_count=4):
 ids=[r['id'] for r in rows]
 if len(ids)!=len(set(ids)) or any(r.get('split')!='train' for r in rows):raise ValueError('Training-source rows only')
 if not set(admitted).issubset(ids):raise ValueError('Binding source missing')
 targets=[rid for rid in ids if rid in admitted]
 controls=sorted((rid for rid in ids if rid not in admitted),key=lambda rid:hashlib.sha256(('batch-control-v1:'+rid).encode()).hexdigest())[:control_count]
 return {'target_record_ids':targets,'control_record_ids':controls,'selected_record_ids':[rid for rid in ids if rid in set(targets+controls)],
  'selection_reasons':{rid:['exact_original_start_binding' if rid in admitted else 'fixed_unrelated_control'] for rid in targets+controls},
  'full_required_by_scope':False,'full_scope_changes':[],'unselected_count':len(ids)-len(targets)-len(controls),
  'selection_is_dependency_proof':False,'release_requires_full_pass':True}

def review_case(old,new,*,selected):
 if cases_equal(old,new):return {'allowed':True,'kind':'identical'}
 if not selected:return {'allowed':False,'kind':'unselected_changed'}
 compiled=deepcopy(new['compiled'])
 metadata=compiled.pop('replay_parameter_context_v97',None)
 parameter=compiled['battle'].pop('replay_parameters',None)
 if not metadata or not parameter or not cases_equal({'compiled':old['compiled']},{'compiled':compiled}):
  return {'allowed':False,'kind':'physical_start_changed'}
 if old['simulation']['initial']!=new['simulation']['initial']:return {'allowed':False,'kind':'runtime_initial_changed'}
 for key in ['record_id','game_id','round','expected','initiative','initiative_matches_record']:
  if old[key]!=new[key]:return {'allowed':False,'kind':'comparison_changed'}
 before,after=terminal(old),terminal(new)
 if old['all_four_match'] and (before!=after or old['settlement']!=new['settlement']):
  return {'allowed':False,'kind':'previous_matched_terminal_changed'}
 trace=new['simulation'].get('replay_parameters_v97')
 if not trace or trace['consumed']!=trace['total_parameters']:return {'allowed':False,'kind':'unverified_stream'}
 return {'allowed':True,'kind':'original_record_parameters','before':before,'after':after,
  'previous_all_four_match':old['all_four_match'],'current_all_four_match':new['all_four_match'],
  'settlement_unchanged':old['settlement']==new['settlement'],'previous_trace_unchanged':old['simulation']['trace']==new['simulation']['trace'],
  'parameter_count':trace['consumed'],'reader_mode':trace['reader_mode']}
