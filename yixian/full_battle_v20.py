"""Explicit preparation-slot engravings over the frozen v17 battle compiler."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from . import full_battle_v17 as v17
from .simulator import engine_contract, SimulatorError

ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-engraving-effects-v20.json'
PROOF_SHA='fd5446a34e7d0c93c030d6e32a30efc2b065ea58061a8b6b617d4acd6d713edf'
BRIDGE=ROOT/'tools/full_battle_bridge_v20.mjs'
SUPPORTED={13001,13004,13006,13008,13009,13013,13016,13019}
ORIGIN='privateData.xianMoData.tempDatas:preparation_grid_selection'
UnresolvedBattle=v17.UnresolvedBattle
catalogue=v17.catalogue
derive_start_initiative=v17.derive_start_initiative


def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Engraving evidence changed')
    facts=json.loads(raw)
    for p,h in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('Engraving source changed:'+p)
    return facts


def compile_start(row,**kwargs):
    extension_contract();projected=deepcopy(row);entries=[]
    context=kwargs.get('combat_context')
    for index,p in enumerate(projected['players']):
        start=p['candidate_start'];choices=start.get('xian_mo_strategies')
        if not isinstance(choices,list) or any(type(v) is not int for v in choices):
            raise UnresolvedBattle('Explicit xian_mo_strategies array required')
        owned=sorted(SUPPORTED.intersection(choices));values=[]
        if owned:
            if len(choices)!=len(set(choices)):raise UnresolvedBattle('Duplicate season choices')
            if (not isinstance(context,dict) or context.get('source_raw_sha256')!=row['source']['raw_sha256']
                    or not isinstance(context.get('players'),list) or len(context['players'])!=2):
                raise UnresolvedBattle('Explicit engraving source context required')
            data=context['players'][index].get('season_engraving_input')
            if not isinstance(data,dict) or data.get('origin')!=ORIGIN:
                raise UnresolvedBattle('engraving_preparation_slot_missing:'+str(owned))
            slots=data.get('slots');selected=data.get('selected_strategy_ids')
            if not isinstance(slots,dict) or selected!=owned:
                raise UnresolvedBattle('engraving_preparation_ownership_mismatch:'+str(owned))
            for identifier in owned:
                slot=slots.get(str(identifier))
                # Client default zero is not evidence of an omitted replay field.
                if type(slot) is not int or not 0<=slot<8:
                    raise UnresolvedBattle('engraving_preparation_slot_missing:'+str(identifier))
                values.append({'strategy_id':identifier,'slot':slot})
            start['xian_mo_strategies']=[v for v in choices if v not in SUPPORTED]
        entries.append(values)
    result=v17.compile_start(projected,**kwargs)
    if any(entries):
        result['battle']['season_engraving']={'players':entries}
        for source,effect in zip(row['players'],result['effect_players']):
            effect['season_choices']=deepcopy(source['candidate_start']['xian_mo_strategies'])
        result['current_engraving_context']={'evidence_sha256':PROOF_SHA,'slots_origin':ORIGIN,
            'scope':'environment calibration only; never opponent policy observation',
            'round_or_battle_counters_imported':False,'training_label_allowed':False}
    return result


def simulate_batch(battles,*,timeout=90):
    extension_contract();v17.extension_contract()
    v17.v16.extension_contract();v17.v16.v15.extension_contract();v17.v16.v15.v14.extension_contract()
    v17.v16.v15.v14.v13.extension_contract();v17.v16.v15.v14.v13.v12.extension_contract()
    module=v17.v16.v15.v14.v13.v12.v11
    for attr in ['v10','v9','v8','v7','v6','v5']:
        module.extension_contract();module=getattr(module,attr)
    module.extension_contract();module.v4.plant_contract();module.v4.v3.counter_contract();module.v4.v3.v2.extension_contract()
    if not isinstance(battles,list) or not 1<=len(battles)<=1000:raise ValueError('Require 1–1000 battles')
    node=shutil.which('node')
    if not node:raise SimulatorError('Node runtime is not on PATH')
    run=subprocess.run([node,'--experimental-default-type=module',str(BRIDGE)],input=json.dumps(battles,ensure_ascii=False,allow_nan=False),
        text=True,encoding='utf-8',cwd=ROOT,capture_output=True,timeout=timeout)
    if run.returncode:raise SimulatorError(run.stderr.strip())
    results=json.loads(run.stdout)
    if len(results)!=len(battles):raise SimulatorError('Batch result count mismatch')
    return {'results':results,'engine':engine_contract(),'adapter_contract':{'schema':'complete-single-battle-diagnostic-v20',
        'evidence_sha256':PROOF_SHA,'native_scheduler_reused':True,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),'current_server_verified':False,'training_label_allowed':False}
