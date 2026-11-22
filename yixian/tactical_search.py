"""Character-agnostic numerical lineup search against a fixed information set.

One board is selected for ALL possible hidden states. Incomplete scenarios are
never dropped and renormalized to make a candidate look better. The evaluator
owns rules/fate/initiative execution; this module supplies none of those rules.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Scenario:
    key: str
    probability: float
    payload: dict
    information_digest: str
    rules_fingerprint: str
    provenance: str  # hypothesis, declared_prior, or software_fixture


def unique_orders(cards, limit):
    if not 1 <= len(cards) <= 8 or type(limit) is not int or limit < 1:
        raise ValueError('Require 1..8 cards and positive order budget')
    counts = Counter(cards)
    emitted = 0
    def visit(prefix):
        nonlocal emitted
        if emitted >= limit:
            return
        if len(prefix) == len(cards):
            emitted += 1
            yield tuple(prefix)
            return
        for card in sorted(counts):
            if counts[card]:
                counts[card] -= 1
                yield from visit(prefix+[card])
                counts[card] += 1
    return visit([])


def lower_tail(values, probabilities, fraction):
    remaining, total = fraction, 0.
    for value, probability in sorted(zip(values, probabilities)):
        amount = min(remaining, probability)
        total += amount * value
        remaining -= amount
        if remaining <= 1e-12:
            break
    return total / fraction


def search_lineups(view, cards, proposals, scenarios, evaluator, *, max_evaluations=512,
                   risk_weight=0., tail_fraction=.25):
    if not scenarios or len({s.key for s in scenarios}) != len(scenarios):
        raise ValueError('Distinct opponent hypotheses required')
    if not 0 <= risk_weight <= 1 or not 0 < tail_fraction <= 1 or max_evaluations < len(scenarios):
        raise ValueError('Invalid risk or evaluation budget')
    for scenario in scenarios:
        if (not math.isfinite(scenario.probability) or scenario.probability <= 0
                or scenario.information_digest != view['digest']
                or scenario.rules_fingerprint != view['rules_fingerprint']
                or scenario.provenance not in ('hypothesis', 'declared_prior', 'software_fixture')):
            raise ValueError('Invalid/foreign/stale hypothesis; actual hidden state is not a prior')
    if not math.isclose(sum(s.probability for s in scenarios), 1., abs_tol=1e-8):
        raise ValueError('Hypothesis probabilities must sum to one')
    base = Counter(cards)
    if not 1 <= len(cards) <= 8:
        raise ValueError('Require explicit 1..8-card multiset')
    seen, rows, evaluations, clipped = set(), [], 0, False
    for proposal in proposals:
        board = tuple(proposal)
        if Counter(board) != base:
            raise ValueError('Proposal changed owned multiset; hand selection requires a separate legal action')
        if board in seen:
            continue
        if evaluations + len(scenarios) > max_evaluations:
            clipped = True
            break
        seen.add(board)
        values, reasons = [], []
        for scenario in scenarios:
            outcome = evaluator(board, deepcopy(scenario.payload))
            evaluations += 1
            if (outcome.get('rules_fingerprint') != view['rules_fingerprint']
                    or outcome.get('terminated') is not True or outcome.get('truncated') is not False
                    or outcome.get('resolved') is not True
                    or not isinstance(outcome.get('utility'), (float, int))
                    or not math.isfinite(outcome['utility'])):
                reasons.append(scenario.key)
            else:
                values.append(float(outcome['utility']))
        if reasons:
            rows.append({'board': list(board), 'eligible': False, 'unresolved_scenarios': reasons})
            continue
        probabilities = [s.probability for s in scenarios]
        mean = sum(p*v for p, v in zip(probabilities, values))
        tail = lower_tail(values, probabilities, tail_fraction)
        rows.append({'board': list(board), 'eligible': True, 'expected_utility': mean,
                     'lower_tail_utility': tail, 'worst_utility': min(values),
                     'objective': (1-risk_weight)*mean + risk_weight*tail})
    valid = [row for row in rows if row['eligible']]
    best = max(valid, key=lambda r: r['objective']) if valid else None
    return {'selected_board': best['board'] if best else None, 'candidates': rows,
            'evaluations': evaluations, 'budget_exhausted': clipped,
            'optimality_scope': 'evaluated_proposals_and_declared_hypotheses_only',
            'belief_calibrated': False, 'game_strength_evaluated': False,
            'training_label_allowed': False, 'full_match_training': False}
