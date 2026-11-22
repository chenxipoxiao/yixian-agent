"""Versioned Nether Dagger identity closure; v190 remains immutable."""
from pathlib import Path
import hashlib, json
from . import full_battle_v190 as previous
ROOT = Path(__file__).resolve().parents[1]
UnresolvedBattle = previous.UnresolvedBattle
derive_start_initiative = previous.derive_start_initiative
def extension_contract():
    raw = (ROOT / 'data/inspection/current-nether-dagger-identities-v190r2.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != '5b96545f90d6b8d65c6d7ce9d1af573318dc7451126d258cc24b1af8b67a2bfa':
        raise UnresolvedBattle('nether_dagger_v190r2:evidence_changed')
    facts = json.loads(raw)
    for name, expected in facts['source_sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise UnresolvedBattle('nether_dagger_v190r2:source_changed:' + name)
    return facts
def catalogue():
    extension_contract()
    return previous.catalogue()
def compile_start(row, **kwargs):
    extension_contract()
    if 'tables' not in kwargs:
        kwargs['tables'] = catalogue()
    return previous.compile_start(row, **kwargs)
