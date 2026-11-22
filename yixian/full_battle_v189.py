"""Admit the exact source-backed first-rarity Exquisite Sword Formation."""
from pathlib import Path
import hashlib,json
from . import full_battle_v188 as previous
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-exquisite-sword-v189.json'
PROOF_SHA='ddd0a99b3b05ef54f240184e03096815f03b14fe7d19a6e9fcac7ebd4b3baf5c'
UnresolvedBattle=previous.UnresolvedBattle
derive_start_initiative=previous.derive_start_initiative

def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('exquisite_v189:evidence_changed')
    f=json.loads(raw)
    for name,h in f['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('exquisite_v189:source_changed:'+name)
    return f

def catalogue():
    f=extension_contract();cards,mapping,talents,season=previous.catalogue()
    for c in f['cards']:
        if c['raw_id'] in mapping or c['runtime_id'] in mapping.values():raise UnresolvedBattle('exquisite_v189:alias_collision')
        if cards[c['raw_id']]!=c['config']:raise UnresolvedBattle('exquisite_v189:config_changed')
        mapping[c['raw_id']]=c['runtime_id']
    return cards,mapping,talents,season

def compile_start(row,**kwargs):
    extension_contract()
    for player in row['players']:
        if 222 in player['candidate_start']['talents']:
            raise UnresolvedBattle('exquisite_v189:talent222_branch_not_admitted')
    if 'tables' not in kwargs:kwargs['tables']=catalogue()
    return previous.compile_start(row,**kwargs)
