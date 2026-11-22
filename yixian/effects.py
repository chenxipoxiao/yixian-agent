"""A small, explicit executable subset of Yi Xian fate effects.

These hooks operate on copied offline state. They do not simulate cards, infer
server candidate pools, or certify that an otherwise unsupported battle is
correct. Persistent effect_state belongs to the simulated match, not a replay.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .research import canonical_json
from .season_start import (apply_season_start, IMPLEMENTED_SEASON_START_IDS,
                           TOGGLEABLE_SEASON_IDS, PARTIAL_SEASON_IDS, DEFAULT_PARAMETERS, NATIVE_SEASON_IDS)
from .death_fates import (initialize_death_fates, apply_death_prevention, DEATH_FATES,
                         contract as death_contract, UnknownDeathFateState)
from .dragon_scale import cap_damage, contract as dragon_scale_contract
from .dragon_scale_reward import PENDING as DRAGON_SCALE_PENDING, contract as dragon_reward_contract
from .dragon_inheritance import PENDING as INHERITANCE_PENDING, contract as inheritance_contract

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_FATES = frozenset({7, 45, 65, 105, 154})
SUPPORTED_SEASON = frozenset({2011}) | (IMPLEMENTED_SEASON_START_IDS - PARTIAL_SEASON_IDS)


class UnknownEffectState(ValueError):
    """A persistent effect cannot be evaluated without its initial state."""


def _integer(value, label, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{label} must be an integer >= {minimum}')
    return value


def _ids(player, field):
    values = player.get(field, [])
    if not isinstance(values, list):
        raise ValueError(f'{field} must be a list')
    result = set()
    for item in values:
        if isinstance(item, dict) and field == 'season_choices':
            if item.get('kind') == 'skip':
                continue
            if item.get('kind') != 'select':
                raise ValueError('A season receipt needs kind=select or skip')
            item = item.get('selected')
        if not ((type(item) is int and item > 0) or (isinstance(item, str) and item)):
            raise ValueError(f'Invalid effect id in {field}')
        result.add(item)
    return result


def _copy(player):
    if not isinstance(player, Mapping):
        raise ValueError('Player effect state must be an object')
    canonical_json(player)
    result = deepcopy(dict(player))
    _ids(result, 'fates')
    _ids(result, 'season_choices')
    state = result.setdefault('effect_state', {'schema_version': 1})
    if not isinstance(state, dict) or type(state.get('schema_version')) is not int or state.get('schema_version') != 1:
        raise ValueError('Unknown effect-state schema')
    disabled = state.setdefault('disabled_season_ids', [])
    if not isinstance(disabled, list) or any(type(x) is not int or x not in TOGGLEABLE_SEASON_IDS for x in disabled):
        raise ValueError('Invalid disabled effect IDs')
    if len(set(disabled)) != len(disabled):
        raise ValueError('Repeated disabled effect ID')
    if 'talent_105_remaining' in state and (type(state['talent_105_remaining']) is not int or state['talent_105_remaining'] not in (0, 1)):
        raise ValueError('Talent 105 remaining uses must be 0 or 1')
    if 'season_1001_initialized' in state and type(state['season_1001_initialized']) is not bool:
        raise ValueError('Season switch initialization marker must be boolean')
    return result


class EffectEngine:
    def __init__(self, *, start_qi=2, kindness_reduction=1, guard_threshold=15, dragon_scale_limit=20,
                 source=None, season_parameters=None):
        self.start_qi = _integer(start_qi, 'start_qi', 1)
        self.kindness_reduction = _integer(kindness_reduction, 'kindness_reduction', 1)
        self.guard_threshold = _integer(guard_threshold, 'guard_threshold', 1)
        self.dragon_scale_limit = _integer(dragon_scale_limit, 'dragon_scale_limit', 1)
        self.season_parameters = deepcopy(season_parameters or DEFAULT_PARAMETERS)
        self.season_parameters[1001] = [self.start_qi]
        self.source = deepcopy(source or {'kind': 'local_snapshot_reference_defaults',
                                         'asset_catalog': '2026.11.06.06.05.32'})

    @classmethod
    def from_local(cls, root=ROOT/'data/local/2026-11-06'):
        root = Path(root)
        paths = {'season': root/'season/XianMoStrategyConfig.json', 'talents': root/'tables/TalentConfig.json'}
        content = {key:path.read_bytes() for key, path in paths.items()}
        season = {row['id']:row for row in json.loads(content['season'])}
        talents = {row['id']:row for row in json.loads(content['talents'])}
        return cls(start_qi=season[1001]['otherParams'][0], kindness_reduction=season[2011]['otherParams'][0],
                   guard_threshold=talents[105]['otherParams'][0],
                   dragon_scale_limit=talents[27]['otherParams'][0],
                   season_parameters={identifier:season[identifier]['otherParams'] for identifier in IMPLEMENTED_SEASON_START_IDS},
                   source={'kind': 'local_extracted_configuration',
                           'sha256': {key:hashlib.sha256(value).hexdigest() for key,value in content.items()}})

    def contract(self):
        return {'schema_version': 1, 'supported_regular_fates': sorted(SUPPORTED_FATES),
                'supported_season_effects': sorted(SUPPORTED_SEASON),
                'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'season_start_sha256': hashlib.sha256((ROOT/'yixian/season_start.py').read_bytes()).hexdigest(),
                'battle_start_component_ids': sorted(IMPLEMENTED_SEASON_START_IDS),
                'native_battle_component_ids': sorted(NATIVE_SEASON_IDS),
                'death_fates': death_contract(),
                'dragon_scale': dragon_scale_contract(),
                'optional_dragon_scale_reward': dragon_reward_contract(),
                'optional_dragon_inheritance_draw': inheritance_contract(),
                'relative_settlement_order': [2011, 27, 45, 105, 'single_available_death_prevention'],
                'parameters': {'start_qi': self.start_qi, 'kindness_reduction': self.kindness_reduction,
                               'guard_threshold': self.guard_threshold, 'dragon_scale_limit': self.dragon_scale_limit},
                'source': deepcopy(self.source), 'complete_current_season_rules': False,
                'scope': 'registered_effect_components_on_explicit_offline_state'}

    @staticmethod
    def coverage(player):
        fates, season = _ids(player, 'fates'), _ids(player, 'season_choices')
        order = lambda value: (type(value).__name__, str(value))
        return {'supported_fates': sorted(fates & SUPPORTED_FATES),
                'supported_season': sorted(season & SUPPORTED_SEASON),
                'unsupported_fates': sorted(fates - SUPPORTED_FATES, key=order),
                'conditional_fates': sorted(fates & {83}),
                'partial_fates': sorted(fates & {27}),
                'partial_fate_components': {'27': ['destiny_damage_cap']} if 27 in fates else {},
                'unsupported_season': sorted(season - SUPPORTED_SEASON, key=order),
                'partial_season': sorted(season & PARTIAL_SEASON_IDS),
                'requires_native_runtime': sorted(season & NATIVE_SEASON_IDS),
                'complete_rule_execution': False}

    def initialize_player(self, player, *, newly_acquired_fates=(), talent_counters=None, season_temp_datas=None):
        """Initialize missing ledgers once; existing simulated state always wins.

        Imported ordinary-fate counters use the client's raw talentTempDatas.
        Pass newly_acquired_fates=(105,) only when an actual acquisition occurs.
        Missing imported usage state is an error, never a free immunity refill.
        """
        result = _copy(player)
        state = result['effect_state']
        fates, season = _ids(result, 'fates'), _ids(result, 'season_choices')
        if isinstance(newly_acquired_fates, (str, bytes)):
            raise ValueError('newly_acquired_fates must contain integer ids')
        try:
            newly_acquired_fates = tuple(newly_acquired_fates)
        except TypeError as error:
            raise ValueError('newly_acquired_fates must contain integer ids') from error
        if any(type(x) is not int for x in newly_acquired_fates):
            raise ValueError('newly_acquired_fates must contain integer ids')
        if any(x not in fates for x in newly_acquired_fates):
            raise ValueError('A newly acquired fate must already be owned')
        if talent_counters is not None and not isinstance(talent_counters, Mapping):
            raise ValueError('talent_counters must be a mapping')
        if season_temp_datas is not None and not isinstance(season_temp_datas, Mapping):
            raise ValueError('season_temp_datas must be a mapping')
        if 105 in fates and 'talent_105_remaining' not in state:
            if 105 in newly_acquired_fates:
                state['talent_105_remaining'] = 1
            else:
                state['talent_105_remaining'] = self._guard_remaining_from_raw(talent_counters)
        for identifier in sorted(season & TOGGLEABLE_SEASON_IDS):
            marker = f'season_{identifier}_initialized'
            if state.get(marker, False):
                continue
            # Client IsSwitchActive: absent/zero tempDatas[id] means enabled.
            value = 0 if season_temp_datas is None else season_temp_datas.get(str(identifier), season_temp_datas.get(identifier, 0))
            if type(value) is not int:
                raise ValueError('Season switch value must be an integer')
            if value != 0 and identifier not in state['disabled_season_ids']:
                state['disabled_season_ids'].append(identifier)
            state[marker] = True
        return initialize_death_fates(result, talent_counters=talent_counters, newly_acquired_fates=newly_acquired_fates)

    @staticmethod
    def _guard_remaining_from_raw(counters):
        if counters is None:
            raise UnknownEffectState('Import talentTempDatas or explicitly initialize a newly acquired talent 105')
        # ShowDeathDamage requires ContainsKey(105) AND value > 0. An explicitly
        # supplied empty snapshot therefore means unavailable, not one free use.
        value = counters.get('105', counters.get(105, 0))
        if type(value) is not int:
            raise ValueError('Raw talent 105 counter must be an integer')
        return int(value > 0)

    def set_season_enabled(self, player, strategy_id, enabled):
        if type(strategy_id) is not int or strategy_id not in TOGGLEABLE_SEASON_IDS or type(enabled) is not bool:
            raise ValueError('Only registered season switches are implemented')
        result = _copy(player)
        if strategy_id not in _ids(result, 'season_choices'):
            raise ValueError('Cannot toggle an unowned season effect')
        state = result['effect_state']
        disabled = set(state['disabled_season_ids'])
        disabled.discard(strategy_id) if enabled else disabled.add(strategy_id)
        state['disabled_season_ids'] = sorted(disabled)
        state[f'season_{strategy_id}_initialized'] = True
        return result

    def battle_start(self, left, right):
        """Apply start hooks to temporary combat-state copies, never match HP/Qi."""
        players = [self.initialize_player(left), self.initialize_player(right)]
        if any(player['effect_state'].get(INHERITANCE_PENDING) for player in players):
            raise UnknownEffectState('Resolve pending Dragon Inheritance draws before another battle')
        if any(player['effect_state'].get(DRAGON_SCALE_PENDING) for player in players):
            raise UnknownEffectState('Resolve pending Dragon Scale upgrade before another battle')
        if any(player['effect_state'].get('death_fate_pending') for player in players):
            raise UnknownDeathFateState('Resolve pending death-fate rewards before another battle')
        for player in players:
            player['qi'] = _integer(player.get('qi', 0), 'qi')
        result = apply_season_start(players, [_ids(player,'season_choices') for player in players], parameters=self.season_parameters)
        return {'players': result['players'], 'events': result['events'],
                'unsupported_effects': [self.coverage(player) for player in players],
                'complete_rule_execution': False}

    def settle(self, winner, loser, base_damage, *, draw_five_elements=None):
        """Apply the supported effects' relative order; caller deducts life.

        CalLifeDamage applies winner's 2011. ShowDeathDamage then applies
        loser's 27 cap, 45, then 105. Other intervening effects (e.g. 慈念曲)
        remain unsupported, so this is never a full-rule claim. Fate 27's
        post-battle upgrade remains unsupported, and 27 is NOT admitted to
        SUPPORTED_FATES. Offline actors default to non-mirrors; replay callers
        must supply their observed is_mirror flag explicitly.
        """
        damage = _integer(base_damage, 'base_damage')
        winning = self.initialize_player(winner)
        losing = self.initialize_player(loser)
        if any(player['effect_state'].get(INHERITANCE_PENDING) for player in (winning, losing)):
            raise UnknownEffectState('Resolve pending Dragon Inheritance draws before another settlement')
        if any(player['effect_state'].get(DRAGON_SCALE_PENDING) for player in (winning, losing)):
            raise UnknownEffectState('Resolve pending Dragon Scale upgrade before another settlement')
        if any(player['effect_state'].get('death_fate_pending') for player in (winning,losing)):
            raise UnknownDeathFateState('Resolve pending death-fate rewards before another settlement')
        winner_season = _ids(winning, 'season_choices')
        loser_fates = _ids(losing, 'fates')
        events = []
        if 2011 in winner_season:
            before = damage
            damage = max(1, damage - self.kindness_reduction)
            events.append({'phase': 'destiny_damage', 'effect_id': 2011,
                           'damage_before': before, 'damage_after': damage})
        if 27 in loser_fates:
            before = damage
            damage = cap_damage(damage, life_before_battle=losing.get('life'),
                                is_mirror=losing.get('is_mirror', False), limit=self.dragon_scale_limit)
            if damage != before:
                events.append({'phase': 'destiny_damage', 'effect_id': 27,
                               'component': 'damage_cap', 'damage_before': before, 'damage_after': damage})
        if 45 in loser_fates and damage > 0 and damage % 2 == 0:
            before = damage
            damage //= 2
            events.append({'phase': 'destiny_damage', 'effect_id': 45,
                           'damage_before': before, 'damage_after': damage})
        if (105 in loser_fates and losing['effect_state']['talent_105_remaining'] > 0
                and damage >= self.guard_threshold):
            before = damage
            damage = 0
            losing['effect_state']['talent_105_remaining'] = 0
            events.append({'phase': 'destiny_damage', 'effect_id': 105,
                           'damage_before': before, 'damage_after': damage,
                           'remaining_uses_before': 1, 'remaining_uses_after': 0})
        pending = []
        if loser_fates & DEATH_FATES:
            prevention = apply_death_prevention(losing, damage, draw_five_elements=draw_five_elements)
            losing, damage = prevention['player'], prevention['life_damage']
            events.extend(prevention['events'])
            pending = prevention['pending_actions']
        if 2011 in winner_season:
            # Victory grants this even when the loser's guard absorbs all damage.
            # Tips_9 permits temporary overflow; the match's next battle-start
            # resource cleanup handles the storage cap, not this win effect.
            if 'rerolls' not in winning:
                raise UnknownEffectState('Winner rerolls are required to apply season 2011')
            before = _integer(winning['rerolls'], 'rerolls')
            winning['rerolls'] = before + 1
            events.append({'phase': 'battle_win', 'effect_id': 2011,
                           'rerolls_before': before, 'rerolls_after': before+1,
                           'source': 'local_effect_description',
                           'exact_server_accounting_timing_verified': False})
        return {'winner': winning, 'loser': losing, 'life_damage': damage, 'events': events,
                'pending_actions': pending, 'complete_resolution': not pending,
                'unsupported_effects': {'winner': self.coverage(winning), 'loser': self.coverage(losing)},
                'complete_rule_execution': False}
