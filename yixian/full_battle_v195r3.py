"""Observed level-five dream water surge; earlier contracts frozen."""
from pathlib import Path
import hashlib
import json
from . import full_battle_v194 as previous

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / 'data/inspection/current-dream-water-v195r3.json'
PROOF_SHA = '1342ad7ea8032cdbb0e19128be60a89626f82522ce28867763fc446f8fbe84e0'
UnresolvedBattle = previous.UnresolvedBattle
derive_start_initiative = previous.derive_start_initiative

def extension_contract():
    raw = PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROOF_SHA:
        raise UnresolvedBattle('dream_water_v195r3:evidence_changed')
    facts = json.loads(raw)
    for name, expected in facts['source_sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise UnresolvedBattle('dream_water_v195r3:source_changed:' + name)
    return facts

def catalogue():
    facts = extension_contract()
    cards, mapping, talents, season = previous.catalogue()
    for card in facts['cards']:
        if card['raw_id'] in mapping or card['runtime_id'] in mapping.values():
            raise UnresolvedBattle('dream_water_v195r3:alias_collision')
        if cards[card['raw_id']] != card['config']:
            raise UnresolvedBattle('dream_water_v195r3:config_changed')
        mapping[card['raw_id']] = card['runtime_id']
    return cards, mapping, talents, season

def compile_start(row, **kwargs):
    extension_contract()
    if 'tables' not in kwargs:
        kwargs['tables'] = catalogue()
    return previous.compile_start(row, **kwargs)
