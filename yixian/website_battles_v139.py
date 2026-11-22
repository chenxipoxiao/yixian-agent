"""Validate owner1010 from the exact website prebattle step, then compile.

No fabricated v77 source projection; no opponent switch defaults. Only1010 is
admitted by the new preparation branch. Card bodies and settlement are frozen.
"""
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import hashlib,json
from . import website_battles_v137r2 as previous
from . import full_battle_v124 as season
from .combat_compiler_view_v81 import compiler_modules
from .combat_website_preparation_v139 import compile_start as website_preparation

ORIGIN=previous.ORIGIN
UnresolvedBattle=previous.UnresolvedBattle

def require(ok,reason):
    if not ok:raise UnresolvedBattle('website_preparation_v139:'+reason)

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def merge(target,patch):
    if not isinstance(patch,dict):return deepcopy(patch)
    out=deepcopy(target) if isinstance(target,dict) else {}
    for key,value in patch.items():
        if isinstance(value,dict) and value.get('$deleted') is True:out.pop(key,None)
        else:out[key]=merge(out.get(key),value)
    return out

@lru_cache(maxsize=128)
def _before(path,sha,step):
    # Caller rehashes the file even on a cache hit.
    raw=json.loads(Path(path).read_text(encoding='utf-8'))
    require(type(step)is int and 1<=step<=len(raw['steps']),'invalid_source_step')
    state={}
    for s in raw['steps'][:step-1]:state=merge(state,s['patch'])
    selected=raw['steps'][step-1]
    require('battle' in selected,'not_authoritative_battle_step')
    return raw['id'],raw['targetUid'],state,selected['battle']

def validate_website_entry(row,index,cp,ids,context):
    require(index==0 and ids==[1010],'only_owner1010_supported')
    require(cp.get('website_hand_unknown') is False,'private_owner_required')
    src=row['source'];entry=cp.get('website_owner_preparation_v137')
    require(isinstance(entry,dict),'receipt_required')
    expected={'origin':ORIGIN,'source_raw_sha256':src['raw_sha256'],'source_step':src['step'],
        'case_id':row['id'],'player_index':0,'environment_only':True}
    require(all(entry.get(k)==v for k,v in expected.items()),'source_binding_mismatch')
    require(context.get('source_raw_sha256')==src['raw_sha256'],'context_source_mismatch')
    p=Path(src['path'])
    require(hashlib.sha256(p.read_bytes()).hexdigest()==src['raw_sha256'],'source_file_changed')
    rid,uid,before,battle=_before(str(p),src['raw_sha256'],src['step'])
    require(row['id']==rid+'/round'+str(row['round']) and before['round']==battle['round']==row['round'],'source_round_mismatch')
    require(any(x.get('authoritative') is True and uid in x.get('players',{}) for x in battle['matchups']),'owner_authority_required')
    private=before.get('privatePlayer')
    require(isinstance(private,dict) and private.get('uid')==uid,'source_private_owner_required')
    require(entry.get('private_state_sha256')==digest(private),'private_state_hash_mismatch')
    choices=private.get('selectedXianMoStrategies')
    require(isinstance(choices,list) and len({x['id'] for x in choices})==len(choices),'source_unique_ownership_required')
    chosen=[x for x in choices if x['id']==1010]
    require(len(chosen)==1 and type(chosen[0].get('locked'))is bool,'source_switch_unknown')
    require(1010 in row['players'][0]['candidate_start']['xian_mo_strategies'],'ownership_mismatch')
    require(1010 in entry.get('selected_strategy_ids',[]),'receipt_ownership_mismatch')
    value=entry.get('parameters',{}).get('1010')
    require(type(value)is int and value in (0,1) and value==int(chosen[0]['locked']),'switch_differs_from_source')
    require(cp.get('website_strategy_parameters',{}).get('1010')==value,'parameter_conflict')
    require(private.get('deck')==row['players'][0]['candidate_start']['board'],'private_board_mismatch')
    require(type(private.get('hand'))is list and cp.get('hand_count')==len(private['hand']),'private_hand_mismatch')
    return {1010:value}

def compiler():
    view=previous.compiler();modules=compiler_modules(view)
    target=modules['yixian.full_battle_v77']
    target._website_validate_1010=validate_website_entry
    target.compile_start=season.rebind(website_preparation,target)
    # v124 creates a per-call view and otherwise overwrites the outer v77 hook.
    modules['yixian.full_battle_v124'].batch_preparation=website_preparation
    return view

def compile_case(case,view,tables):
    previous.validate_owner_parameters(case)
    normalized=previous.normalize_choice_ownership(case)
    p=normalized['row']['players'][0];cp=normalized['combat_context']['players'][0]
    if 1010 in p['candidate_start']['xian_mo_strategies'] and cp.get('website_owner_preparation_v137') is not None:
        require(normalized.get('preparation_owner_verified') is True,'private_owner_required')
        validate_website_entry(normalized['row'],0,cp,[1010],normalized['combat_context'])
    return previous.compile_case(normalized,view,tables)
