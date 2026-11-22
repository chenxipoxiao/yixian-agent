"""Recover the client's base combat state, before all initialization effects.

This is not a complete battle adapter. It deliberately cannot produce a training
label or claim that the replay provider's snapshot timing has been validated.
"""
from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEVELS = 'data/local/2026-11-06/tables/LevelConfig.json'
LEVEL_HASH = '3acb6a40e9cefacb8e7bc5133eb4469d894f10af852c9e6026b87db4d6fcdd9b'
EVIDENCE = 'data/inspection/base-combat-initialization-v1.json'
EVIDENCE_HASH = '753a02721b499afdbc0447fa3b70e34a68c7c610ec3826e8e0646d7af33cd01f'


class IncompleteCombatState(ValueError):
    """Missing/ambiguous evidence must not be repaired with later state."""


def _read_pinned(root, name, expected):
    raw = (Path(root)/name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f'Initialization evidence hash mismatch: {name}')
    return json.loads(raw)


def load_initialization_contract(root=ROOT):
    facts = _read_pinned(root, EVIDENCE, EVIDENCE_HASH)
    levels = _read_pinned(root, LEVELS, LEVEL_HASH)
    values = {row['level']: row['baseMaxHp'] for row in levels}
    if (values != {1: 40, 2: 45, 3: 52, 4: 62, 5: 75, 6: 100}
            or facts['level_config_sha256'] != LEVEL_HASH):
        raise ValueError('Unexpected pinned realm HP table')
    return {'schema_version': 1, 'scope': facts['scope'],
            'realm_base_hp': {str(k): v for k, v in values.items()}, 'client_dll_sha256': facts['client_dll_sha256'],
            'level_config_sha256': LEVEL_HASH, 'evidence_sha256': EVIDENCE_HASH,
            'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'boundary': 'before_InitData_and_OnBattleStarted_effects',
            'server_parity_verified': False, 'complete_battle_input': False}


def _int_field(source, name, *, minimum=None):
    if name not in source or type(source[name]) is not int:
        raise IncompleteCombatState(f'Explicit integer {name} required')
    value = source[name]
    if abs(value) > 1_000_000 or minimum is not None and value < minimum:
        raise IncompleteCombatState(f'Out-of-scope {name}')
    return value


def _card_array(source, name, *, minimum_size=0):
    if name not in source or not isinstance(source[name], list):
        raise IncompleteCombatState(f'Explicit {name} array required')
    values = source[name]
    if not minimum_size <= len(values) <= 8 or any(type(c) is not int or c < 0 for c in values):
        raise IncompleteCombatState(f'Invalid or out-of-scope {name}')
    return list(values)


def derive_base_combat_state(public_data, *, contract=None):
    """Translate only fields read by CreateTempData and GetStartMaxHp.

    Client IL explicitly reads publicData.level. A disagreeing lastRoundData.level
    is preserved as an unresolved timing flag; it is not silently substituted.
    Current public hp, extraMaxHp, private board/hand and outcomes are ignored.
    """
    contract = contract or load_initialization_contract()
    if not isinstance(public_data, Mapping) or not isinstance(public_data.get('lastRoundData'), Mapping):
        raise IncompleteCombatState('publicData.lastRoundData is required')
    start = public_data['lastRoundData']
    level = _int_field(public_data, 'level', minimum=0)
    last_level = _int_field(start, 'level', minimum=0) if 'level' in start else None
    if level != 0 and str(level) not in contract['realm_base_hp']:
        raise IncompleteCombatState('Unknown public realm level')
    extra = _int_field(start, 'extraMaxHp')
    base = 0 if level == 0 else contract['realm_base_hp'][str(level)]
    hp = base + extra
    if hp <= 0:
        raise IncompleteCombatState('Nonpositive base HP outside this active-battle adapter')
    cards = _card_array(start, 'usedCards', minimum_size=1)
    keyin = _card_array(start, 'usedKeYinCards')
    return {'schema_version': 1, 'scope': 'candidate_base_combat_initialization',
            'base_combat': {'hp': hp, 'max_hp': hp, 'qi': 0, 'def': 0,
                            'action_again_per_round': 1, 'raw_cards': cards,
                            'raw_keyin_cards': keyin},
            'input_evidence': {'public_level': level, 'last_round_level': last_level,
                               'realm_base_max_hp': base, 'last_round_extra_max_hp': extra},
            'snapshot_levels_agree': level == last_level if last_level is not None else None,
            'source_timing_verified': False, 'effects_applied': False,
            'reapplied_acquisition_rewards': False, 'complete_battle_input': False,
            'training_label_allowed': False, 'server_parity_verified': False,
            'boundary': contract['boundary'],
            'pending_before_battle': ['permanent_buff_application', 'ordinary_and_seasonal_start_effects',
                                      'cross_effect_order', 'raw_card_execution_mapping', 'snapshot_timing_calibration']}
