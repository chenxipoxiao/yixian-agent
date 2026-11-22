"""Source-bound native Nether Tempered Dagger entry; old versions stay frozen."""
from pathlib import Path
import hashlib
import json
from . import full_battle_v189r2 as previous

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / 'data/inspection/current-nether-dagger-v190.json'
PROOF_SHA = 'c67faef4916597f8a0204ee43834b736367ba5240d19cd811605b00584a56fb1'
UnresolvedBattle = previous.UnresolvedBattle
derive_start_initiative = previous.derive_start_initiative


def extension_contract():
    raw = PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROOF_SHA:
        raise UnresolvedBattle('nether_dagger_v190:evidence_changed')
    facts = json.loads(raw)
    for name, expected in facts['source_sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise UnresolvedBattle('nether_dagger_v190:source_changed:' + name)
    return facts


def catalogue():
    facts = extension_contract()
    cards, mapping, talents, season = previous.catalogue()
    for card in facts['cards']:
        if card['raw_id'] in mapping or card['runtime_id'] in mapping.values():
            raise UnresolvedBattle('nether_dagger_v190:alias_collision')
        if cards[card['raw_id']] != card['config']:
            raise UnresolvedBattle('nether_dagger_v190:config_changed')
        mapping[card['raw_id']] = card['runtime_id']
    return cards, mapping, talents, season


def compile_start(row, **kwargs):
    extension_contract()
    if 'tables' not in kwargs:
        kwargs['tables'] = catalogue()
    return previous.compile_start(row, **kwargs)
