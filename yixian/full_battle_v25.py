"""Admit explicit3005 stored speed without replaying acquisition."""
from copy import deepcopy
import hashlib,json
from pathlib import Path
from . import full_battle_v24 as v24
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-season-speed-v25.json'
PROOF_SHA='98528a297ba3671ba1f3337fc3c260a6da5abd7366a69f235db9e65cc8664d73'
UnresolvedBattle=v24.UnresolvedBattle
catalogue=v24.catalogue

def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Season speed evidence changed')
    facts=json.loads(raw)
    for p,h in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('Season speed source changed:'+p)
    return facts

def _owned_speed(row):
    owned=[]
    for player in row['players']:
        start=player['candidate_start'];choices=start.get('xian_mo_strategies')
        if not isinstance(choices,list) or any(type(x) is not int for x in choices):
            raise UnresolvedBattle('Explicit xian_mo_strategies array required')
        has=3005 in choices;owned.append(has)
        if has:
            if choices.count(3005)!=1:raise UnresolvedBattle('Duplicate Dragon Rend the Sky3005')
            permanent=start.get('permanentBuffTempDatas')
            if not isinstance(permanent,dict) or type(permanent.get('10056')) is not int or permanent['10056']!=3:
                raise UnresolvedBattle('season3005_recorded_speed_required:explicit10056=3')
    return owned

def derive_start_initiative(row,*,game_mode=3):
    extension_contract();_owned_speed(row)
    return v24.derive_start_initiative(row,game_mode=game_mode)

def compile_start(row,**kwargs):
    extension_contract();owned=_owned_speed(row);projected=deepcopy(row)
    for player,has in zip(projected['players'],owned):
        if has:
            s=player['candidate_start'];s['xian_mo_strategies']=[x for x in s['xian_mo_strategies'] if x!=3005]
    result=v24.compile_start(projected,**kwargs)
    if any(owned):
        for index,(source,has) in enumerate(zip(row['players'],owned)):
            result['effect_players'][index]['season_choices']=deepcopy(source['candidate_start']['xian_mo_strategies'])
            if has:
                result['declared_components'][index]['season3005_speed']={
                    'strategy_id':3005,'recorded_permanent_id':'10056','recorded_value':3,
                    'initiative_reader':'combat_initiative.derive_displayed_speed',
                    'acquisition_reward_reapplied':False,'combat_buff_created':False,
                    'evidence_sha256':PROOF_SHA}
    return result

def simulate_batch(battles,*,timeout=90):
    extension_contract()
    result=v24.simulate_batch(battles,timeout=timeout)
    result['parent_adapter_contract']=result['adapter_contract']
    result['adapter_contract']={'schema':'complete-single-battle-diagnostic-v25',
        'evidence_sha256':PROOF_SHA,'bridge_unchanged_from_v24':True,'current_content_complete':False}
    return result
