"""Expose the audited 402 executor to native snapshots without changing rules."""
from pathlib import Path
import hashlib
import json
from . import full_battle_v180 as previous
from . import full_battle_v142 as audited

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / 'data/inspection/native-cloud-steps-v186.json'
PROOF_SHA = '9ade3f659234f226a153df40e13419cc0547ce70eb5a4e25a64cf11830387bcc'
UnresolvedBattle = previous.UnresolvedBattle
derive_start_initiative = previous.derive_start_initiative


def extension_contract():
    raw = PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROOF_SHA:
        raise UnresolvedBattle('native_cloud_steps_v186:evidence_changed')
    facts = json.loads(raw)
    for name, expected in facts['source_sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise UnresolvedBattle('native_cloud_steps_v186:source_changed:' + name)
    return facts


def catalogue():
    facts = extension_contract()
    card = next(c for c in audited.extension_contract()['cards'] if c['raw_id'] == facts['raw_id'])
    cards, mapping, talents, season = previous.catalogue()
    if (card['runtime_id'] != facts['runtime_id'] or cards[402] != card['config']
            or 402 in mapping or card['runtime_id'] in mapping.values()):
        raise UnresolvedBattle('native_cloud_steps_v186:identity_mismatch')
    mapping[402] = card['runtime_id']
    return cards, mapping, talents, season


def compile_start(row, **kwargs):
    extension_contract()
    if 'tables' not in kwargs:
        kwargs['tables'] = catalogue()
    return previous.compile_start(row, **kwargs)
