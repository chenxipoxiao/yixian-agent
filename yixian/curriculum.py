"""Explicitly synthetic fixed-battle curriculum, never labelled live-game data."""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random
from .research import canonical_json

CARDS = [f'111{i:02d}1' for i in range(1, 13)]


def make_cases(count=72, seed=7311):
    """Create distinct fixture families. These are not samples of online matchmaking."""
    if type(count) is not int or not 3 <= count <= 10000:
        raise ValueError('case count must be between 3 and 10000')
    rng = random.Random(seed)
    cases = []
    seen = set()
    while len(cases) < count:
        own = rng.choices(CARDS, k=8)
        other = rng.choices(CARDS, k=8)
        family = hashlib.sha256(canonical_json([sorted(own), sorted(other)]).encode()).hexdigest()[:16]
        if family in seen:
            continue
        seen.add(family)
        hp = rng.choice([32, 40, 48, 56])
        battle = {
            'seed': seed + len(cases), 'max_turns': 96, 'first_player': rng.randrange(2),
            'include_log': False,
            'players': [
                {'character': 'sw1', 'hp': hp, 'max_hp': hp, 'cultivation': 10,
                 'round_number': 1, 'destiny': 100, 'cards': own},
                {'character': 'sw2', 'hp': hp, 'max_hp': hp, 'cultivation': 9,
                 'round_number': 1, 'destiny': 100, 'cards': other},
            ],
        }
        cases.append({'id': f'curriculum-{family}', 'battle': battle,
                      'source': {'game_id': f'synthetic-{family}', 'evidence': 'synthetic',
                                 'artifact': f'curriculum-generator-v1:{seed}'}})
    return cases


def split_cases(cases):
    """Group all variants of a source game before a deterministic 60/20/20 split."""
    groups = {}
    for case in cases:
        source = case.get('source', {})
        game_id = source.get('game_id')
        if not isinstance(game_id, str) or not game_id:
            raise ValueError('every case requires source.game_id')
        groups.setdefault(game_id, []).append(deepcopy(case))
    if len(groups) < 5:
        raise ValueError('at least five distinct source games required')
    keys = sorted(groups, key=lambda key: hashlib.sha256(key.encode()).digest())
    end_train = max(1, int(len(keys) * .6))
    end_valid = min(len(keys)-1, max(end_train+1, int(len(keys) * .8)))
    chunks = {'train': keys[:end_train], 'validation': keys[end_train:end_valid], 'test': keys[end_valid:]}
    return {name: [row for key in ids for row in groups[key]] for name, ids in chunks.items()}


def fingerprint(cases):
    return hashlib.sha256(canonical_json(cases).encode('utf-8')).hexdigest()


def write_cases(path: Path, cases):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding='utf-8')
