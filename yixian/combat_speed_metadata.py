"""Pinned name-token/parameter context for client speed display diagnostics.

This is not a legal card-pool definition and does not certify server initiative.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import MappingProxyType

from .combat_initialization import ROOT, IncompleteCombatState

METADATA = 'data/inspection/conditional-speed-metadata-v1.json'
METADATA_HASH = 'f3298c0d2c02925b652f8ab048d6cc0ed58359cc9f8e76721c31a7cd155713dd'
EVIDENCE = 'data/inspection/conditional-speed-evidence-v1.json'
EVIDENCE_HASH = 'ce6c24b3ca0dc8a7b9bc0077f14e4da6a6d4536f442feb1a4226a83fcf4ec8a5'


@dataclass(frozen=True)
class SpeedMetadata:
    card_tokens: MappingProxyType
    talent_speed: MappingProxyType
    engraving_speed: MappingProxyType
    metadata_sha256: str
    evidence_sha256: str


def load_speed_metadata(root=ROOT):
    loaded = []
    for name, expected in ((METADATA, METADATA_HASH), (EVIDENCE, EVIDENCE_HASH)):
        raw = (Path(root)/name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError(f'Conditional speed evidence hash mismatch: {name}')
        loaded.append(json.loads(raw))
    data, evidence = loaded
    if data['schema_version'] != 1 or evidence['schema_version'] != 1:
        raise ValueError('Unsupported conditional speed schema')
    return SpeedMetadata(
        MappingProxyType({int(k): tuple(v) for k,v in data['card_element_tokens'].items()}),
        MappingProxyType({int(k): v for k,v in data['talent_speed'].items()}),
        MappingProxyType({int(k): v for k,v in data['engraving_speed'].items()}),
        METADATA_HASH, EVIDENCE_HASH,
    )


def conditional_speed_contract(root=ROOT):
    metadata = load_speed_metadata(root)
    return {'metadata_sha256': metadata.metadata_sha256, 'evidence_sha256': metadata.evidence_sha256,
            'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'talent_ids': list(metadata.talent_speed), 'engraving_ids': list(metadata.engraving_speed),
            'board_source': 'explicit lastRoundData.usedCards; ordered, zero not filtered',
            'unknown_card_or_parameter': 'reject', 'metadata_requires_explicit_opt_in': True,
            'legal_pool_claim': False, 'server_parity_verified': False, 'training_label_allowed': False}


def _same_wuxing(ordered_card_tokens):
    """Mirror the name scan, including its first matching card's early break."""
    selected = None
    for tokens in ordered_card_tokens:
        for token in tokens:
            if selected is None:
                selected = token
                break
            if selected != token:
                return False
    return selected is not None


def conditional_speed_components(start, talents, engravings, metadata):
    if not isinstance(metadata, SpeedMetadata):
        raise IncompleteCombatState('Explicit pinned SpeedMetadata required')
    conditional = [t for t in talents if t % 10000 == 128]
    talent_components = []
    if conditional:
        cards = start.get('usedCards')
        if (not isinstance(cards, list) or len(cards) > 8
                or any(type(c) is not int or c not in metadata.card_tokens for c in cards)):
            raise IncompleteCombatState('Explicit known ordered usedCards required for family128')
        same = _same_wuxing([metadata.card_tokens[c] for c in cards])
        override = 278 in talents
        for identifier in conditional:
            if identifier not in metadata.talent_speed:
                raise IncompleteCombatState('Unknown exact family128 parameter')
            talent_components.append({'id': identifier, 'same_wuxing': same,
                                      'exact_278_override': override,
                                      'speed': metadata.talent_speed[identifier] if same or override else 0})
    engraving_components = []
    for identifier in engravings:
        if identifier % 10000 == 42:
            if identifier not in metadata.engraving_speed:
                raise IncompleteCombatState('Unknown exact family42 parameter; client fallback unsupported')
            engraving_components.append({'id': identifier, 'speed': metadata.engraving_speed[identifier]})
    return talent_components, engraving_components
