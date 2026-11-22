"""Reviewed current start-state projections over the frozen complete v6 engine."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from . import full_battle_v6 as v6
from .simulator import engine_contract, SimulatorError

ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-start-states-v7.json'
PROOF_SHA='bdc8242efd356f18b419a6f829a61489bfe64570bddc8ef012e1bb3617bf6947'
BRIDGE=ROOT/'tools/full_battle_bridge_v7.mjs'
UnresolvedBattle=v6.UnresolvedBattle
catalogue=v6.catalogue
derive_start_initiative=v6.derive_start_initiative

def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Current state evidence changed')
    facts=json.loads(raw)
    for path,digest in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:raise UnresolvedBattle('Current state source changed:'+path)
    return facts

def compile_start(row,**kwargs):
    facts=extension_contract();projected=deepcopy(row);metadata=[]
    if len(projected.get('players',[]))!=2:raise UnresolvedBattle('Two start snapshots required')
    for player in projected['players']:
        start=player.get('candidate_start',{});permanent=start.get('permanentBuffTempDatas')
        if not isinstance(permanent,dict):raise UnresolvedBattle('Explicit permanent dictionary required')
        entry={'plant_startup':{},'preparation_counters':{},'fates_already_in_start_snapshot':[],'native_fates':{}}
        for key,field in facts['permanent_startup'].items():
            if key not in permanent:continue
            value=permanent.pop(key)
            if type(value) is not int or not 1<=value<=1_000_000:raise UnresolvedBattle('positive_plant_value_required:'+key)
            entry['plant_startup'][field]=value
        for key in facts['preparation_only_permanent']:
            if key not in permanent:continue
            value=permanent.pop(key)
            if type(value) is not int or not 0<=value<=1_000_000:raise UnresolvedBattle('nonnegative_preparation_counter_required:'+key)
            entry['preparation_counters'][key]=value
        fate_ids=start.get('talents')
        if not isinstance(fate_ids,list) or any(type(x) is not int for x in fate_ids) or len(set(fate_ids))!=len(fate_ids):
            raise UnresolvedBattle('Unique explicit talent list required')
        retained=[]
        for fate in fate_ids:
            if str(fate) in facts['preparation_or_speed_fates']:
                entry['fates_already_in_start_snapshot'].append(fate)
            elif fate==267:entry['native_fates']['wind_spirit_forging_stacks']=1
            else:retained.append(fate)
        # The current client reads the public innate talent, not a guessed raw counter.
        if 110 in fate_ids:
            elements=[element for raw,element in facts['innate_marks'].items() if int(raw) in fate_ids]
            if len(elements)!=1:raise UnresolvedBattle('innate_mark_requires_one_explicit_innate_talent')
            counters=start.get('talentTempDatas')
            if not isinstance(counters,dict):raise UnresolvedBattle('Explicit talent dictionary required')
            if '110' in counters:raise UnresolvedBattle('unexpected_innate_counter_context')
            counters['110']={'innate_element':elements[0]}
            entry['innate_element_from_start_talent']=elements[0]
        start['talents']=retained;metadata.append(entry)
    result=v6.compile_start(projected,**kwargs)
    for original,raw,effect,entry in zip(row['players'],result['battle']['players'],result['effect_players'],metadata):
        for field,value in {**entry['plant_startup'],**entry['native_fates']}.items():
            if field in raw:raise UnresolvedBattle('Duplicate native effect:'+field)
            raw[field]=value
        effect['fates']=deepcopy(original['candidate_start']['talents'])
        effect['talent_counters']=deepcopy(original['candidate_start']['talentTempDatas'])
    result['current_start_projection']={'evidence_sha256':PROOF_SHA,'players':metadata,
        'acquisition_rewards_reapplied':False,'cross_round_updates_implemented':False,'training_label_allowed':False}
    return result

def simulate_batch(battles,*,timeout=90):
    extension_contract();v6.extension_contract();v6.v5.extension_contract()
    v6.v5.v4.plant_contract();v6.v5.v4.v3.counter_contract();v6.v5.v4.v3.v2.extension_contract()
    engine=engine_contract()
    if not isinstance(battles,list) or not battles or len(battles)>1000:raise ValueError('Require 1–1000 battles')
    node=shutil.which('node')
    if not node:raise SimulatorError('Node runtime is not on PATH')
    run=subprocess.run([node,'--experimental-default-type=module',str(BRIDGE)],
        input=json.dumps(battles,ensure_ascii=False,allow_nan=False),text=True,encoding='utf-8',cwd=ROOT,capture_output=True,timeout=timeout)
    if run.returncode:raise SimulatorError(run.stderr.strip())
    results=json.loads(run.stdout)
    if len(results)!=len(battles):raise SimulatorError('Batch result count mismatch')
    return {'results':results,'engine':engine,'adapter_contract':{'schema':'complete-single-battle-diagnostic-v7',
        'evidence_sha256':PROOF_SHA,'native_scheduler_reused':True,'old_versions_unchanged':True,
        'full_match_environment':False,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),
        'implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'current_server_verified':False,'training_label_allowed':False}
