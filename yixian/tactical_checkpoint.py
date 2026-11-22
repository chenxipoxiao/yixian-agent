"""Explicit v3 loading and legal proposal generation; never load v3 as v2."""
from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path

from .research import contract_digest
from .tactical_rules import TacticalCatalogue

SCOPE = 'rule_aware_recorded_order_proposal_v3'


def load_tactical_checkpoint(path, *, root, expected_sha256, catalogue, device='cpu',
                             allow_rule_patch=False):
    import torch
    from .tactical_model import TacticalProposalPolicy
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected_sha256:
        raise ValueError('Checkpoint hash mismatch')
    packet = torch.load(path, map_location='cpu', weights_only=True)
    contract = packet['contract']
    if (contract.get('schema_version') != 3 or contract.get('scope') != SCOPE
            or packet['contract_digest'] != contract_digest(contract)):
        raise ValueError('Invalid v3 proposal contract')
    if contract.get('test_data_opened') is not False or contract.get('battle_labels_used') is not False:
        raise ValueError('Unexpected proposal training evidence')
    for name, expected in contract['source_sha256'].items():
        source = (Path(root)/name).resolve()
        if not source.is_relative_to(Path(root).resolve()) or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Proposal source contract mismatch: {name}')
    vocabulary = packet['vocabulary']
    from .tactical_rules import digest
    if digest(vocabulary) != contract['vocabulary_digest']:
        raise ValueError('Vocabulary contract mismatch')
    patch = catalogue.fingerprint != contract['card_rule_fingerprint']
    if patch and not allow_rule_patch:
        raise ValueError('New rules require explicit patch re-evaluation mode')
    model = TacticalProposalPolicy(len(vocabulary)+1, rule_features=catalogue.matrix(vocabulary),
                                   **contract['model'])
    model.load_state_dict(packet['model'])
    # Never silently keep the stale feature buffer stored in old weights.
    if patch:
        model.rule_features.copy_(torch.tensor(catalogue.matrix(vocabulary)))
    else:
        torch.testing.assert_close(model.rule_features, torch.tensor(catalogue.matrix(vocabulary)), rtol=0, atol=0)
    model.to(device).eval()
    return model, {'vocabulary': vocabulary, 'rule_patch_applied': patch,
                   'rules_fingerprint': catalogue.fingerprint, 'scope': SCOPE,
                   'patch_strength_verified': False, 'battle_strength_verified': False,
                   'exact_resume': False}


def generate_proposals(model, vocabulary, cards, *, count=32, seed=0):
    """One greedy proposal followed by seeded samples; no reference prefixes."""
    import torch
    if type(count) is not int or not 1 <= count <= 4096 or not 1 <= len(cards) <= 8:
        raise ValueError('Invalid generation budget')
    mapping = {c: i+1 for i, c in enumerate(vocabulary)}
    if set(cards)-mapping.keys():
        raise ValueError('New card IDs require a versioned vocabulary expansion')
    device = next(model.parameters()).device
    generator = torch.Generator(device=device).manual_seed(seed)
    bag = torch.zeros((count, 8), device=device, dtype=torch.long)
    bag[:, :len(cards)] = torch.tensor([mapping[c] for c in cards], device=device)
    prefix, available = torch.zeros_like(bag), bag.ne(0)
    model.eval()
    with torch.inference_mode():
        for step in range(len(cards)):
            logits = model(bag, prefix, available)
            chosen = torch.multinomial(logits.softmax(-1), 1, generator=generator).squeeze(1)
            chosen[0] = logits[0].argmax()
            prefix[:, step] = bag[torch.arange(count, device=device), chosen]
            available[torch.arange(count, device=device), chosen] = False
    proposals = []
    for row in prefix.cpu().tolist():
        board = tuple(vocabulary[token-1] for token in row[:len(cards)])
        if Counter(board) != Counter(cards):
            raise RuntimeError('Proposal generator changed owned cards')
        if board not in proposals:
            proposals.append(board)
    return proposals
