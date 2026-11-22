"""7062 preparation ownership preserved; no pool/action receipt is inferred.

The diagnostic accepts an already recorded opening, never replays this active
preparation action, and never allows continuation into a counterfactual round.
"""
from copy import deepcopy
from pathlib import Path
import hashlib,json
from . import full_battle_v127 as previous
from . import full_battle_v80 as core
from .combat_compiler_view_v81 import isolated_compiler,compiler_modules
from .full_battle_v45 import digest_json,snapshot_binding

ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-sever-mortal-phase-v128.json'
PROOF_SHA='fee50b3dc4473b727c0f9e762e3da7cdef4d8be28fad0c742035e856c1be542b'
BRIDGE=ROOT/'tools/full_battle_bridge_v128.mjs'
PREPARATION_IDS=frozenset({7062})
UnresolvedBattle=previous.UnresolvedBattle
catalogue=previous.catalogue
derive_start_initiative=previous.derive_start_initiative

def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:
        raise UnresolvedBattle('phase_v128:evidence_changed')
    facts=json.loads(raw)
    for name,h in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h:
            raise UnresolvedBattle('phase_v128:source_changed:'+name)
    return facts

def owned_ids(row):
    found=[]
    for player in row['players']:
        owned=player['candidate_start'].get('xian_mo_strategies')
        if not isinstance(owned,list) or any(type(x)is not int for x in owned):
            raise UnresolvedBattle('phase_v128:explicit_season_ownership_required')
        found.append(sorted(set(owned)&PREPARATION_IDS))
    return found

def compile_owned_start(row,ids,facts,**kwargs):
    tables=kwargs.get('tables')
    tables=catalogue() if tables is None else tables
    season=deepcopy(tables[3])
    for strategy in set(x for values in ids for x in values):
        if season.get(strategy)!=facts['strategy_configs'][str(strategy)]:
            raise UnresolvedBattle('phase_v128:configuration_changed:'+str(strategy))
        season[strategy]['isBattleEffect']=False
    result=previous.compile_start(row,**{**kwargs,'tables':(*tables[:3],season)})
    for seat,player in enumerate(row['players']):
        if result['effect_players'][seat]['season_choices']!=player['candidate_start']['xian_mo_strategies']:
            raise UnresolvedBattle('phase_v128:ownership_not_preserved')
    result['preparation_scope_v128']={
        'strategy_ids_by_player':ids,'source_kind':'fixed_client_readers_and_localized_preparation_phase',
        'ownership_preserved':True,'active_use_replayed':False,
        'active_use_receipt_inferred':False,'remaining_uses_inferred':False,
        'exchange_or_pool_mutated':False,'pending_legal_preparation_transition':True,
        'authoritative_resources_mutated':False,'match_continuation_allowed':False,
        'training_label_allowed':False,
    }
    return result

def compile_start(row,**kwargs):
    facts=extension_contract();ids=owned_ids(row)
    if not any(ids):return previous.compile_start(row,**kwargs)
    result=compile_owned_start(row,ids,facts,**kwargs)
    result['preparation_scope_v128']['evidence_sha256']=PROOF_SHA
    expected=facts['random_bindings'].get(row['id'])
    if expected is not None:
        ctx=kwargs.get('combat_context');binding=expected['binding']
        if snapshot_binding(row,ctx)!=binding['snapshot_sha256']:
            raise UnresolvedBattle('phase_v128:original_snapshot_mismatch')
        stream=ctx.get('battle_params');evidence=row.get('battle_params_evidence',{})
        if (not isinstance(stream,list) or any(type(x)is not int for x in stream)
                or digest_json(stream)!=binding['stream_sha256']
                or evidence.get('entries')!=len(stream) or evidence.get('sha256')!=binding['stream_sha256']):
            raise UnresolvedBattle('phase_v128:original_stream_required')
        battle=result['battle']
        if (digest_json(battle)!=expected['compiled_battle_sha256']
                or battle['first_player']!=binding['first_player']
                or any('parameter' in k or k=='falling_paper' for k in battle)):
            raise UnresolvedBattle('phase_v128:original_compiled_start_required')
        battle['replay_parameters']={'stream':list(stream),'battle_sha256':digest_json(battle),'record_binding':deepcopy(binding)}
        result['replay_parameter_context_v128']={'evidence_sha256':PROOF_SHA,'record_conditioned':True,
            'policy_observation_allowed':False,'counterfactual_reuse_allowed':False,'training_label_allowed':False}
    return result

def simulate_batch(battles,*,timeout=90):
    extension_contract()
    for module in compiler_modules(previous).values():
        contract=vars(module).get('extension_contract')
        if contract is not None:contract()
    result=isolated_compiler(core,runtime_bridge=BRIDGE).simulate_batch(battles,timeout=timeout)
    result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v128',
        'preparation_admission_evidence_sha256':PROOF_SHA,'training_label_allowed':False}
    return result
