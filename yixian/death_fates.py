"""Four one-use death protections on explicit, copied offline match state.

The caller passes destiny damage *after* other damage modifiers and immunity,
then deducts the returned ``life_damage`` exactly once. ``life`` must reflect
any destiny changes during combat. The function does not set life to one itself.
Description-derived rewards are separate from a server-calibrated draw model.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
from pathlib import Path

from .research import canonical_json


DEATH_FATES = frozenset({7, 65, 83, 154})
IMPLEMENTED_DEATH_FATES = DEATH_FATES
FIVE_ELEMENTS = ('wood', 'fire', 'earth', 'metal', 'water')
REWARD_CARD_65 = 12  # Raw local CardConfig ID: 飞鸿踏雪, not 燕舞.


class UnknownDeathFateState(ValueError):
    """Required counter or match resource has not been supplied."""


class AmbiguousDeathFateOrder(ValueError):
    """Client display overwrite order does not prove server consumption order."""


def _integer(value, label, minimum=0):
    if type(value) is not int or minimum is not None and value < minimum:
        suffix = '' if minimum is None else f' >= {minimum}'
        raise ValueError(f'{label} must be an integer{suffix}')
    return value


def _copy(player):
    if not isinstance(player, Mapping):
        raise ValueError('Player state must be a mapping')
    canonical_json(player)
    result = deepcopy(dict(player))
    fates = result.get('fates', [])
    if not isinstance(fates, list):
        raise ValueError('fates must be a list')
    if any(not ((type(x) is int and x > 0) or (isinstance(x, str) and x)) for x in fates):
        raise ValueError('Invalid fate id')
    state = result.setdefault('effect_state', {'schema_version': 1})
    if not isinstance(state, dict) or type(state.get('schema_version')) is not int or state['schema_version'] != 1:
        raise ValueError('Unknown effect-state schema')
    ledger = state.setdefault('death_fate_remaining', {})
    if (not isinstance(ledger, dict) or any(str(k) not in {str(x) for x in DEATH_FATES}
            or type(v) is not int or v not in (0, 1) for k, v in ledger.items())):
        raise ValueError('Death-fate ledger must map supported string ids to 0 or 1')
    # A single canonical key avoids disagreement between JSON and in-memory IDs.
    if any(type(k) is not str for k in ledger):
        raise ValueError('Death-fate ledger keys must be strings')
    pending = state.setdefault('death_fate_pending', [])
    if not isinstance(pending, list) or len(pending) > 1:
        raise ValueError('Invalid death-fate pending actions')
    if pending and pending[0] != _draw_request():
        raise ValueError('Unknown death-fate pending action')
    return result


def initialize_death_fates(player, *, talent_counters=None, newly_acquired_fates=()):
    """Import counters once. Existing simulation counters always take priority.

    An explicit empty raw snapshot means no charge (ContainsKey && value > 0
    in ShowDeathDamage); an absent snapshot is unknown, never a fresh charge.
    """
    result = _copy(player)
    fates = set(result.get('fates', []))
    if isinstance(newly_acquired_fates, (str, bytes)):
        raise ValueError('newly_acquired_fates must contain integer ids')
    try:
        fresh = tuple(newly_acquired_fates)
    except TypeError as error:
        raise ValueError('newly_acquired_fates must contain integer ids') from error
    if any(type(x) is not int or x not in fates for x in fresh):
        raise ValueError('Newly acquired fates must be owned integer ids')
    if talent_counters is not None and not isinstance(talent_counters, Mapping):
        raise ValueError('talent_counters must be a mapping')
    ledger = result['effect_state']['death_fate_remaining']
    for fate in sorted(fates & DEATH_FATES):
        key = str(fate)
        if key in ledger:
            continue
        if fate in fresh:
            ledger[key] = 1
        elif talent_counters is None:
            raise UnknownDeathFateState(f'Import talentTempDatas or explicitly acquire fate {fate}')
        else:
            value = talent_counters.get(key, talent_counters.get(fate, 0))
            if type(value) is not int:
                raise ValueError(f'Raw talent {fate} counter must be an integer')
            ledger[key] = int(value > 0)
    return result


def _resource(player, name, minimum=0):
    if name not in player:
        raise UnknownDeathFateState(f'{name} is required for this death-fate reward')
    return _integer(player[name], name, minimum)


def _hand(player):
    hand = player.get('hand_cards')
    if not isinstance(hand, list) or any(type(x) is not int or x <= 0 for x in hand):
        raise UnknownDeathFateState('hand_cards must contain explicit positive raw CardConfig ids')
    return hand


def _draw_request():
    return {'kind': 'draw_distinct_five_elements', 'effect_id': 83, 'count': 5,
            'elements': list(FIVE_ELEMENTS), 'minimum_realm': 4,
            'card_id_space': 'raw_local_CardConfig'}


def _draw_cards(callback, request):
    """A supplied pool/sampler must return IDs with checked card metadata.

    No uniform or other server sampling distribution is inferred here. The
    provider owns its pool, randomness and source verification. Metadata uses
    ``realm`` for cultivation tier, not a card's upgrade level.
    """
    cards = callback(deepcopy(request))
    if not isinstance(cards, (list, tuple)) or len(cards) != 5:
        raise ValueError('Five-element provider must return exactly five card records')
    ids, elements = [], []
    for card in cards:
        if not isinstance(card, Mapping):
            raise ValueError('Draw provider needs card_id, element and realm metadata')
        ids.append(_integer(card.get('card_id'), 'drawn card_id', 1))
        element = card.get('element')
        if element not in FIVE_ELEMENTS:
            raise ValueError('Drawn card element must be one of the five elements')
        elements.append(element)
        _integer(card.get('realm'), 'drawn card realm', 4)
    if len(set(ids)) != 5 or set(elements) != set(FIVE_ELEMENTS):
        raise ValueError('Drawn cards must cover each of five different elements once')
    return ids


def _result(player, damage, events):
    pending = deepcopy(player['effect_state']['death_fate_pending'])
    return {'player': player, 'life_damage': damage, 'events': events,
            'pending_actions': pending,
            'unsupported': ['fate_83_server_draw_distribution'] if pending else [],
            'complete_resolution': not pending, 'complete_rule_execution': False}


def apply_death_prevention(player, incoming_damage, *, talent_counters=None,
                          newly_acquired_fates=(), draw_five_elements=None):
    """Apply at most one eligible protection; never revive an already dead player.

    Unresolved card generation is returned and persisted explicitly. A caller
    must resolve it before allowing the match to progress. Multiple eligible
    protections are rejected because client UI order alone is not authoritative.
    """
    damage = _integer(incoming_damage, 'incoming_damage')
    result = initialize_death_fates(player, talent_counters=talent_counters,
                                    newly_acquired_fates=newly_acquired_fates)
    life = _resource(result, 'life', 1)
    state = result['effect_state']
    if state['death_fate_pending']:
        raise UnknownDeathFateState('Resolve pending death-fate card generation before another settlement')
    if damage < life:
        return _result(result, damage, [])
    eligible = sorted(f for f in set(result.get('fates', [])) & DEATH_FATES
                      if state['death_fate_remaining'][str(f)] > 0)
    if len(eligible) > 1:
        raise AmbiguousDeathFateOrder(f'Unverified simultaneous death-protection order: {eligible}')
    if not eligible:
        return _result(result, damage, [])
    fate = eligible[0]
    event = {'phase': 'death_prevention', 'effect_id': fate,
             'damage_before': damage, 'damage_after': life - 1,
             'remaining_uses_before': 1, 'remaining_uses_after': 0,
             'source': 'local_2026_11_06_descriptions_and_replay_counter_deltas'}
    if fate == 7:
        before = _resource(result, 'rerolls')
        result['rerolls'] = before + 5
        event.update(rerolls_before=before, rerolls_after=before + 5)
    elif fate == 65:
        before = _resource(result, 'exp', 1)
        _hand(result).append(REWARD_CARD_65)
        result['exp'] = before - 1
        event.update(exp_before=before, exp_after=before - 1, cards_added=[REWARD_CARD_65])
    elif fate == 83:
        # A replay AI trigger retained destiny but paid no cost/drew no cards;
        # that branch is not calibrated. Do not fabricate the human reward.
        if result.get('is_ai') is True:
            raise UnknownDeathFateState('Fate 83 AI reward behavior is not calibrated')
        before = _resource(result, 'exp', 5)
        hand = _hand(result)
        result['exp'] = before - 5
        request = _draw_request()
        if draw_five_elements is None:
            state['death_fate_pending'].append(request)
            event['cards_pending'] = True
        else:
            cards = _draw_cards(draw_five_elements, request)
            hand.extend(cards)
            event['cards_added'] = cards
            event['draw_provider'] = 'explicit_external_provider_not_server_validated'
        event.update(exp_before=before, exp_after=before - 5)
    elif fate == 154:
        for field in ('max_hp', 'extra_max_hp', 'max_physique'):
            # Extra maximum HP is a signed modifier, unlike the resulting cap.
            before = _resource(result, field, None if field == 'extra_max_hp' else 0)
            result[field] = before + 4
            event[field + '_before'] = before
            event[field + '_after'] = before + 4
    state['death_fate_remaining'][str(fate)] = 0
    return _result(result, life - 1, [event])


def resolve_pending_death_fates(player, *, draw_five_elements):
    """Finish a pending fate 83 draw without charging cultivation/counter again."""
    result = _copy(player)
    pending = result['effect_state']['death_fate_pending']
    if not pending:
        return _result(result, None, [])
    if result['effect_state']['death_fate_remaining'].get('83') != 0:
        raise UnknownDeathFateState('Pending fate 83 draw needs its already-consumed counter')
    cards = _draw_cards(draw_five_elements, pending[0])
    _hand(result).extend(cards)
    pending.clear()
    return _result(result, None, [{'phase': 'death_prevention_reward', 'effect_id': 83,
                                 'cards_added': cards,
                                 'draw_provider': 'explicit_external_provider_not_server_validated'}])


def contract():
    return {'schema_version': 1, 'supported_death_fates': sorted(DEATH_FATES),
            'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'parameters': {'7_rerolls': 5, '65_exp_cost': 1, '65_raw_card': 12,
                           '83_exp_cost': 5, '83_card_count': 5, '83_minimum_realm': 4,
                           '154_max_hp_and_physique_bonus': 4},
            'source_snapshot': 'data/local/2026-11-06',
            'evidence': 'data/inspection/death-damage-full-il.json',
            'requires_post_combat_destiny': True,
            'multiple_simultaneous_protections_supported': False,
            'server_draw_distribution_verified': False,
            'complete_current_season_rules': False}
