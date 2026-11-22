"""Native admission for one previously audited dream consonance card."""
from pathlib import Path
import hashlib,json
from . import full_battle_v186 as previous
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/native-dream-consonance-v188.json'
PROOF_SHA='ba776fe116d806777406a8daf24bb067057af61cb5ea26dbbf8f781502f78fdf'
UnresolvedBattle=previous.UnresolvedBattle
derive_start_initiative=previous.derive_start_initiative

def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('native_dream_v188:evidence_changed')
    f=json.loads(raw)
    for name,h in f['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('native_dream_v188:source_changed:'+name)
    return f

def catalogue():
    f=extension_contract();cards,mapping,talents,season=previous.catalogue()
    for c in f['cards']:
        if c['raw_id'] in mapping or c['runtime_id'] in mapping.values():raise UnresolvedBattle('native_dream_v188:alias_collision')
        if cards[c['raw_id']]!=c['config']:raise UnresolvedBattle('native_dream_v188:config_changed')
        mapping[c['raw_id']]=c['runtime_id']
    return cards,mapping,talents,season

def compile_start(row,**kwargs):
    extension_contract()
    if 'tables' not in kwargs:kwargs['tables']=catalogue()
    return previous.compile_start(row,**kwargs)
