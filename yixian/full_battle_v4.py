"""Optional current-client plant startup projection for complete diagnostics.

Keep base HP untouched: the native per-player opening handler applies the
effects with ordinary healing/damage hooks. Acquisition and cross-round plant
growth are not replayed. Frozen v1/v2/v3 entry points remain unchanged.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from . import full_battle_v3 as v3
from .simulator import engine_contract, SimulatorError

ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/permanent-plants-v4.json'
PROOF_SHA='53e74db7efaa577b73ed0fa5606ed34d0ed481135f45b393500ffaaadadd5c56'
BRIDGE=ROOT/'tools/full_battle_bridge_v4.mjs'
UnresolvedBattle=v3.UnresolvedBattle
catalogue=v3.catalogue
derive_start_initiative=v3.derive_start_initiative


def plant_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:
        raise UnresolvedBattle('Permanent plant evidence changed')
    proof=json.loads(raw)
    native=ROOT/'external/yisim/gamestate_full.js'
    if hashlib.sha256(native.read_bytes()).hexdigest()!=proof['native_engine_sha256']:
        raise UnresolvedBattle('Permanent plant native engine changed')
    return proof


def compile_start(row,**kwargs):
    proof=plant_contract();projected=deepcopy(row);retained=[]
    if not isinstance(projected.get('players'),list) or len(projected['players'])!=2:
        raise UnresolvedBattle('Two start snapshots required')
    for index,player in enumerate(projected['players']):
        permanent=player.get('candidate_start',{}).get('permanentBuffTempDatas')
        if not isinstance(permanent,dict):raise UnresolvedBattle('Explicit permanent dictionary required')
        effects={}
        for key,rule in proof['mapping'].items():
            if key not in permanent:continue
            value=permanent[key]
            if type(value) is not int or not 1<=value<=1_000_000:
                raise UnresolvedBattle('plant_value_pending:'+key+':requires explicit positive bounded integer')
            effects[key]={'value':value,'field':rule['field']}
            del permanent[key]
        retained.append({'snapshot_slot':('p1','p2')[index],'effects':effects})
    # All unreviewed keys and version/context checks remain enforced by v3.
    result=v3.compile_start(projected,**kwargs)
    for raw,metadata in zip(result['battle']['players'],retained):
        for key,effect in metadata['effects'].items():
            if effect['field'] in raw:raise UnresolvedBattle('Plant startup would be applied twice:'+key)
            raw[effect['field']]=effect['value']
    result['permanent_plant_startup']={'players':retained,'evidence_sha256':PROOF_SHA,
        'execution':'native do_plant_start_permanent_buffs after fates and before card openings',
        'initial_hp_not_adjusted':True,'original_input_mutated':False,
        'persistent_acquisition_or_growth_implemented':False,'training_label_allowed':False}
    return result


def simulate_batch(battles,*,timeout=90):
    plant_contract();v3.counter_contract();v3.v2.extension_contract()
    engine=engine_contract()
    if not isinstance(battles,list) or not battles or len(battles)>1000:
        raise ValueError('Require 1–1000 battles')
    node=shutil.which('node')
    if not node:raise SimulatorError('Node runtime is not on PATH')
    run=subprocess.run([node,'--experimental-default-type=module',str(BRIDGE)],
        input=json.dumps(battles,ensure_ascii=False,allow_nan=False),text=True,encoding='utf-8',
        cwd=ROOT,capture_output=True,timeout=timeout)
    if run.returncode:raise SimulatorError(run.stderr.strip())
    results=json.loads(run.stdout)
    if len(results)!=len(battles):raise SimulatorError('Batch result count mismatch')
    return {'results':results,'engine':engine,
        'adapter_contract':{'schema':'complete-single-battle-diagnostic-v4',
            'plant_evidence_sha256':PROOF_SHA,'counter_evidence_sha256':v3.PROOF_SHA,
            'positive_plants_only':True,'opening_terminal_supported':False,
            'initial_hp_not_adjusted':True,'persistent_acquisition_or_growth_implemented':False,
            'full_match_environment':False,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),
        'implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'current_server_verified':False,'training_label_allowed':False}
