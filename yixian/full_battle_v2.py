"""Optional current sword-card extension; the frozen v1 path is unchanged."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from . import full_battle as v1
from .simulator import engine_contract, SimulatorError

ROOT=Path(__file__).resolve().parents[1]
BRIDGE=ROOT/'tools/full_battle_bridge_v2.mjs'
PROOF=ROOT/'data/inspection/current-sword-cards-v2.json'
UnresolvedBattle=v1.UnresolvedBattle
derive_start_initiative=v1.derive_start_initiative


def extension_contract():
    raw=PROOF.read_bytes();facts=json.loads(raw)
    if hashlib.sha256(raw).hexdigest()!='caf6ee89c9a4515ee36d60b3d9078b5ddc72a2132925ef301f8cc233119e35b9':
        raise ValueError('Current sword evidence changed')
    table=ROOT/'data/local/2026-11-06/tables/CardConfig.json'
    if hashlib.sha256(table.read_bytes()).hexdigest()!=facts['card_table_sha256']:
        raise ValueError('Current sword card table changed')
    return facts,hashlib.sha256(raw).hexdigest()


def catalogue():
    cards,mapping,talents,season=v1.catalogue()
    facts,_=extension_contract()
    for family in facts['families']:
        for card,alias in zip(family['cards'],family['runtime_ids']):
            if card['id'] in mapping:raise ValueError('Existing mapped card may not be silently replaced')
            mapping[card['id']]=alias
    return cards,mapping,talents,season


def compile_start(row,**kwargs):
    if 'tables' not in kwargs:kwargs['tables']=catalogue()
    result=v1.compile_start(row,**kwargs)
    facts,digest=extension_contract()
    ids={c['id'] for f in facts['families'] for c in f['cards']}
    result['current_card_extension']={'schema':2,'proof_sha256':digest,
        'present_raw_ids':sorted({c for p in result['declared_components'] for c in p['raw_cards'] if c in ids}),
        'runtime_aliases_only':True,'training_label_allowed':False}
    return result


def simulate_batch(battles,*,timeout=90):
    engine=engine_contract();_,digest=extension_contract()
    if not isinstance(battles,list) or not battles or len(battles)>1000:raise ValueError('Require 1–1000 battles')
    node=shutil.which('node')
    if not node:raise SimulatorError('Node runtime is not on PATH')
    run=subprocess.run([node,'--experimental-default-type=module',str(BRIDGE)],
        input=json.dumps(battles,ensure_ascii=False,allow_nan=False),text=True,encoding='utf-8',
        cwd=ROOT,capture_output=True,timeout=timeout)
    if run.returncode:raise SimulatorError(run.stderr.strip())
    results=json.loads(run.stdout)
    if len(results)!=len(battles):raise SimulatorError('Batch result count mismatch')
    return {'results':results,'engine':engine,
        'adapter_contract':{'schema':'complete-single-battle-diagnostic-v2','proof_sha256':digest,
            'slot_count':'1-8 explicit slots','full_match_environment':False,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),
        'implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'current_server_verified':False,'training_label_allowed':False}
