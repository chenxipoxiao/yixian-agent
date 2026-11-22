"""Exact extreme raven attack, qi and defense entry; earlier contracts frozen."""
from pathlib import Path
import hashlib
import json
from . import full_battle_v191r2 as previous

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / 'data/inspection/current-extreme-raven-v192.json'
PROOF_SHA = '1b209a40d31f12942c07506aa334e05876a94ec70b81b180a6bf72e94cfb6f07'
UnresolvedBattle = previous.UnresolvedBattle
derive_start_initiative = previous.derive_start_initiative

def extension_contract():
    raw = PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROOF_SHA:
        raise UnresolvedBattle('extreme_raven_v192:evidence_changed')
    facts = json.loads(raw)
    for name, expected in facts['source_sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise UnresolvedBattle('extreme_raven_v192:source_changed:' + name)
    return facts

def catalogue():
    facts = extension_contract()
    cards, mapping, talents, season = previous.catalogue()
    for card in facts['cards']:
        if card['raw_id'] in mapping or card['runtime_id'] in mapping.values():
            raise UnresolvedBattle('extreme_raven_v192:alias_collision')
        if cards[card['raw_id']] != card['config']:
            raise UnresolvedBattle('extreme_raven_v192:config_changed')
        mapping[card['raw_id']] = card['runtime_id']
    return cards, mapping, talents, season

def compile_start(row, **kwargs):
    extension_contract()
    if 'tables' not in kwargs:
        kwargs['tables'] = catalogue()
    return previous.compile_start(row, **kwargs)
