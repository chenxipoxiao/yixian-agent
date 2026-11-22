"""Bound original-record random card parameters; no new policy observation."""
from copy import deepcopy
import hashlib,json
from pathlib import Path
from . import full_battle_v88r2 as previous
from .full_battle_v45 import digest_json,snapshot_binding
from .combat_compiler_view_v81 import isolated_compiler
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-nested-card-parameters-v89.json'
PROOF_SHA='c0353b02499bd3b9d98f9436f98e36f20cfc72a69fcc681f8e9779a298bfbab8'
BRIDGE=ROOT/'tools/full_battle_bridge_v89.mjs'
UnresolvedBattle=previous.UnresolvedBattle
catalogue=previous.catalogue
derive_start_initiative=previous.derive_start_initiative

def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('nested_card_parameters_v89:evidence_changed')
    facts=json.loads(raw)
    for p,h in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('nested_card_parameters_v89:source_changed:'+p)
    return facts

def compile_start(row,**kwargs):
    facts=extension_contract();expected=facts['admitted_records'].get(row.get('id'))
    if expected is None:return previous.compile_start(row,**kwargs)
    ctx=kwargs.get('combat_context');binding=expected['binding']
    if not isinstance(ctx,dict) or snapshot_binding(row,ctx)!=binding['snapshot_sha256']:
        raise UnresolvedBattle('nested_card_parameters_v89:original_snapshot_mismatch')
    params=ctx.get('battle_params')
    if not isinstance(params,list) or not params or any(type(x) is not int for x in params) or digest_json(params)!=binding['stream_sha256']:
        raise UnresolvedBattle('nested_card_parameters_v89:recorded_stream_mismatch')
    evidence=row.get('battle_params_evidence',{})
    if evidence.get('entries')!=len(params) or evidence.get('sha256')!=binding['stream_sha256']:
        raise UnresolvedBattle('nested_card_parameters_v89:source_parameter_mismatch')
    result=previous.compile_start(row,**kwargs);battle=result['battle']
    if any(k in battle for k in ('typed_parameters','falling_paper','cloud_sword_parameters','card_parameters','debuff_parameters','probability_parameters')):
        raise UnresolvedBattle('nested_card_parameters_v89:mixed_parameter_handlers')
    if digest_json(battle)!=expected['compiled_battle_sha256']:
        raise UnresolvedBattle('nested_card_parameters_v89:unaudited_compiled_start')
    battle['nested_card_parameters']={'stream':list(params),'battle_sha256':digest_json(battle),'record_binding':deepcopy(binding)}
    result['nested_card_parameter_context_v89']={'evidence_sha256':PROOF_SHA,'record_conditioned':True,
        'snapshot_sha256':binding['snapshot_sha256'],'first_player':binding['first_player'],
        'full_parameter_stream_sha256':binding['stream_sha256'],'policy_observation_allowed':False,
        'counterfactual_reuse_allowed':False,'training_label_allowed':False}
    return result

def simulate_batch(battles,*,timeout=90):
    extension_contract();previous.extension_contract()
    ancestor=previous.previous
    ancestor.extension_contract();ancestor.previous.extension_contract()
    for m in [ancestor.previous.previous,ancestor.previous.previous.previous.previous.previous.previous,ancestor.previous.previous.previous,ancestor.previous.previous.previous.previous,ancestor.previous.previous.previous.previous.previous]:m.extension_contract()
    result=isolated_compiler(ancestor.previous.previous.core,runtime_bridge=BRIDGE).simulate_batch(battles,timeout=timeout)
    result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v89',
        'nested_card_parameters_evidence_sha256':PROOF_SHA,'training_label_allowed':False}
    return result
