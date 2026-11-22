"""Strict development-only corpus loading for S1 multi-seed training."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .order_data import CHARACTER, SCOPE, SPLIT_SALT, VERSION, validate_splits

DEVELOPMENT_ROLES = ('train', 'validation')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_development_corpus(directory, *, expected_manifest_sha256):
    """Never open test.jsonl, even for checksums, during development training."""
    directory = Path(directory)
    manifest_path = directory/'manifest.json'
    if sha(manifest_path) != expected_manifest_sha256:
        raise ValueError('Pinned corpus manifest hash mismatch')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    required = {'scope': SCOPE, 'rules_version': VERSION, 'character_id': CHARACTER,
                'season_mec': 10, 'split_salt': SPLIT_SALT}
    if any(manifest.get(key) != value for key, value in required.items()):
        raise ValueError('Unsupported corpus scope, character, split or rules version')
    vocabulary = manifest['vocabulary']
    if not vocabulary or any(type(card) is not int or card <= 0 for card in vocabulary) or len(set(vocabulary)) != len(vocabulary):
        raise ValueError('Invalid vocabulary')
    mapping = {card: index+1 for index, card in enumerate(vocabulary)}
    records, boards = {}, {}
    for split in DEVELOPMENT_ROLES:
        path = directory/f'{split}.jsonl'
        if sha(path) != manifest['split_sha256'][split]:
            raise ValueError(f'{split} data hash mismatch')
        with path.open(encoding='utf-8') as stream:
            rows = [json.loads(line) for line in stream]
        if not rows or any(row['split'] != split for row in rows):
            raise ValueError('Missing or incorrectly partitioned development rows')
        for row in rows:
            board = row['board']
            if not isinstance(board, list) or not 3 <= len(board) <= 8 or len(set(board)) < 2:
                raise ValueError('Uninformative or malformed board')
            if any(type(card) is not int or card not in mapping for card in board):
                raise ValueError('Unknown card in board')
            identity = hashlib.sha256(json.dumps([row['game_id'], board], separators=(',', ':')).encode()).hexdigest()
            if row['id'] != identity or row.get('season_mec') != 10:
                raise ValueError('Board identity or season mismatch')
        records[split] = rows
        boards[split] = [[mapping[card] for card in row['board']] for row in rows]
    summary = validate_splits(records['train']+records['validation'])
    for dimension in ('boards', 'games'):
        for split in DEVELOPMENT_ROLES:
            if summary[dimension][split] != manifest['split_summary'][dimension][split]:
                raise ValueError('Development counts disagree with manifest')
    return manifest, records, boards


def validate_development_config(config):
    if config.get('scope') != SCOPE or config.get('full_match_training') is not False:
        raise ValueError('Unsupported training scope')
    if config.get('evaluation_roles') != list(DEVELOPMENT_ROLES) or config.get('test_evaluation_enabled') is not False:
        raise ValueError('This entrypoint supports only training and validation')
    settings = config['train']
    seeds = [settings[key] for key in ('seed', 'validation_seed', 'bootstrap_seed')]
    if len(set(seeds)) != len(seeds) or any(type(seed) is not int or seed < 0 for seed in seeds):
        raise ValueError('Development random streams must use distinct nonnegative seeds')
    if 'test_seed' in settings:
        raise ValueError('Final-test random streams do not belong to development config')
    if not 0 < settings['max_minutes'] <= 120:
        raise ValueError('Training job must have a positive runtime limit at most two hours')
    for key in ('batch_size', 'max_updates', 'validation_interval', 'early_stopping_patience',
                'evaluation_batch_size', 'cpu_threads', 'bootstrap_samples'):
        if type(settings[key]) is not int or settings[key] < 1:
            raise ValueError(f'{key} must be a positive integer')
    if config.get('selection_metric') != 'validation_teacher_nll':
        raise ValueError('Checkpoint selection must use the preregistered validation metric')
