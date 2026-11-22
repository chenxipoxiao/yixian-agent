"""Source-only counter-update windows, never battle inputs or match continuation.

An endpoint is selected by a recorded one-game counter transition, not a
predicted balance. It may contain automatic new-round rewards. Equality is a
conditional timing observation and cannot establish pure battle causality.
"""
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import hashlib,json

def merge(target,patch):
    if not isinstance(patch,dict):return deepcopy(patch)
    out=deepcopy(target) if isinstance(target,dict) else {}
    for key,value in patch.items():
        if isinstance(value,dict) and value.get('$deleted') is True:out.pop(key,None)
        else:out[key]=merge(out.get(key),value)
    return out

@lru_cache(maxsize=32)
def _load(path,digest):
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('website_window_v146:source_changed')
    record=json.loads(raw);state={};states=[]
    for step in record['steps']:
        state=merge(state,step['patch']);states.append(state)
    return record,states

def _stats(player):
    values=[player.get('wins'),player.get('losses')]
    if any(type(x)is not int or x<0 for x in values):return None
    return values

def observe_counter_window(row,max_steps=32):
    if type(max_steps)is not int or not 1<=max_steps<=32:raise ValueError('website_window_v146:bounded_window_required')
    src=row['source'];path=str(Path(src['path']).resolve())
    if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=src['raw_sha256']:raise ValueError('website_window_v146:source_changed')
    record,states=_load(path,src['raw_sha256']);n=src['step']
    if type(n)is not int or not 2<=n<=len(states):raise ValueError('website_window_v146:invalid_step')
    selected=record['steps'][n-1];battle=selected.get('battle');uid=record['targetUid']
    if not isinstance(battle,dict) or row['id']!=record['id']+'/round'+str(battle['round']):raise ValueError('website_window_v146:case_binding_mismatch')
    matchups=[m for m in battle['matchups'] if m.get('authoritative') is True and uid in m.get('players',{})]
    if len(matchups)!=1:raise ValueError('website_window_v146:owner_authority_required')
    pair=matchups[0]['players'];owner=pair[uid];other=owner['opponentUid'];ids=[uid,other]
    if other not in pair or pair[other]['opponentUid']!=uid:raise ValueError('website_window_v146:pair_binding_mismatch')
    before=states[n-2];base=[before['players'][u] for u in ids]
    stats=[_stats(p) for p in base];life=[p.get('life') for p in base]
    results=[pair[u]['result'] for u in ids]
    if any(s is None for s in stats) or any(type(v)is not int for v in life):raise ValueError('website_window_v146:explicit_before_required')
    if any(pair[u]['lifeBefore']!=v for u,v in zip(ids,life)):raise ValueError('website_window_v146:before_balance_conflict')
    if sorted(results)!=['loss','win']:raise ValueError('website_window_v146:binary_result_required')
    expected=[[s[0]+int(r=='win'),s[1]+int(r=='loss')] for s,r in zip(stats,results)]
    endpoints=[None,None];events=[];stop='window_exhausted';private_fields=set()
    for j in range(n-1,min(n-1+max_steps,len(states))):
        step=record['steps'][j];state=states[j]
        if j>n-1 and any(m.get('authoritative') is True and any(u in m.get('players',{}) for u in ids)
                for m in step.get('battle',{}).get('matchups',[])):
            stop='next_authoritative_battle';break
        # Exported action summaries are not independent command logs. Unknown
        # actors are conservatively treated as possibly involving either seat.
        actions=step.get('humanActions',[])
        prep=[a.get('kind') for a in actions if a.get('kind')!='destiny' and a.get('actorUid') in ids+[None]]
        if j>n-1 and prep:
            stop='intervening_preparation_action';break
        players=[state.get('players',{}).get(u,{}) for u in ids]
        current=[_stats(p) for p in players];balances=[p.get('life') for p in players]
        if any(v is None for v in current) or any(type(v)is not int for v in balances):stop='missing_public_balance_or_counter';break
        if any(s not in (initial,final) for s,initial,final in zip(current,stats,expected)):
            stop='counter_transition_not_one_recorded_game';break
        round_value=state.get('round')
        if type(round_value)is not int or round_value not in (battle['round'],battle['round']+1):stop='round_boundary_unresolved';break
        private_fields.update(step.get('patch',{}).get('privatePlayer',{}))
        life_written=[i for i,u in enumerate(ids) if 'life' in step.get('patch',{}).get('players',{}).get(u,{})]
        counter_written=[i for i,u in enumerate(ids) if {'wins','losses'}&set(step.get('patch',{}).get('players',{}).get(u,{}))]
        if life_written or counter_written or j==n-1:
            events.append({'step':j+1,'round':round_value,'life':balances,'counters':current,
                'life_written_seats':life_written,'counter_written_seats':counter_written,
                'action_kinds':[a.get('kind') for a in actions]})
        for seat in [0,1]:
            if endpoints[seat] is None and current[seat]==expected[seat]:
                endpoints[seat]={'step':j+1,'round':round_value,'life':balances[seat],'counters':current[seat],
                    'net_change':balances[seat]-life[seat]}
        if all(endpoints):stop='first_counter_updates_observed';break
    return {'case_id':row['id'],'source_sha256':src['raw_sha256'],'battle_step':n,'battle_round':battle['round'],
        'before_life':life,'before_counters':stats,'expected_counters':expected,'immediate_recorded_delta':[pair[u]['lifeDelta'] for u in ids],
        'resolved':all(endpoints),'stop_reason':stop,'endpoints':endpoints,
        'observed_window_net_change':[e['net_change'] if e else None for e in endpoints],
        'source_events':events,'private_patch_field_names_in_window':sorted(private_fields),
        'automatic_new_round_rewards_excluded':False,'pure_combat_end_balance_certified':False,
        'endpoint_selection_uses_simulation':False,'comparison_only':True,'training_label_allowed':False}
