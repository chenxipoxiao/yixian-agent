"""Separate two postbattle rewards from single-battle admission.

Keep ownership and the original physical state. Rewards are pending, never
granted by the diagnostic; the caller cannot continue a match from this result.
The frozen v125 compiler and runtime remain available without mutation.
"""
from copy import deepcopy
from pathlib import Path
import hashlib,json
from . import full_battle_v125r3 as previous
from . import full_battle_v80 as core
from .combat_compiler_view_v81 import isolated_compiler,compiler_modules
from .full_battle_v45 import digest_json,snapshot_binding

ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-postbattle-admission-v126.json'
PROOF_SHA='962aa6b36c64e71ca9b2dd483b25b22e9bc5580e5455516c88ee78daaa8d661b'
BRIDGE=ROOT/'tools/full_battle_bridge_v126.mjs'
POSTBATTLE_IDS=frozenset({7011,7038})
UnresolvedBattle=previous.UnresolvedBattle
catalogue=previous.catalogue
derive_start_initiative=previous.derive_start_initiative

def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:
        raise UnresolvedBattle('postbattle_v126:evidence_changed')
    facts=json.loads(raw)
    for name,h in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h:
            raise UnresolvedBattle('postbattle_v126:source_changed:'+name)
    return facts

def owned_ids(row):
    found=[]
    for player in row['players']:
        owned=player['candidate_start'].get('xian_mo_strategies')
        if not isinstance(owned,list) or any(type(x)is not int for x in owned):
            raise UnresolvedBattle('postbattle_v126:explicit_season_ownership_required')
        found.append(sorted(set(owned)&POSTBATTLE_IDS))
    return found

def compile_owned_start(row,ids,facts,**kwargs):
    # Metadata is projected only in this call's private table. Every ID remains
    # in the original snapshot, generic ownership queries, and settlement data.
    tables=kwargs.get('tables')
    tables=catalogue() if tables is None else tables
    season=deepcopy(tables[3])
    for strategy in set(x for values in ids for x in values):
        if season.get(strategy)!=facts['strategy_configs'][str(strategy)]:
            raise UnresolvedBattle('postbattle_v126:configuration_changed:'+str(strategy))
        season[strategy]['isBattleEffect']=False
    result=previous.compile_start(row,**{**kwargs,'tables':(*tables[:3],season)})
    for seat,player in enumerate(row['players']):
        if result['effect_players'][seat]['season_choices']!=player['candidate_start']['xian_mo_strategies']:
            raise UnresolvedBattle('postbattle_v126:ownership_not_preserved')
    result['postbattle_scope_v126']={
        'strategy_ids_by_player':ids,'source_kind':'fixed_client_readers_and_localized_reward_phase',
        'ownership_preserved':True,'preparation_rewards_replayed':False,
        'pending_reward_evaluation':True,'reward_trigger_or_amount_inferred':False,
        'authoritative_resources_mutated':False,'match_continuation_allowed':False,
        'training_label_allowed':False,
    }
    return result

def compile_start(row,**kwargs):
    facts=extension_contract();ids=owned_ids(row)
    if not any(ids):return previous.compile_start(row,**kwargs)
    result=compile_owned_start(row,ids,facts,**kwargs)
    result['postbattle_scope_v126']['evidence_sha256']=PROOF_SHA
    expected=facts['random_bindings'].get(row['id'])
    if expected is not None:
        ctx=kwargs.get('combat_context');binding=expected['binding']
        if snapshot_binding(row,ctx)!=binding['snapshot_sha256']:
            raise UnresolvedBattle('postbattle_v126:original_snapshot_mismatch')
        stream=ctx.get('battle_params');evidence=row.get('battle_params_evidence',{})
        if (not isinstance(stream,list) or any(type(x)is not int for x in stream)
                or digest_json(stream)!=binding['stream_sha256']
                or evidence.get('entries')!=len(stream) or evidence.get('sha256')!=binding['stream_sha256']):
            raise UnresolvedBattle('postbattle_v126:original_stream_required')
        battle=result['battle']
        if (digest_json(battle)!=expected['compiled_battle_sha256']
                or battle['first_player']!=binding['first_player']
                or any('parameter' in k or k=='falling_paper' for k in battle)):
            raise UnresolvedBattle('postbattle_v126:original_compiled_start_required')
        battle['replay_parameters']={'stream':list(stream),'battle_sha256':digest_json(battle),'record_binding':deepcopy(binding)}
        result['replay_parameter_context_v126']={'evidence_sha256':PROOF_SHA,'record_conditioned':True,
            'policy_observation_allowed':False,'counterfactual_reuse_allowed':False,'training_label_allowed':False}
    return result

def simulate_batch(battles,*,timeout=90):
    extension_contract()
    for module in compiler_modules(previous).values():
        contract=vars(module).get('extension_contract')
        if contract is not None:contract()
    result=isolated_compiler(core,runtime_bridge=BRIDGE).simulate_batch(battles,timeout=timeout)
    result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v126',
        'postbattle_admission_evidence_sha256':PROOF_SHA,'training_label_allowed':False}
    return result
