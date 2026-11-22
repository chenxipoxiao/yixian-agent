"""Auxiliary reconstruction of recorded Long Yao boards, not action-log BC.

The model sees a shuffled bag of the recorded board and its constructed prefix.
No battle result, private hand, future round, or inferred management action is an
input or label. Whole games are kept together across every replay perspective.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json

import numpy as np

CHARACTER = 1000003
VERSION = '001.0008.0005'
SCOPE = 'longyao_shuffled_recorded_board_reconstruction'
SPLIT_SALT = 'longyao-order-pretrain-v1-unseen-games'


def game_split(game_id):
    value = int(hashlib.sha256((SPLIT_SALT + ':' + game_id).encode()).hexdigest()[:8], 16) / 2**32
    return 'train' if value < .8 else 'validation' if value < .9 else 'test'


def extract_boards(record, *, allowed_cards, excluded_games=()):
    from .replays import game_key
    data = record.get('data', {})
    if data.get('seasonMec') != 10 or data.get('gameMode') != 3 or data.get('version') != VERSION:
        return []
    group = game_key(data['gameId'])
    if group in excluded_games:
        return []
    results = []
    for turn in data.get('roundStats', []):
        for slot in ('p1', 'p2'):
            public = turn.get(slot, {}).get('publicData', {})
            if public.get('characterId') != CHARACTER or public.get('isAI') is not False:
                continue
            board = public.get('lastRoundData', {}).get('usedCards')
            if not isinstance(board, list) or not 3 <= len(board) <= 8:
                continue
            if any(type(card) is not int or card <= 0 or card not in allowed_cards for card in board):
                continue
            if len(set(board)) < 2:
                continue
            # Conservative deduplication also removes unchanged boards in later
            # rounds. It does not claim to merge anonymized player identities.
            key = hashlib.sha256(json.dumps([group, board], separators=(',', ':')).encode()).hexdigest()
            results.append({'id': key, 'game_id': group, 'split': game_split(group),
                            'character_id': CHARACTER, 'board': board,
                            'first_observed_round': turn.get('round'),
                            'source_rules_version': VERSION, 'season_mec': 10,
                            'scope': SCOPE, 'recorded_action_trajectory': False})
    return results


def validate_splits(records):
    groups, ids = {}, set()
    counts = Counter()
    for row in records:
        group, split = row['game_id'], row['split']
        if split != game_split(group) or groups.setdefault(group, split) != split:
            raise ValueError('Whole-game split mismatch')
        if row['id'] in ids:
            raise ValueError('Duplicate board record')
        ids.add(row['id'])
        if row.get('scope') != SCOPE or row.get('recorded_action_trajectory') is not False:
            raise ValueError('Unsupported training-data scope')
        if row.get('character_id') != CHARACTER or row.get('source_rules_version') != VERSION:
            raise ValueError('Character or version mismatch')
        counts[split] += 1
    return {'boards': dict(counts), 'games': dict(Counter(groups.values()))}


def informative_steps(board):
    return [step for step in range(len(board) - 1) if len(set(board[step:])) > 1]


def teacher_batch(boards, rng, *, steps=None):
    """Duplicate cards are interchangeable pointer targets; pad token is zero."""
    size = len(boards)
    candidates = np.zeros((size, 8), dtype=np.int64)
    prefix = np.zeros_like(candidates)
    available = np.zeros((size, 8), dtype=bool)
    targets = np.zeros_like(available)
    for index, source in enumerate(boards):
        board = list(source)
        if not 3 <= len(board) <= 8 or any(type(card) not in (int, np.int64) or card <= 0 for card in board):
            raise ValueError('A board needs 3..8 positive vocabulary IDs')
        choices = informative_steps(board)
        if not choices:
            raise ValueError('No informative ordering decision')
        step = int(rng.choice(choices)) if steps is None else int(steps[index])
        if step not in choices:
            raise ValueError('Invalid or deterministic teacher step')
        candidates[index, :len(board)] = rng.permutation(board)
        available[index, :len(board)] = True
        prefix[index, :step] = board[:step]
        for card in board[:step]:
            match = np.flatnonzero(available[index] & (candidates[index] == card))[0]
            available[index, match] = False
        targets[index] = available[index] & (candidates[index] == board[step])
    return {'candidates': candidates, 'prefix': prefix, 'available': available, 'targets': targets}
