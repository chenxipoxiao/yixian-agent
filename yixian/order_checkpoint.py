"""Contract-checked loading for the development-only v2 order checkpoint."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .order_data import SCOPE
from .pretrain_protocol import sha, validate_development_config
from .research import contract_digest

TRAINING_SOURCES = ('yixian/order_data.py', 'yixian/order_model.py', 'yixian/order_evaluation.py',
                    'yixian/pretrain_protocol.py', 'tools/train_longyao_development.py')


def load_order_checkpoint(path, *, root, expected_sha256, device='cpu', expected_config=None,
                          expected_manifest_sha256=None):
    import torch
    from .order_model import BoardOrderPolicy
    if sha(path) != expected_sha256:
        raise ValueError('Checkpoint file hash mismatch')
    packet = torch.load(path, map_location='cpu', weights_only=True)
    contract, config, vocabulary = packet['contract'], packet['config'], packet['vocabulary']
    if contract.get('schema_version') != 2 or contract.get('scope') != SCOPE or packet['contract_digest'] != contract_digest(contract):
        raise ValueError('Unsupported or damaged v2 checkpoint contract')
    validate_development_config(config)
    if expected_config is not None and config != expected_config:
        raise ValueError('Checkpoint configuration differs from frozen selection')
    if expected_manifest_sha256 is not None and contract['dataset_manifest_sha256'] != expected_manifest_sha256:
        raise ValueError('Checkpoint dataset differs from frozen selection')
    if set(contract['source_sha256']) != set(TRAINING_SOURCES):
        raise ValueError('Unexpected training source contract')
    for name in TRAINING_SOURCES:
        if sha(Path(root)/name) != contract['source_sha256'][name]:
            raise ValueError(f'Checkpoint source contract mismatch: {name}')
    digest = hashlib.sha256(json.dumps(vocabulary).encode()).hexdigest()
    if digest != contract['vocabulary_sha256'] or config['model'] != contract['model']:
        raise ValueError('Vocabulary or model architecture contract mismatch')
    if contract.get('test_data_opened') is not False or set(contract['split_sha256']) != {'train', 'validation'}:
        raise ValueError('Checkpoint is not from a development-only run')
    model = BoardOrderPolicy(len(vocabulary)+1, **contract['model']).to(device).eval()
    model.load_state_dict(packet['model'])
    return model, {'vocabulary': vocabulary, 'config': config, 'contract': contract,
                   'contract_digest': packet['contract_digest'], 'step': packet['step']}
