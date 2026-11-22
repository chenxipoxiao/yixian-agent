"""Ordinary fate 27's damage cap; its once-only upgrade is not implemented.

The pinned client bypasses ordinary fate modifiers for mirrors and players
already eliminated before battle. This component never reads a usage counter:
the damage cap and the one-time post-battle upgrade are separate effects.
"""
from pathlib import Path
import hashlib

IMPLEMENTED_DRAGON_SCALE_COMPONENT_IDS = frozenset({27})


def cap_damage(damage, *, life_before_battle, is_mirror=False, limit=20):
    if type(damage) is not int or damage < 0:
        raise ValueError('Destiny damage must be a nonnegative integer')
    if type(limit) is not int or limit < 1:
        raise ValueError('Dragon Scale limit must be a positive integer')
    if type(life_before_battle) is not int:
        raise ValueError('Dragon Scale requires explicit pre-battle destiny')
    if type(is_mirror) is not bool:
        raise ValueError('Mirror status must be boolean')
    return damage if is_mirror or life_before_battle <= 0 else min(damage, limit)


def contract():
    return {'schema_version': 1, 'ordinary_fate_id': 27,
            'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'implemented_components': ['destiny_damage_cap'],
            'unimplemented_components': ['first_low_destiny_permanent_card_upgrade',
                                         'upgrade_candidate_selection_and_persistent_usage'],
            'damage_cap_uses_upgrade_counter': False,
            'default_mirror_status_in_offline_api': False,
            'relative_order': [27, 45, 105, 'single_available_death_prevention'],
            'evidence': 'data/inspection/dragon-scale-cap-v1.json',
            'whole_effect_implemented': False, 'current_server_rules_verified': False}
