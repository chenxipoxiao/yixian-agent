"""Current clear-heart card and explicit starting swordsmith counter."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from . import full_battle_v8 as v8
from .simulator import engine_contract, SimulatorError

ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-clear-heart-v9.json'
PROOF_SHA='f007aeb00b607f349ccd115287399a9e962b78b5d72c55a57243d82d4f779346'
BRIDGE=ROOT/'tools/full_battle_bridge_v9.mjs'
UnresolvedBattle=v8.UnresolvedBattle
derive_start_initiative=v8.derive_start_initiative
EXTRA_FATES={10094:'sword_pattern_carving_chain_attack_stacks',
             30094:'sword_pattern_carving_intense_stacks',30095:'qi_forging_spiritual_power_stacks'}

def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Clear-heart evidence changed')
    facts=json.loads(raw)
    for path,digest in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:raise UnresolvedBattle('Clear-heart source changed:'+path)
    return facts

def catalogue():
    extension_contract();cards,mapping,talents,season=v8.catalogue()
    if 19 in mapping:raise UnresolvedBattle('Clear-heart alias already assigned')
    mapping[19]='611033'
    return cards,mapping,talents,season

def compile_start(row,**kwargs):
    extension_contract();projected=deepcopy(row);metadata=[]
    if len(projected.get('players',[]))!=2:raise UnresolvedBattle('Two start snapshots required')
    for player in projected['players']:
        start=player.get('candidate_start',{});fates=start.get('talents');counters=start.get('talentTempDatas')
        if not isinstance(fates,list) or any(type(f) is not int for f in fates) or len(fates)!=len(set(fates)):
            raise UnresolvedBattle('Unique explicit talent list required')
        if not isinstance(counters,dict):raise UnresolvedBattle('Explicit talent dictionary required')
        entry={'native_fates':{EXTRA_FATES[f]:1 for f in fates if f in EXTRA_FATES}}
        if 92 in fates:
            value=counters.get('92',0)
            if type(value) is not int or not 0<=value<=18:raise UnresolvedBattle('swordsmith_start_counter_outside_reviewed_range')
            entry['swordsmith_start_counter']=value
            entry['counter_key_present']='92' in counters
            counters['92']={'swordsmith_attack_bonus':value}
        start['talents']=[f for f in fates if f not in EXTRA_FATES]
        metadata.append(entry)
    if 'tables' not in kwargs:kwargs['tables']=catalogue()
    result=v8.compile_start(projected,**kwargs)
    for original,raw,effect,entry in zip(row['players'],result['battle']['players'],result['effect_players'],metadata):
        for field,value in entry['native_fates'].items():
            if field in raw:raise UnresolvedBattle('Duplicate native effect:'+field)
            raw[field]=value
        effect['fates']=deepcopy(original['candidate_start']['talents'])
        effect['talent_counters']=deepcopy(original['candidate_start']['talentTempDatas'])
    result['current_clear_heart']={'evidence_sha256':PROOF_SHA,'players':metadata,'training_label_allowed':False}
    return result

def simulate_batch(battles,*,timeout=90):
    extension_contract();v8.extension_contract();v8.v7.extension_contract();v8.v7.v6.extension_contract();v8.v7.v6.v5.extension_contract()
    v8.v7.v6.v5.v4.plant_contract();v8.v7.v6.v5.v4.v3.counter_contract();v8.v7.v6.v5.v4.v3.v2.extension_contract()
    engine=engine_contract()
    if not isinstance(battles,list) or not battles or len(battles)>1000:raise ValueError('Require 1–1000 battles')
    node=shutil.which('node')
    if not node:raise SimulatorError('Node runtime is not on PATH')
    run=subprocess.run([node,'--experimental-default-type=module',str(BRIDGE)],
        input=json.dumps(battles,ensure_ascii=False,allow_nan=False),text=True,encoding='utf-8',cwd=ROOT,capture_output=True,timeout=timeout)
    if run.returncode:raise SimulatorError(run.stderr.strip())
    results=json.loads(run.stdout)
    if len(results)!=len(battles):raise SimulatorError('Batch result count mismatch')
    return {'results':results,'engine':engine,'adapter_contract':{'schema':'complete-single-battle-diagnostic-v9',
        'evidence_sha256':PROOF_SHA,'native_scheduler_reused':True,'old_versions_unchanged':True,
        'full_match_environment':False,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),
        'implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'current_server_verified':False,'training_label_allowed':False}
