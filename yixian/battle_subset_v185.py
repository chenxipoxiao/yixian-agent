"""Restricted, one-battle training contract; no replay continuation or S2 promotion.

Policy inputs are an owned card multiset. Opponent scripts receive their own
multiset and a strictly earlier public board, never the learner's new order.
Counterfactual rewards are new simulator outputs, not recorded outcome labels.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
import random

SCOPE = 'longyao_verified_subset_battle_order_v185'
BASE_FIELDS = {'players', 'first_player', 'seed', 'max_turns', 'include_trace', 'current_rules_context'}
EXCLUDED_PLAYER_FIELDS = {'five_elements_pure_vase_cards', 'swordplay_talent_cards'}
SEARCH_SEED = 2026111801


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def split_game(game_id):
    return 'validation' if int(digest(['v185-reward-development-split', game_id])[:8], 16) % 5 == 0 else 'train'


def policy_observation(row):
    # Deliberately narrower than full tactical information. Reward/oracle state
    # and all opponent private fields are inaccessible to the model.
    return {'owned_cards': sorted(row['raw_cards'][row['learner']])}


def priority(card, catalogue, pressure, style):
    c = catalogue[card]
    qi = float(c.get('chargeQi', 0))
    cost = max(0, float(c.get('anima', 0)))
    defense = float(c.get('def', 0))
    attack = float(c.get('attack', 0)) * max(1, float(c.get('attackCount', 0)))
    # Fixed numerical baseline, not a claimed learned all-character opponent.
    weights = ((4., 1.6, 1.), (3., .7, 1.8), (5., 2.5, .5))[style]
    return -(weights[0]*qi - 2.*cost + weights[1]*pressure*defense + weights[2]*attack), card


def reactive_orders(own_cards, history, round_number, catalogue):
    if history is not None:
        if type(history['round']) is not int or history['round'] >= round_number:
            raise ValueError('Unrevealed current/future opponent order')
        past = [catalogue[c] for c in history['board']]
        pressure = min(2., sum(max(0, c.get('attack', 0))*max(1, c.get('attackCount', 0))
                              for c in past)/max(1, len(past))/5.)
    else:
        pressure = 1.  # Predeclared no-observation script, not imputed history.
    return [sorted(own_cards, key=lambda c: priority(c, catalogue, pressure, style)) for style in range(3)]


def candidate_orders(cards, catalogue, count=12):
    if not 3 <= len(cards) <= 8 or len(set(cards)) < 2:
        raise ValueError('Require informative 3..8-card multiset')
    bag = sorted(cards)
    rng = random.Random(int(digest([SEARCH_SEED, bag])[:16], 16))
    initial = [bag, list(reversed(bag))] + reactive_orders(bag, None, 1, catalogue)
    result = []
    for order in initial:
        if order not in result:
            result.append(order)
    for _ in range(1000):
        order = rng.sample(bag, len(bag))
        if order not in result:
            result.append(order)
        if len(result) >= count:
            break
    # No recorded order or outcome enters this candidate generator.
    return result[:count]


def admission_reason(case):
    if not case['all_four_match']:
        return 'recorded_terminal_disagreement'
    if case['initiative']['candidate_first_index'] is None:
        return 'recorded_first_tie_conditioned'
    if case['simulation'].get('used_randomness') is not False:
        return 'runtime_randomness'
    battle = case['compiled']['battle']
    if set(battle) - BASE_FIELDS:
        return 'special_context_or_record_parameter_not_admitted'
    if any(EXCLUDED_PLAYER_FIELDS & set(p) for p in battle['players']):
        return 'hidden_history_or_vase_not_admitted'
    if not any(p['character'] == 'sw3' for p in battle['players']):
        return 'no_longyao'
    if any(any(v is None for v in p.values()) for p in battle['players']):
        return 'unknown_start_value'
    if case['compiled'].get('initiative_source') != 'independent_start_speed_comparison':
        return 'initiative_not_independent'
    return None


def mapped_order(row, seat, raw_order):
    if Counter(raw_order) != Counter(row['raw_cards'][seat]):
        raise ValueError('Changed owned multiset')
    mapping = dict(zip(row['raw_cards'][seat], row['battle']['players'][seat]['cards'], strict=True))
    if any(mapping[a] != b for a,b in zip(row['raw_cards'][seat], row['battle']['players'][seat]['cards'])):
        raise ValueError('Ambiguous runtime identity')
    return [mapping[c] for c in raw_order]


def battle_input(row, learner_order, opponent_order):
    if set(row['battle']) - BASE_FIELDS:
        raise ValueError('Counterfactual requires versioned simple-input whitelist')
    battle = deepcopy(row['battle'])
    seat = row['learner']
    battle['players'][seat]['cards'] = mapped_order(row, seat, learner_order)
    battle['players'][1-seat]['cards'] = mapped_order(row, 1-seat, opponent_order)
    battle['include_trace'] = False
    battle['seed'] = 'v185-counterfactual-fixed'  # Random use rejects; never seed-search.
    return battle


def utility(result, learner):
    if (result.get('unresolved') or result.get('truncated') or not result.get('terminated')
            or result.get('used_randomness') is not False):
        raise ValueError('Unresolved, truncated or stochastic battle has no reward')
    win = 1. if result['winner'] == learner else -1.
    margin = result['hp_delta'] * (1 if learner == 0 else -1)
    return win + .1*math.tanh(margin/50.)


def summarize_matrix(results, rows, candidate_count):
    expected = candidate_count * 3
    if len(results) != expected:
        raise ValueError('Incomplete fixed opponent panel')
    values = [utility(r, rows['learner']) for r in results]
    matrix = [values[i:i+3] for i in range(0, expected, 3)]
    # Same complete opponent panel for every candidate; never best per opponent.
    return matrix, [sum(v)/3 for v in matrix]
