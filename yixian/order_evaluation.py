"""Recorded-order reproduction with teacher and independently generated prefixes.

Scorers see only candidate tokens, their own prefix and an occurrence mask.
All confidence intervals below concern game-balanced reproduction, not strength.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import math

import numpy as np

from .order_data import informative_steps, teacher_batch


def position_counts(boards, vocabulary_size):
    counts = np.ones((8, vocabulary_size), dtype=np.float64)
    for board in boards:
        for step, card in enumerate(board):
            counts[step, card] += 1
    return counts


def _choices(scorer, candidates, prefix, available):
    # Copies prevent a scorer from altering another policy's evaluation state.
    scores = np.asarray(scorer(candidates.copy(), prefix.copy(), available.copy()), dtype=np.float64)
    if scores.shape != candidates.shape or not np.isfinite(scores[available]).all():
        raise ValueError('Invalid shape or non-finite legal policy score')
    chosen = scores.argmax(axis=1)
    if not available[np.arange(len(chosen)), chosen].all():
        raise ValueError('Policy selected an unavailable occurrence')
    return scores, chosen


def frequency_scorer(counts):
    def score(candidates, prefix, available):
        steps = np.count_nonzero(prefix, axis=1)
        return np.where(available, np.log(counts[steps[:, None], candidates]), -np.inf)
    return score


def shuffled_candidates(boards, identifiers, seed):
    if len(boards) != len(identifiers) or len(set(identifiers)) != len(identifiers):
        raise ValueError('Every board needs a unique stable identifier')
    candidates = np.zeros((len(boards), 8), dtype=np.int64)
    for index, (board, identifier) in enumerate(zip(boards, identifiers)):
        if not 3 <= len(board) <= 8 or len(set(board)) < 2 or any(type(c) not in (int, np.int64) or c <= 0 for c in board):
            raise ValueError('Expected 3..8 positive vocabulary tokens')
        digest = hashlib.sha256(f'{seed}:{identifier}'.encode()).digest()
        rng = np.random.default_rng(int.from_bytes(digest[:8], 'big'))
        candidates[index, :len(board)] = rng.permutation(sorted(board))
    return candidates


def decode_own_prefix(candidates, scorer, *, batch_size=256):
    """Decode all slots, never supplying a reference-order prefix to the scorer."""
    candidates = np.asarray(candidates, dtype=np.int64)
    if batch_size < 1 or candidates.ndim != 2 or candidates.shape[1] != 8:
        raise ValueError('Expected positive batch size and eight-slot bags')
    lengths = np.count_nonzero(candidates, axis=1)
    if np.any(candidates < 0) or np.any((lengths < 3) | (lengths > 8)):
        raise ValueError('Each bag needs 3..8 positive tokens')
    output = np.zeros_like(candidates)
    for start in range(0, len(candidates), batch_size):
        bag = candidates[start:start+batch_size]
        prefix = np.zeros_like(bag)
        available = bag != 0
        for step in range(int(np.count_nonzero(bag, axis=1).max())):
            active = np.flatnonzero(available.any(axis=1))
            _, chosen = _choices(scorer, bag[active], prefix[active], available[active])
            prefix[active, step] = bag[active, chosen]
            available[active, chosen] = False
        for original, predicted in zip(bag, prefix):
            if Counter(original[original > 0]) != Counter(predicted[predicted > 0]):
                raise ValueError('Decoder changed the supplied multiset')
        output[start:start+len(bag)] = prefix
    return [row[:length].tolist() for row, length in zip(output, lengths)]


def random_order_expectations(board):
    """Uniform occurrence permutations, including repeated-card multiplicities."""
    counts = Counter(board)
    exact = math.prod(math.factorial(n) for n in counts.values()) / math.factorial(len(board))
    correct_positions = sum(counts[card] / len(board) for card in board)
    return exact, correct_positions


def _rates(totals):
    return {
        'teacher_nll': totals['nll'] / totals['decisions'],
        'teacher_next_card_accuracy': totals['correct'] / totals['decisions'],
        'own_prefix_exact_board_accuracy': totals['exact'] / totals['boards'],
        'own_prefix_position_accuracy': totals['positions_correct'] / totals['positions'],
    }


def grouped_summary(groups, *, bootstrap_seed, bootstrap_samples=2000):
    if bootstrap_samples < 1 or not groups:
        raise ValueError('Nonempty games and a positive bootstrap count are required')
    policies = ('model', 'position_frequency', 'random')
    keys = sorted(groups)
    totals = {policy: Counter() for policy in policies}
    per_game = {policy: [] for policy in policies}
    for game in keys:
        for policy in policies:
            totals[policy].update(groups[game][policy])
            per_game[policy].append(_rates(groups[game][policy]))
    metric_names = tuple(per_game['model'][0])
    arrays = {policy: np.array([[game[name] for name in metric_names] for game in per_game[policy]])
              for policy in policies}
    macro = {policy: dict(zip(metric_names, arrays[policy].mean(axis=0).tolist())) for policy in policies}
    rng = np.random.default_rng(bootstrap_seed)
    differences = {baseline: arrays['model']-arrays[baseline] for baseline in policies[1:]}
    samples = {baseline: np.empty((bootstrap_samples, len(metric_names))) for baseline in differences}
    for index in range(bootstrap_samples):
        draw = rng.integers(0, len(keys), len(keys))
        for baseline, values in differences.items():
            samples[baseline][index] = values[draw].mean(axis=0)
    intervals = {}
    for baseline, values in samples.items():
        bounds = np.quantile(values, [.025, .975], axis=0)
        intervals[baseline] = {name: {
            'model_minus_baseline': float(differences[baseline][:, col].mean()),
            'low': float(bounds[0, col]), 'high': float(bounds[1, col]),
        } for col, name in enumerate(metric_names)}
    return {'games': len(keys), 'boards': int(totals['model']['boards']),
            'informative_decisions': int(totals['model']['decisions']),
            'pooled_metrics': {policy: _rates(values) for policy, values in totals.items()},
            'game_macro_metrics': macro, 'paired_game_macro_ci95': intervals,
            'bootstrap': {'seed': bootstrap_seed, 'samples': bootstrap_samples,
                          'resampling_unit': 'whole_game', 'estimator': 'mean_of_per_game_rates'}}


def evaluate_orders(boards, game_ids, identifiers, scorer, counts, *, seed,
                    batch_size=256, bootstrap_seed, bootstrap_samples=2000):
    if not boards or len(boards) != len(game_ids) or len(boards) != len(identifiers) or batch_size < 1:
        raise ValueError('Aligned nonempty boards, groups and identifiers are required')
    if counts.ndim != 2 or counts.shape[0] != 8 or not np.isfinite(counts).all() or np.any(counts <= 0):
        raise ValueError('Position counts must be finite and positively smoothed')
    candidates = shuffled_candidates(boards, identifiers, seed)
    if candidates.max() >= counts.shape[1]:
        raise ValueError('Board token outside frequency vocabulary')
    generated = decode_own_prefix(candidates, scorer, batch_size=batch_size)
    frequency = decode_own_prefix(candidates, frequency_scorer(counts), batch_size=batch_size)
    groups = defaultdict(lambda: defaultdict(Counter))
    for board, game, predicted, baseline in zip(boards, game_ids, generated, frequency):
        for policy, output in (('model', predicted), ('position_frequency', baseline)):
            groups[game][policy].update(boards=1, positions=len(board), exact=int(board == output),
                                       positions_correct=sum(a == b for a, b in zip(board, output)))
        exact, correct = random_order_expectations(board)
        groups[game]['random'].update(boards=1, positions=len(board), exact=exact, positions_correct=correct)
    # Teacher labels are evaluator-only. All three policies share each decision.
    cases = [(index, step) for index, board in enumerate(boards) for step in informative_steps(board)]
    rng = np.random.default_rng(seed)
    for start in range(0, len(cases), batch_size):
        part = cases[start:start+batch_size]
        batch = teacher_batch([boards[i] for i, _ in part], rng, steps=[step for _, step in part])
        logits, choices = _choices(scorer, batch['candidates'], batch['prefix'], batch['available'])
        for row, (index, step) in enumerate(part):
            legal, target = batch['available'][row], batch['targets'][row]
            scores = logits[row]
            # Exclude unavailable occurrences explicitly when computing mass.
            nll = np.logaddexp.reduce(scores[legal])-np.logaddexp.reduce(scores[target])
            group = groups[game_ids[index]]
            group['model'].update(decisions=1, nll=float(nll), correct=int(target[choices[row]]))
            probability = target.sum()/legal.sum()
            group['random'].update(decisions=1, nll=-float(np.log(probability)), correct=float(probability))
            weights = counts[step, batch['candidates'][row]] * legal
            group['position_frequency'].update(decisions=1,
                nll=-float(np.log(weights[target].sum()/weights.sum())), correct=int(target[weights.argmax()]))
    result = grouped_summary(groups, bootstrap_seed=bootstrap_seed, bootstrap_samples=bootstrap_samples)
    result.update(metric_scope='recorded_order_reproduction_not_game_win_rate',
                  prefix_source='own_previous_predictions_for_full_board_metrics',
                  random_full_board_baseline='exact_expectation_over_uniform_occurrence_permutations',
                  illegal_predictions=0, multiset_violations=0, game_strength_evaluated=False,
                  full_match_training=False, per_game_metrics_available=True)
    game_metrics = {game: {policy: _rates(values) for policy, values in policies.items()}
                    for game, policies in groups.items()}
    return result, game_metrics


def torch_scorer(model, device):
    """Lazy import keeps statistical and isolation tests usable without PyTorch."""
    import torch
    model.eval()

    def score(candidates, prefix, available):
        with torch.inference_mode(), torch.autocast(device_type=device.type, dtype=torch.float16,
                                                   enabled=device.type == 'cuda'):
            tensors = [torch.as_tensor(value, device=device) for value in (candidates, prefix, available)]
            return model(*tensors).float().cpu().numpy()
    return score
