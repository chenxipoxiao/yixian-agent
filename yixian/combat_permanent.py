"""Recover the pinned client's InitData physique boundary, not a full battle.

Permanent snapshot maps also contain noncombat counters. Only the two fields
explicitly read in InitData become combat buffs here; later hooks remain pending.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .combat_initialization import (
    ROOT, IncompleteCombatState, derive_base_combat_state, load_initialization_contract,
)

EVIDENCE = 'data/inspection/permanent-combat-initialization-v1.json'
EVIDENCE_HASH = '96ca3160c125975fb23cbb8569b8474727d1021105ac8cb0d6d173825dc69724'
BOUNDARY = 'after_InitData_physique_before_OnBattleStarted'
PHYSIQUE = '10023'
PHYSIQUE_CAP = '10024'


def load_permanent_initialization_contract(root=ROOT):
    root = Path(root)
    raw = (root/EVIDENCE).read_bytes()
    if hashlib.sha256(raw).hexdigest() != EVIDENCE_HASH:
        raise ValueError('Permanent initialization evidence hash mismatch')
    evidence = json.loads(raw)
    base = load_initialization_contract(root)
    if evidence['client_dll_sha256'] != base['client_dll_sha256']:
        raise ValueError('Base and permanent initialization client versions differ')
    return {'schema_version': 1, 'scope': evidence['scope'], 'game_mode_scope': 3,
            'base_initialization': base, 'evidence_sha256': EVIDENCE_HASH,
            'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'boundary': BOUNDARY, 'raw_buff_ids': [10023, 10024],
            'missing_map_policy': 'reject; an explicitly present empty map is distinct',
            'other_permanent_entries': 'defer without assigning battle semantics',
            'server_parity_verified': False, 'complete_battle_input': False}


def _permanent_map(public_data):
    if not isinstance(public_data, Mapping) or not isinstance(public_data.get('lastRoundData'), Mapping):
        raise IncompleteCombatState('publicData.lastRoundData required')
    start = public_data['lastRoundData']
    if 'permanentBuffTempDatas' not in start or not isinstance(start['permanentBuffTempDatas'], Mapping):
        raise IncompleteCombatState('Explicit lastRoundData.permanentBuffTempDatas map required')
    result = {}
    for key, value in start['permanentBuffTempDatas'].items():
        if not isinstance(key, str) or not key.isascii() or not key.isdecimal() or str(int(key)) != key or int(key) <= 0:
            raise IncompleteCombatState('Permanent buff keys must be positive canonical decimal strings')
        if type(value) is not int or abs(value) > 1_000_000:
            raise IncompleteCombatState('Permanent buff values must be bounded explicit integers')
        result[key] = value
    return result


def derive_permanent_combat_state(public_data, *, contract=None, game_mode=3):
    """Derive afresh from a pre-battle snapshot; never update an evolved state.

    Positive physique increases max_hp without healing. Its cap is a separately
    stored buff, not a reason to clamp the recorded physique or derive a value
    from round number. Source timing and later opening effects remain unverified.
    """
    contract = contract or load_permanent_initialization_contract()
    if type(game_mode) is not int or game_mode != contract['game_mode_scope'] or game_mode != 3:
        raise IncompleteCombatState('Only explicitly scoped ordinary mode 3 is supported')
    permanent = _permanent_map(public_data)
    result = derive_base_combat_state(public_data, contract=contract['base_initialization'])
    base = deepcopy(result['base_combat'])
    combat = deepcopy(base)
    physique = max(0, permanent.get(PHYSIQUE, 0))
    cap = max(0, permanent.get(PHYSIQUE_CAP, 0))
    combat['max_hp'] += physique
    combat['raw_buffs'] = {key: permanent[key] for key in (PHYSIQUE, PHYSIQUE_CAP) if permanent.get(key, 0) > 0}
    combat.update(physique=physique, physique_cap=cap)
    # Keep the preceding boundary intact for audits and avoid an ambiguous field
    # named base_combat containing post-initialization values.
    result.update(scope='candidate_combat_after_InitData_physique', initialized_combat=combat,
                  permanent_input=deepcopy(permanent),
                  input_evidence=dict(result['input_evidence'], permanent_map_explicit=True,
                                      physique_entry_present=PHYSIQUE in permanent,
                                      physique_cap_entry_present=PHYSIQUE_CAP in permanent),
                  initialization_events=[{'source': 'lastRoundData.permanentBuffTempDatas',
                      'buff_id': 10023, 'raw_value': permanent.get(PHYSIQUE, 0),
                      'max_hp_delta': physique, 'hp_delta': 0},
                      {'source': 'lastRoundData.permanentBuffTempDatas', 'buff_id': 10024,
                       'raw_value': permanent.get(PHYSIQUE_CAP, 0), 'stored_cap': cap, 'max_hp_delta': 0, 'hp_delta': 0}],
                  deferred_permanent_entries={key: value for key, value in permanent.items() if key not in (PHYSIQUE, PHYSIQUE_CAP)},
                  boundary=BOUNDARY, initialization_component_applied=True,
                  complete_permanent_effects_applied=False, reapplied_acquisition_rewards=False,
                  pending_before_battle=['later_permanent_buff_hooks', 'ordinary_and_seasonal_start_effects',
                      'cross_effect_order', 'raw_card_execution_mapping', 'snapshot_timing_calibration'])
    return result
