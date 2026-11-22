"""Pinned OpenConfig74 healing correction; all v82 start admission is retained."""
import hashlib,json
from pathlib import Path
from . import full_battle_v82 as previous
from . import full_battle_v80 as core
from .combat_compiler_view_v81 import isolated_compiler
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-nonpositive-healing-v83.json'
PROOF_SHA='dba6ecef00b482e5368b02ec2e4320a68d31eea0306cebf2004d9f93370670b4'
BRIDGE=ROOT/'tools/full_battle_bridge_v83.mjs'
UnresolvedBattle=previous.UnresolvedBattle
catalogue=previous.catalogue
derive_start_initiative=previous.derive_start_initiative
def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('healing_v83:evidence_changed')
    facts=json.loads(raw)
    for name,h in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('healing_v83:source_changed:'+name)
    return facts
def compile_start(row,**kwargs):
    extension_contract()
    return previous.compile_start(row,**kwargs)
def simulate_batch(battles,*,timeout=90):
    extension_contract();previous.extension_contract();previous.previous.extension_contract()
    result=isolated_compiler(core,runtime_bridge=BRIDGE).simulate_batch(battles,timeout=timeout)
    result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v83',
        'evidence_sha256':PROOF_SHA,'fixed_local_open_feature_74':True,'training_label_allowed':False}
    return result
