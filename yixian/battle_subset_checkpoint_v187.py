"""Explicit loader for the restricted battle-reward proposal checkpoint.

The older v3 loader must continue to reject this different training contract.
Loading requires the original frozen release and its independently checked hash.
"""
from collections import Counter
from pathlib import Path
import hashlib
import json

from .battle_subset_v187 import SCOPE, candidate_orders, digest
from .tactical_checkpoint import load_tactical_checkpoint
from .tactical_rules import TacticalCatalogue


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_verified_subset_checkpoint(path, *, root, expected_sha256, device='cpu'):
    import torch
    root = Path(root).resolve()
    if sha(path) != expected_sha256:
        raise ValueError('Restricted checkpoint hash mismatch')
    packet = torch.load(path, map_location='cpu', weights_only=True)
    contract = packet['contract']
    if (contract.get('scope') != SCOPE or contract.get('test_opened') is not False
            or contract.get('S2_accepted') is not False or contract.get('full_match_training') is not False):
        raise ValueError('Unsupported restricted battle-training contract')
    if sha(root/'package-manifest.json') != contract['engine_package_sha256']:
        raise ValueError('Frozen engine package identity mismatch')
    package = json.loads((root/'package-manifest.json').read_text('utf8'))
    for name, expected in package['sha256'].items():
        source = (root/name).resolve()
        if not source.is_relative_to(root) or sha(source) != expected:
            raise ValueError('Frozen release file changed: '+name)
    config = json.loads((root/'run-config.json').read_text('utf8'))
    if packet['config'] != config or digest(config) != contract['config_digest']:
        raise ValueError('Training configuration changed')
    catalogue = TacticalCatalogue.load(root/config['card_table'], rules_version='001.0008.0005',
                                       expected_sha256=config['card_table_sha256'])
    if catalogue.fingerprint != contract['numeric_features_sha256']:
        raise ValueError('Card numeric features changed; new evaluation required')
    model, metadata = load_tactical_checkpoint(root/config['warm_start'], root=root,
        expected_sha256=config['warm_start_sha256'], catalogue=catalogue, device=device)
    if metadata != contract['warm_start'] or metadata['vocabulary'] != packet['vocabulary']:
        raise ValueError('Warm-start architecture or vocabulary mismatch')
    model.load_state_dict(packet['model'], strict=True)
    torch.testing.assert_close(model.rule_features.cpu(),
        torch.tensor(catalogue.matrix(packet['vocabulary'])), rtol=0, atol=0)
    model.to(device).eval()
    return model, packet['vocabulary'], catalogue, {
        'scope':SCOPE, 'step':packet['step'], 'model_sha256':expected_sha256,
        'full_match_training':False, 'independent_acceptance':False, 'exact_resume':False,
        'action_space':'fixed multiset-only candidates ranked by whole-sequence likelihood',
    }


def choose_order(model, vocabulary, cards, card_configs):
    """Use own cards only. No simulator, reward, or opponent state is accepted."""
    import torch
    from .order_model import reconstruction_loss
    orders = candidate_orders(cards, card_configs)
    mapping = {c:i+1 for i,c in enumerate(vocabulary)}
    if set(cards)-mapping.keys():
        raise ValueError('New card requires a versioned vocabulary expansion')
    device = next(model.parameters()).device
    batch = [[mapping[c] for c in order] for order in orders]
    bag = torch.zeros((len(orders),8),dtype=torch.long,device=device)
    bag[:,:len(cards)] = torch.tensor(sorted(batch[0]),device=device)
    prefix = torch.zeros_like(bag); available = bag.ne(0)
    scores = torch.zeros(len(orders),device=device)
    with torch.inference_mode(), torch.autocast(device_type=device.type,dtype=torch.float16,enabled=device.type=='cuda'):
        for step in range(len(cards)):
            wanted = torch.tensor([b[step] for b in batch],device=device)
            targets = available & bag.eq(wanted[:,None])
            scores -= reconstruction_loss(model(bag,prefix,available),targets)
            prefix[:,step] = wanted
            chosen = targets.long().argmax(1)
            available[torch.arange(len(orders),device=device),chosen] = False
    choice = int(scores.argmax())
    result = orders[choice]
    if Counter(result) != Counter(cards):
        raise RuntimeError('Selected order changed owned cards')
    return {'order':result,'candidate_index':choice,'candidate_count':len(orders),
            'sequence_log_likelihood':float(scores[choice]),'private_opponent_input':False}
