"""Bound original-record random card parameters; no new policy observation."""
from copy import deepcopy
import hashlib,json
from pathlib import Path
from . import full_battle_v86 as previous
from .full_battle_v45 import digest_json,snapshot_binding
from .combat_compiler_view_v81 import isolated_compiler
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-debuff-parameters-v87r2.json'
PROOF_SHA='3fac79e345a9d8928ba45e283849f34b6071b8df2e4cfe26af37cddae69862a3'
BRIDGE=ROOT/'tools/full_battle_bridge_v87r2.mjs'
UnresolvedBattle=previous.UnresolvedBattle
catalogue=previous.catalogue
derive_start_initiative=previous.derive_start_initiative

def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('debuff_parameters_v87r2:evidence_changed')
    facts=json.loads(raw)
    for p,h in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('debuff_parameters_v87r2:source_changed:'+p)
    return facts

def compile_start(row,**kwargs):
    facts=extension_contract();expected=facts['admitted_records'].get(row.get('id'))
    if expected is None:return previous.compile_start(row,**kwargs)
    ctx=kwargs.get('combat_context');binding=expected['binding']
    if not isinstance(ctx,dict) or snapshot_binding(row,ctx)!=binding['snapshot_sha256']:
        raise UnresolvedBattle('debuff_parameters_v87r2:original_snapshot_mismatch')
    params=ctx.get('battle_params')
    if not isinstance(params,list) or not params or any(type(x) is not int for x in params) or digest_json(params)!=binding['stream_sha256']:
        raise UnresolvedBattle('debuff_parameters_v87r2:recorded_stream_mismatch')
    evidence=row.get('battle_params_evidence',{})
    if evidence.get('entries')!=len(params) or evidence.get('sha256')!=binding['stream_sha256']:
        raise UnresolvedBattle('debuff_parameters_v87r2:source_parameter_mismatch')
    result=previous.compile_start(row,**kwargs);battle=result['battle']
    if any(k in battle for k in ('typed_parameters','falling_paper','cloud_sword_parameters','card_parameters')):
        raise UnresolvedBattle('debuff_parameters_v87r2:mixed_parameter_handlers')
    if digest_json(battle)!=expected['compiled_battle_sha256']:
        raise UnresolvedBattle('debuff_parameters_v87r2:unaudited_compiled_start')
    battle['debuff_parameters']={'stream':list(params),'battle_sha256':digest_json(battle),'record_binding':deepcopy(binding)}
    result['debuff_parameter_context_v87r2']={'evidence_sha256':PROOF_SHA,'record_conditioned':True,
        'snapshot_sha256':binding['snapshot_sha256'],'first_player':binding['first_player'],
        'full_parameter_stream_sha256':binding['stream_sha256'],'policy_observation_allowed':False,
        'counterfactual_reuse_allowed':False,'training_label_allowed':False}
    return result

def simulate_batch(battles,*,timeout=90):
    extension_contract();previous.extension_contract()
    # The prior bridge-specific wrappers are immutable; use their frozen core.
    previous.previous.extension_contract()
    for m in [previous.previous.previous,previous.previous.previous.previous,previous.previous.previous.previous.previous,previous.previous.previous.previous.previous.previous]:m.extension_contract()
    result=isolated_compiler(previous.previous.core,runtime_bridge=BRIDGE).simulate_batch(battles,timeout=timeout)
    result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v87r2',
        'debuff_parameters_evidence_sha256':PROOF_SHA,'training_label_allowed':False}
    return result
