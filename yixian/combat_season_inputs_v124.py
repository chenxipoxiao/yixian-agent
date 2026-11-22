"""Original-start private season inputs, kept outside policy observations."""
from copy import deepcopy
from .full_battle_v45 import digest_json,snapshot_binding
from .combat_start_context_bindings_v6 import REVIEW_SHA,integer_ids
SWITCH_IDS={1004,1008,1010,5010,7031,7036,7094,7116,23069}
GRID_IDS={13005,13010,13011,13012,13014,13018}
INPUT_IDS=SWITCH_IDS|GRID_IDS

def require(ok,why):
 if not ok:raise ValueError('season_batch_input_v124:'+why)

def bind_inputs(turn,source,row,context):
 require(source['split']==row['split']=='train','training_source')
 require(source['raw_sha256']==row['source']['raw_sha256']==context['source_raw_sha256'],'raw_source')
 require(source['game_id']==row['game_id']==context['game_id'],'game')
 require(turn['round']==row['round'],'round')
 result={'schema':'season-battle-inputs-v124','record_id':row['id'],'game_id':row['game_id'],
  'round':row['round'],'source_raw_sha256':source['raw_sha256'],'archive':source['archive'],'member':source['member'],
  'snapshot_sha256':snapshot_binding(row,context),'reader_review_sha256':REVIEW_SHA,
  'source_path':'RecentBattleInfo.roundStats[round].p1/p2.privateData.xianMoData.tempDatas',
  'environment_only':True,'policy_observation_allowed':False,'counterfactual_reuse_allowed':False,'players':[]}
 for i,slot in enumerate(('p1','p2')):
  owner=row['players'][i]['candidate_start']['xian_mo_strategies']
  require(integer_ids(owner) and turn[slot]['publicData']['lastRoundData']['xianMoStrategies']==owner,'start_ownership')
  private=turn[slot].get('privateData',{}).get('xianMoData')
  require(isinstance(private,dict) and isinstance(private.get('tempDatas'),dict),'explicit_complete_temp_map')
  selections=private.get('strategies')
  require(isinstance(selections,list) and all(isinstance(x,dict) for x in selections),'private_selections')
  selected=[x.get('selected') for x in selections]
  require(integer_ids(selected) and set(selected)==set(owner),'private_start_ownership')
  temp=private['tempDatas'];ids=sorted(INPUT_IDS.intersection(owner))
  present={str(x):temp[str(x)] for x in ids if str(x) in temp}
  require(all(type(v) is int and -(2**31)<=v<2**31 for v in present.values()),'signed_values')
  require(all(0<=v<8 for k,v in present.items() if int(k) in GRID_IDS),'grid_range')
  result['players'].append({'snapshot_slot':slot,'start_owned_ids':deepcopy(owner),'selected_strategy_ids':ids,
   'present_values':present,'absent_keys':[str(x) for x in ids if str(x) not in temp],
   'complete_temp_map_present':True,'complete_temp_map_sha256':digest_json(temp),'private_ownership_matches_start':True})
 return result

def validate_inputs(row,context,receipt):
 require(isinstance(receipt,dict) and receipt['schema']=='season-battle-inputs-v124','receipt_schema')
 require(receipt['snapshot_sha256']==snapshot_binding(row,context),'start_changed')
 require(receipt['reader_review_sha256']==REVIEW_SHA,'reader_contract')
 require(receipt['record_id']==row['id'] and receipt['round']==row['round'] and receipt['game_id']==row['game_id']==context['game_id'],'record_binding')
 require(receipt['source_raw_sha256']==row['source']['raw_sha256']==context['source_raw_sha256'],'raw_source')
 require(receipt['environment_only'] is True and receipt['policy_observation_allowed'] is False and receipt['counterfactual_reuse_allowed'] is False,'scope')
 require(row['split']=='train' and len(receipt['players'])==2,'training_players')
 values=[]
 for i,p in enumerate(receipt['players']):
  owner=row['players'][i]['candidate_start']['xian_mo_strategies'];ids=sorted(INPUT_IDS.intersection(owner))
  require(integer_ids(owner) and p['start_owned_ids']==owner and p['selected_strategy_ids']==ids,'ownership')
  require(p['snapshot_slot']==row['players'][i]['snapshot_slot']==context['players'][i]['snapshot_slot'],'seat')
  require(p['complete_temp_map_present'] is True and p['private_ownership_matches_start'] is True,'complete_map')
  present=p['present_values'];absent=p['absent_keys']
  require(isinstance(present,dict) and isinstance(absent,list) and absent==sorted(set(absent)) and not set(present)&set(absent) and set(present)|set(absent)=={str(x) for x in ids},'key_presence')
  require(all(type(v) is int and -(2**31)<=v<2**31 for v in present.values()),'signed_values')
  require(all(0<=v<8 for k,v in present.items() if int(k) in GRID_IDS),'grid_range')
  if 'original_preparation_v6' in context:
   require(context['original_preparation_v6']['players'][i]['complete_temp_map_sha256']==p['complete_temp_map_sha256'],'legacy_map_changed')
  values.append({x:present.get(str(x),0) for x in ids})
 return values
