"""Freeze all three validation selections without reading final-test bytes."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from yixian.holdout_protocol import freeze_selection
from yixian.pretrain_protocol import sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if sha(args.plan) != args.plan_sha256:
        raise ValueError('Preregistered plan hash mismatch')
    selection = freeze_selection(ROOT, args.plan, args.out)
    print({'selection_sha256': sha(args.out), 'champion_seed': selection['champion_seed'],
           'test_data_opened': False})


if __name__ == '__main__':
    main()
