"""Explicit learned-card/vase state and reviewed fate initialization, v13."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from . import full_battle_v12 as v12
from .simulator import engine_contract, SimulatorError

ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-fate-context-v13.json'
PROOF_SHA='eb6a32aa0cc666df3e9b18497a78969748a0bd2ca54a4257abe05ff8637b139b'
BRIDGE=ROOT/'tools/full_battle_bridge_v13.mjs'
UnresolvedBattle=v12.UnresolvedBattle
catalogue=v12.catalogue
derive_start_initiative=v12.derive_start_initiative


def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Fate context evidence changed')
    facts=json.loads(raw)
    for path,digest in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:
            raise UnresolvedBattle('Fate context source changed:'+path)
    return facts


def _params(context,kind,key):
    extension=context.get('start_extensions')
    if not isinstance(extension,dict) or extension.get('origin')!='publicData.lastRoundData':
        raise UnresolvedBattle('Explicit start talent metadata required:'+key)
    values=extension.get(kind)
    if not isinstance(values,dict):raise UnresolvedBattle('Explicit start talent dictionary required:'+key)
    if key not in values:return [] # Client GetLingWuCards/ContainsKey branch, known absent.
    obj=values[key]
    params=obj.get('commonParams') if isinstance(obj,dict) else None
    if not isinstance(params,list) or len(params)>64 or any(type(v) is not int or v<0 for v in params):
        raise UnresolvedBattle('Explicit numeric commonParams required:'+key)
    return params


def compile_start(row,**kwargs):
    facts=extension_contract();tables=kwargs.get('tables') or catalogue()
    cards,mapping,_,_=tables;kwargs['tables']=tables
    projected=deepcopy(row);metadata=[]
    context=kwargs['combat_context']
    if len(projected.get('players',[]))!=2 or len(context.get('players',[]))!=2:
        raise UnresolvedBattle('Two start players required')
    for p,ctx in zip(projected['players'],context['players']):
        s=p['candidate_start'];fates=s.get('talents');extra={};prepared={}
        if not isinstance(fates,list) or any(type(v) is not int for v in fates) or len(set(fates))!=len(fates):
            raise UnresolvedBattle('Unique explicit talents required')
        permanent=s.get('permanentBuffTempDatas')
        if not isinstance(permanent,dict):raise UnresolvedBattle('Explicit permanent dictionary required')
        for key in facts['noncombat_permanent_counters']:
            if key in permanent:
                val=permanent.pop(key)
                if type(val) is not int or not 0<=val<=1_000_000:
                    raise UnresolvedBattle('Invalid preparation counter:'+key)
                prepared[key]=val
        if 52 in fates and len(s['board'])==8:
            extra['heptastar_soulstat_stacks']=1
        if 10127 in fates:
            # Native p3 adds one per unit; current fixed config grants two.
            extra['p3_mutual_growth_stacks']=2
        if 192 in fates:
            learned=_params(ctx,'talentDatas','189')
            if any(v not in mapping or v not in cards or v==0 for v in learned):
                raise UnresolvedBattle('Unmapped learned card context')
            extra['chengyuns_fusion_style_stacks']=1
            extra['swordplay_talent_cards']=sorted({mapping[v][:-1] for v in learned})
        if 199 in fates:
            stored=_params(ctx,'privateTalentDatas','199')
            if len(stored) not in (0,3):raise UnresolvedBattle('Explicit three vase slots required')
            if any(v not in mapping or v not in cards for v in stored):
                raise UnresolvedBattle('Unmapped vase card context')
            extra['five_elements_pure_vase_stacks']=1
            extra['five_elements_pure_vase_cards']=[mapping[v] if v else None for v in stored]
        s['talents']=[v for v in fates if v not in facts['handled_fates']]
        metadata.append({'native_fields':extra,'noncombat_permanent_counters':prepared})
    result=v12.compile_start(projected,**kwargs)
    for src,raw,effect,meta in zip(row['players'],result['battle']['players'],result['effect_players'],metadata):
        for field,value in meta['native_fields'].items():
            if field in raw:raise UnresolvedBattle('Duplicate native effect:'+field)
            raw[field]=value
        effect['fates']=deepcopy(src['candidate_start']['talents'])
    result['current_fate_context']={'evidence_sha256':PROOF_SHA,'players':metadata,
        'acquisition_rewards_reapplied':False,'training_label_allowed':False}
    return result


def simulate_batch(battles,*,timeout=90):
    extension_contract();v12.extension_contract()
    # Validate every frozen ancestor; no prior simulation is run here.
    module=v12.v11
    for attr in ['v10','v9','v8','v7','v6','v5']:
        module.extension_contract();module=getattr(module,attr)
    module.extension_contract();module.v4.plant_contract();module.v4.v3.counter_contract();module.v4.v3.v2.extension_contract()
    if not isinstance(battles,list) or not 1<=len(battles)<=1000:raise ValueError('Require 1–1000 battles')
    node=shutil.which('node')
    if not node:raise SimulatorError('Node runtime is not on PATH')
    run=subprocess.run([node,'--experimental-default-type=module',str(BRIDGE)],
        input=json.dumps(battles,ensure_ascii=False,allow_nan=False),text=True,encoding='utf-8',cwd=ROOT,capture_output=True,timeout=timeout)
    if run.returncode:raise SimulatorError(run.stderr.strip())
    results=json.loads(run.stdout)
    if len(results)!=len(battles):raise SimulatorError('Batch result count mismatch')
    return {'results':results,'engine':engine_contract(),'adapter_contract':{'schema':'complete-single-battle-diagnostic-v13',
        'evidence_sha256':PROOF_SHA,'native_scheduler_reused':True,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),
        'current_server_verified':False,'training_label_allowed':False}
