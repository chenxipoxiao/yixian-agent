"""Observed grade-three and grade-five dream cloud dot star; earlier contracts frozen."""
from pathlib import Path
import hashlib
import json
from . import full_battle_v195r3 as previous

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / 'data/inspection/current-dot-star-v196.json'
PROOF_SHA = 'a1c1ba626c293fc16924d3ce631c59d7d82bd3ee32f656f0064322bd66fd4d38'
UnresolvedBattle = previous.UnresolvedBattle
derive_start_initiative = previous.derive_start_initiative

def extension_contract():
    raw = PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROOF_SHA:
        raise UnresolvedBattle('dot_star_v196:evidence_changed')
    facts = json.loads(raw)
    for name, expected in facts['source_sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise UnresolvedBattle('dot_star_v196:source_changed:' + name)
    return facts

def catalogue():
    facts = extension_contract()
    cards, mapping, talents, season = previous.catalogue()
    for card in facts['cards']:
        if card['raw_id'] in mapping or card['runtime_id'] in mapping.values():
            raise UnresolvedBattle('dot_star_v196:alias_collision')
        if cards[card['raw_id']] != card['config']:
            raise UnresolvedBattle('dot_star_v196:config_changed')
        mapping[card['raw_id']] = card['runtime_id']
    return cards, mapping, talents, season

def compile_start(row, **kwargs):
    extension_contract()
    if 'tables' not in kwargs:
        kwargs['tables'] = catalogue()
    return previous.compile_start(row, **kwargs)
