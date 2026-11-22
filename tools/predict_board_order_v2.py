"""Contract-checked own-prefix inference for a frozen development v2 model."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from yixian.order_checkpoint import load_order_checkpoint
from yixian.order_evaluation import decode_own_prefix, torch_scorer


def main():
    import torch
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--checkpoint-sha256', required=True)
    parser.add_argument('--cards', type=int, nargs='+', required=True)
    parser.add_argument('--device', choices=['cuda', 'cpu'], default='cpu')
    args = parser.parse_args()
    model, metadata = load_order_checkpoint(args.checkpoint, root=ROOT,
        expected_sha256=args.checkpoint_sha256, device=args.device)
    mapping = {card: index+1 for index, card in enumerate(metadata['vocabulary'])}
    if not 3 <= len(args.cards) <= 8 or any(card not in mapping for card in args.cards):
        raise ValueError('Supply 3..8 cards from the checkpoint vocabulary')
    bag = np.zeros((1, 8), dtype=np.int64)
    bag[0, :len(args.cards)] = [mapping[card] for card in args.cards]
    tokens = decode_own_prefix(bag, torch_scorer(model, torch.device(args.device)))[0]
    print(json.dumps({'ordered_cards': [metadata['vocabulary'][token-1] for token in tokens],
                      'checkpoint_step': metadata['step'], 'prefix_source': 'own_previous_predictions',
                      'full_match_policy': False, 'game_strength_evaluated': False}))


if __name__ == '__main__':
    main()
