"""Three current card families over the frozen native full-battle scheduler."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from . import full_battle_v4 as v4
from .simulator import engine_contract, SimulatorError

ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-cloud-cards-v5.json'
PROOF_SHA='f9fa41a2eeae81c58a01865f3b9b08e8c26d9349a51f4d978e4f733159f4f906'
BRIDGE=ROOT/'tools/full_battle_bridge_v5.mjs'
UnresolvedBattle=v4.UnresolvedBattle
derive_start_initiative=v4.derive_start_initiative


def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:
        raise UnresolvedBattle('Current cloud card evidence changed')
    facts=json.loads(raw)
    for source,key in [('data/local/2026-11-06/tables/CardConfig.json','card_table_sha256'),
                       ('external/yisim/gamestate_full.js','native_engine_sha256')]:
        if hashlib.sha256((ROOT/source).read_bytes()).hexdigest()!=facts[key]:
            raise UnresolvedBattle('Current cloud card source changed')
    return facts


def catalogue():
    cards,mapping,talents,season=v4.catalogue()
    facts=extension_contract()
    for family in facts['families']:
        for card,alias in zip(family['cards'],family['runtime_ids']):
            if card['id'] in mapping or alias in mapping.values():
                raise UnresolvedBattle('Existing card mapping may not be replaced')
            mapping[card['id']]=alias
    return cards,mapping,talents,season


def compile_start(row,**kwargs):
    facts=extension_contract()
    if 'tables' not in kwargs:kwargs['tables']=catalogue()
    result=v4.compile_start(row,**kwargs)
    ids={c['id'] for f in facts['families'] for c in f['cards']}
    result['current_cloud_card_extension']={'schema':5,'proof_sha256':PROOF_SHA,
        'present_raw_ids':sorted({c for p in result['declared_components'] for c in p['raw_cards'] if c in ids}),
        'runtime_aliases_only':True,'native_scheduler_reused':True,'training_label_allowed':False}
    return result


def simulate_batch(battles,*,timeout=90):
    extension_contract();v4.plant_contract();v4.v3.counter_contract();v4.v3.v2.extension_contract()
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
        'adapter_contract':{'schema':'complete-single-battle-diagnostic-v5','proof_sha256':PROOF_SHA,
            'native_scheduler_reused':True,'old_versions_unchanged':True,
            'opening_terminal_supported':False,'full_match_environment':False,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),
        'implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'current_server_verified':False,'training_label_allowed':False}
