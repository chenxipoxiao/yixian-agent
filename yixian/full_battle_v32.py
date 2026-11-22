"""Dream Echo with uniquely determined pre-battle hand targets; v31 retained."""
from copy import deepcopy
import hashlib,json,shutil,subprocess
from pathlib import Path
from . import full_battle_v31 as v31
from .simulator import engine_contract,SimulatorError
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-dream-echo-v32.json'
PROOF_SHA='b8d21d306e7d2f2962d39ebe1fa75d996ddefa7796c1e3063f931db59da16690'
BRIDGE=ROOT/'tools/full_battle_bridge_v32.mjs'
UnresolvedBattle=v31.UnresolvedBattle
derive_start_initiative=v31.derive_start_initiative
def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Echo formation evidence changed')
    facts=json.loads(raw)
    for p,h in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('Echo formation source changed:'+p)
    return facts
def catalogue():
    facts=extension_contract();cards,mapping,talents,season=v31.catalogue()
    for c in facts['cards']:
        if c['raw_id'] in mapping or c['runtime_id'] in mapping.values():raise UnresolvedBattle('Dream Echo alias collision')
        mapping[c['raw_id']]=c['runtime_id']
    return cards,mapping,talents,season

def compile_start(row,**kwargs):
    extension_contract()
    if 'tables' not in kwargs:kwargs['tables']=catalogue()
    result=v31.compile_start(row,**kwargs)
    active=[any(c in (349,10349) for c in p['candidate_start']['board']) for p in row['players']]
    if not any(active):return result
    context=kwargs.get('combat_context');cards,mapping,*_=kwargs['tables']
    if not isinstance(context,dict) or context.get('source_raw_sha256')!=row['source']['raw_sha256']:
        raise UnresolvedBattle('dream_echo_hand_source_required')
    hands=[]
    for index,needed in enumerate(active):
        if not needed:hands.append(None);continue
        p=context['players'][index];data=p.get('dream_echo_hand')
        if not isinstance(data,dict) or data.get('origin')!='publicData.lastRoundData.handCards' or data.get('source_raw_sha256')!=row['source']['raw_sha256'] or data.get('environment_only') is not True:
            raise UnresolvedBattle('dream_echo_hand_required:'+str(index))
        hand=data.get('raw_cards')
        if not isinstance(hand,list) or len(hand)>256 or any(type(c) is not int or c not in cards for c in hand):
            raise UnresolvedBattle('dream_echo_hand_invalid:'+str(index))
        if len(hand)!=p.get('hand_count'):raise UnresolvedBattle('dream_echo_hand_count_mismatch:'+str(index))
        eligible=sorted({c for c in hand if cards[c]['cardType'] in (1,3)})
        if len(eligible)>1:raise UnresolvedBattle('dream_echo_multiple_targets:'+str(eligible))
        if eligible and eligible[0] not in mapping:raise UnresolvedBattle('dream_echo_unmapped_target:'+str(eligible[0]))
        hands.append(list(hand))
    result['battle']['dream_echo']={'hands':hands}
    result['dream_echo_context']={'evidence_sha256':PROOF_SHA,'origin':'publicData.lastRoundData.handCards',
        'selection':'unique_eligible_raw_card_or_explicit_empty','recorded_parameters_as_input':False,
        'policy_observation':False,'training_label_allowed':False}
    return result


def simulate_batch(battles,*,timeout=90):
    extension_contract();v31.extension_contract()
    v30=v31.v30
    v30.extension_contract()
    v29=v30.v29
    v29.extension_contract()
    v28=v29.v28
    v28.extension_contract()
    v27=v28.v27
    v26=v27.v26
    v27.extension_contract()
    # Check the existing complete chain without executing an old bridge.
    v26.extension_contract();v26.v25.extension_contract();v26.v24.extension_contract()
    v26.v23.extension_contract();v26.v22.extension_contract();v26.v17.extension_contract()
    module=v26.v17.v16
    for attr in ['v15','v14','v13','v12','v11','v10','v9','v8','v7','v6','v5']:
        module.extension_contract();module=getattr(module,attr)
    module.extension_contract();module.v4.plant_contract();module.v4.v3.counter_contract();module.v4.v3.v2.extension_contract()
    if not isinstance(battles,list) or not 1<=len(battles)<=1000:raise ValueError('Require1–1000 battles')
    node=shutil.which('node')
    if not node:raise SimulatorError('Node runtime is not on PATH')
    run=subprocess.run([node,'--experimental-default-type=module',str(BRIDGE)],
        input=json.dumps(battles,ensure_ascii=False,allow_nan=False),text=True,encoding='utf8',
        cwd=ROOT,capture_output=True,timeout=timeout)
    if run.returncode:raise SimulatorError(run.stderr.strip())
    results=json.loads(run.stdout)
    if len(results)!=len(battles):raise SimulatorError('Batch result count mismatch')
    return {'results':results,'engine':engine_contract(),'adapter_contract':{'schema':'complete-single-battle-diagnostic-v32',
        'evidence_sha256':PROOF_SHA,'native_scheduler_reused':True,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),'current_server_verified':False,'training_label_allowed':False}
