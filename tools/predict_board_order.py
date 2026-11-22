"""Load the auxiliary checkpoint and order an already chosen bag of cards."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from yixian.order_data import SCOPE
from yixian.order_model import BoardOrderPolicy
from yixian.research import contract_digest


def predict(checkpoint_path, cards, *, device='cpu'):
    if not 3 <= len(cards) <= 8 or any(type(card) is not int or card <= 0 for card in cards):
        raise ValueError('Supply 3..8 positive raw card IDs')
    saved = torch.load(checkpoint_path, map_location=device, weights_only=True)
    contract = saved['contract']
    if contract.get('scope') != SCOPE or saved['contract_digest'] != contract_digest(contract):
        raise ValueError('Unsupported or damaged checkpoint contract')
    for name in ('yixian/order_data.py', 'yixian/order_model.py', 'tools/train_longyao_pretrain.py'):
        digest = hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
        if contract['source_sha256'].get(name) != digest:
            raise ValueError(f'Source contract mismatch: {name}')
    vocabulary = saved['vocabulary']
    digest = hashlib.sha256(json.dumps(vocabulary).encode()).hexdigest()
    if contract['vocabulary_sha256'] != digest or saved['config']['model'] != contract['model']:
        raise ValueError('Vocabulary or architecture contract mismatch')
    mapping = {identifier:index+1 for index, identifier in enumerate(vocabulary)}
    if any(card not in mapping for card in cards):
        raise ValueError('Card is outside the checkpoint vocabulary')
    model = BoardOrderPolicy(len(mapping)+1, **contract['model']).to(device).eval()
    model.load_state_dict(saved['model'])
    candidates = torch.zeros((1, 8), dtype=torch.long, device=device)
    candidates[0, :len(cards)] = torch.tensor([mapping[card] for card in cards], device=device)
    prefix = torch.zeros_like(candidates)
    available = candidates.ne(0)
    output = []
    with torch.inference_mode():
        for step in range(len(cards)):
            logits = model(candidates, prefix, available)
            chosen = int(logits.argmax(dim=1).item())
            if not available[0, chosen]:
                raise ValueError('Model selected an unavailable occurrence')
            token = int(candidates[0, chosen].item())
            output.append(vocabulary[token-1])
            prefix[0, step] = token
            available[0, chosen] = False
    if Counter(cards) != Counter(output):
        raise ValueError('Predicted order changed the supplied card multiset')
    return {'scope':SCOPE, 'checkpoint_step':saved['step'],
            'contract_digest':saved['contract_digest'], 'input_cards':cards,
            'ordered_cards':output, 'prefix_source':'own_previous_predictions',
            'game_strength_evaluated':False, 'full_match_policy':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--cards', type=int, nargs='+', required=True)
    parser.add_argument('--device', choices=['cuda', 'cpu'], default='cpu')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    result = predict(args.checkpoint, args.cards, device=args.device)
    encoded = json.dumps(result, indent=2)+'\n'
    if args.out:
        with args.out.open('x', encoding='utf-8') as stream:
            stream.write(encoded)
    print(encoded, end='')


if __name__ == '__main__':
    main()
