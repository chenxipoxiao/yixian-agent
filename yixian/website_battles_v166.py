"""Exactly bound second private perspectives for offline battle diagnostics.

The original website adapters validate the original recorder as before. Only
the twenty-one frozen reciprocal boundaries may add a second recorder's
prefix-only hand, vase and five explicit sound switches. No policy observation
or counterfactual continuation receives these private inputs.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import hashlib,json,inspect,importlib

from . import website_battles_v163r2 as previous
from .website_battles_v139 import _before,digest
from .website_battles_v132 import replace_function
from .combat_compiler_view_v81 import compiler_modules

ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/website-cross-perspective-v166.json'
PROOF_SHA='c0324f8bbf1b6ed02e144874d90addb0978b7e7ea2cf92d52e1ecf340f593fae'
ORIGIN=previous.ORIGIN
CROSS_ORIGIN='website:two-source-reciprocal-prebattle-private-owners:v166'
UnresolvedBattle=previous.UnresolvedBattle
SUPPORTED={1001,1002,1006,1007,1008}
FIELDS=['uid','opponentUid','characterId','phase','cultivation','speed','physique','maxPhysique','lifeBefore','first','talents','fateStrategies','xianMoStrategies','battleBuffs','enlightenedCards','deck']

def require(ok,why):
    if not ok:raise UnresolvedBattle('website_cross_v166:'+why)

def facts():
    raw=PROOF.read_bytes()
    require(hashlib.sha256(raw).hexdigest()==PROOF_SHA,'evidence_changed')
    return json.loads(raw)

def extension_contract():
    value=facts()
    require(value['schema']=='website-two-private-owner-prefixes-v166' and len(value['bindings'])==21,'binding_contract_changed')
    for path,h in value['source_sha256'].items():
        require(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==h,'prior_source_changed:'+path)
    return value

def _projection(p):return {k:p[k] for k in FIELDS if k in p}

def validate_binding(case):
    proof=extension_contract();binding=proof['bindings'].get(case['row']['id'])
    require(binding is not None,'unregistered_pair')
    require(digest(case)==binding['case_sha256'],'original_case_changed')
    row=case['row'];ctx=case['combat_context'];src=row['source'];other=binding['candidate_source'];b=binding['binding']
    require(src==binding['primary_source'],'primary_source_changed')
    paths=[Path(src['path']),Path(other['path'])]
    for path,h in zip(paths,[src['raw_sha256'],other['sha256']]):
        require(hashlib.sha256(path.read_bytes()).hexdigest()==h,'source_bytes_changed')
    rid,owner,before,battle=_before(str(paths[0]),src['raw_sha256'],src['step'])
    oid,opponent,ob,bb=_before(str(paths[1]),other['sha256'],binding['candidate_step'])
    require(rid!=oid and owner!=opponent and oid==binding['candidate_recording'],'distinct_source_owners_required')
    require(row['id']==rid+'/round'+str(row['round']) and row['round']==b['round']==before['round']==ob['round']==battle['round']==bb['round'],'source_round_mismatch')
    require(all(s.get('gameMode')==3 and s.get('seasonMechanic')==10 for s in [before,ob]),'mode_outside_scope')
    require(ctx.get('game_mode')==3 and ctx.get('season_mec')==10 and all(p.get('is_mirror') is False for p in ctx['players']),'context_mode_or_mirror')
    require(digest(before)==b['primary_prebattle_sha256'] and digest(ob)==b['candidate_prebattle_sha256'],'prefix_changed')
    require(digest(owner)==b['primary_owner_uid_sha256'] and digest(opponent)==b['candidate_owner_uid_sha256'],'owner_binding_changed')
    pair=[]
    for value,uid in [(battle,owner),(bb,opponent)]:
        matches=[m for m in value['matchups'] if m.get('authoritative') is True and uid in m.get('players',{})]
        require(len(matches)==1 and set(matches[0]['players'])=={owner,opponent},'unique_reciprocal_pair_required')
        pair.append(matches[0]['players'])
    a,c=pair
    require({k:_projection(v) for k,v in a.items()}=={k:_projection(v) for k,v in c.items()},'battle_start_differs')
    require(digest({k:_projection(v) for k,v in sorted(a.items())})==b['battle_start_projection_sha256'],'battle_projection_changed')
    for i,uid in enumerate([owner,opponent]):
        start=row['players'][i]['candidate_start'];p=a[uid]
        require(p.get('opponentUid')==[opponent,owner][i] and p.get('innerDemon') is not True and type(p.get('lifeBefore'))is int and p['lifeBefore']>0,'mirror_or_invalid_pair')
        require(row['players'][i]['character_id']==p['characterId'] and start['board']==p['deck'] and start['level']==p['phase'] and start['exp']==p['cultivation'],'original_player_changed')
        hp=before['players'][uid].get('extraMaxHp')
        require(type(hp)is int and hp==ob['players'][uid].get('extraMaxHp')==start['extra_max_hp_modifier'],'extra_max_hp_differs')
    private=ob.get('privatePlayer')
    require(isinstance(private,dict) and private.get('uid')==opponent and digest(private)==b['candidate_private_sha256'],'private_owner_or_prefix_changed')
    require(private.get('deck')==a[opponent]['deck'],'private_board_changed')
    hand=private.get('hand');require(type(hand)is list and len(hand)==b['candidate_hand_count'] and all(type(c)is int and c>=0 for c in hand),'explicit_hand_required')
    choices=private.get('selectedXianMoStrategies')
    require(type(choices)is list and all(type(x)is dict and type(x.get('id'))is int for x in choices),'explicit_strategies_required')
    ids=[x['id'] for x in choices]
    require(len(ids)==len(set(ids)) and ids==b['candidate_strategy_ids'] and set(ids)=={x['id'] for x in a[opponent]['xianMoStrategies']},'private_ownership_differs')
    for x in choices:
        if x['id'] in SUPPORTED:require(type(x.get('locked'))is bool,'explicit_switch_required')
    if 199 in row['players'][1]['candidate_start']['talents']:
        slots=private.get('cardStorage',{}).get('199')
        require(type(slots)is list and len(slots) in [0,3] and all(type(x)is int and x>=0 for x in slots),'explicit_vase_required')
    return binding,private

def _cross_origin(data,context,row,seat,old_origin):
    if data.get('origin')==old_origin:return True
    if data.get('origin')!=CROSS_ORIGIN:return False
    b=facts()['bindings'].get(row['id'])
    require(b is not None and seat==1,'unregistered_switch_owner')
    receipt=context['players'][seat].get('cross_perspective_v166')
    require(receipt=={'proof_sha256':PROOF_SHA,**b['binding']},'joint_receipt_changed')
    require(data.get('private_source_sha256')==b['candidate_source']['sha256'] and data.get('private_source_step')==b['candidate_step'],'switch_source_changed')
    require(data.get('source_raw_sha256')==b['primary_source']['raw_sha256'] and data.get('case_id')==row['id'],'switch_battle_binding_changed')
    values=data.get('temp_data');ids=data.get('selected_strategy_ids')
    require(type(ids)is list and bool(ids) and set(ids)<=SUPPORTED and type(values)is dict and set(values)=={str(x) for x in ids} and all(type(v)is int and v in [0,1] for v in values.values()),'explicit_switch_map_required')
    return True

def compiler():
    extension_contract();view=previous.compiler();modules=compiler_modules(view)
    for name,old_origin in [('yixian.full_battle_v34',ORIGIN),('yixian.full_battle_v36','privateData.xianMoData:preparation_switch'),
                            ('yixian.full_battle_v51r2','privateData.xianMoData:preparation_switch'),('yixian.full_battle_v52r2',ORIGIN)]:
        module=modules[name];module._cross_origin_v166=_cross_origin
        source=inspect.getsource(importlib.import_module(name).compile_start)
        if old_origin==ORIGIN:
            source=source.replace('privateData.xianMoData:preparation_switch',ORIGIN)
        anchor="data.get('origin')!="+repr(old_origin)
        require(source.count(anchor)==1,'consumer_origin_anchor_changed:'+name)
        source=source.replace(anchor,"not _cross_origin_v166(data,context,row,i,"+repr(old_origin)+")")
        exec(compile(source,__file__,'exec'),vars(module))
    return view

def _inject_context(context,row,binding,private):
    result=deepcopy(context);cp=result['players'][1];choices={x['id']:x for x in private['selectedXianMoStrategies']}
    require(cp.get('website_strategy_parameters',{})=={},'opponent_parameters_already_supplied')
    require(cp.get('sound_control_switch') is None and cp.get('heaven_spirit_switch') is None and cp.get('killing_sound_switch') is None and cp.get('wild_dance_switch') is None,'opponent_receipt_already_supplied')
    cp['hand_count']=len(private['hand']);cp['website_hand_unknown']=False
    cp['cross_perspective_v166']={'proof_sha256':PROOF_SHA,**binding['binding']}
    for sid in choices.keys()&SUPPORTED:cp['website_strategy_parameters'][str(sid)]=int(choices[sid]['locked'])
    for key,ids in [('heaven_spirit_switch',{1001}),('wild_dance_switch',{1002}),('killing_sound_switch',{1006}),('sound_control_switch',{1007})]:
        owned=sorted(choices.keys()&ids)
        if not owned:continue
        cp[key]={'origin':CROSS_ORIGIN,'source_raw_sha256':row['source']['raw_sha256'],'case_id':row['id'],
            'private_source_sha256':binding['candidate_source']['sha256'],'private_source_step':binding['candidate_step'],
            'player_index':1,'environment_only':True,'selected_strategy_ids':owned,'temp_data':{str(x):int(choices[x]['locked']) for x in owned}}
    if 199 in row['players'][1]['candidate_start']['talents']:
        cp['start_extensions']['privateTalentDatas']['199']={'commonParams':deepcopy(private['cardStorage']['199'])}
    return result

def compile_case(case,view,tables):
    if case['row']['id'] not in facts()['bindings']:return previous.compile_case(case,view,tables)
    binding,private=validate_binding(case);projected=deepcopy(case)
    # The existing neutral-vase validator runs before the compiler; provide
    # only this already checked metadata at that boundary. All switch inputs
    # enter after the old recorder's source and choice validators have run.
    if 199 in projected['row']['players'][1]['candidate_start']['talents']:
        projected['combat_context']['players'][1]['start_extensions']['privateTalentDatas']['199']={'commonParams':deepcopy(private['cardStorage']['199'])}
    calls=[]
    def compile_with_second_owner(row,**kwargs):
        require(row['source']==case['row']['source'] and row['id']==case['row']['id'],'compiler_source_changed')
        require(row['players'][1]==case['row']['players'][1],'upstream_opponent_projection_outside_scope')
        context=_inject_context(kwargs['combat_context'],row,binding,private);calls.append(True)
        return view.compile_start(row,**{**kwargs,'combat_context':context})
    result=previous.compile_case(projected,SimpleNamespace(compile_start=compile_with_second_owner),tables)
    require(calls==[True],'single_compiler_boundary_required')
    result['website_cross_perspective_v166']={'proof_sha256':PROOF_SHA,'binding':deepcopy(binding['binding']),
        'hand_count':len(private['hand']),'vase_slots':deepcopy(private.get('cardStorage',{}).get('199')),
        'explicit_switches':{str(x['id']):int(x['locked']) for x in private['selectedXianMoStrategies'] if x['id'] in SUPPORTED},
        'policy_observation_allowed':False,'counterfactual_reuse_allowed':False,'training_label_allowed':False,
        'source_rule_version_certified':False,'outcome_fields_used_as_input':False}
    return result
