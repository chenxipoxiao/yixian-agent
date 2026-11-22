"""Freeze a batch's impact selection, then run a targeted or closing full pass."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from yixian.combat_validation_batch import create_plan, run_plan


def main():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest='command', required=True)
    plan = commands.add_parser('plan')
    plan.add_argument('--spec', type=Path, required=True)
    plan.add_argument('--out', type=Path, required=True)
    run = commands.add_parser('run')
    run.add_argument('--plan', type=Path, required=True)
    run.add_argument('--out', type=Path, required=True)
    run.add_argument('--full', action='store_true', help='One closing full pass after the batch is ready')
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError('Preserve old results; choose a new output path')
    started = time.monotonic()
    if args.command == 'plan':
        spec = json.loads(args.spec.read_text('utf8'))
        result = create_plan(ROOT, **spec)
        display = result['selection']
    else:
        result = run_plan(ROOT, json.loads(args.plan.read_text('utf8')), full=args.full)
        result['elapsed_seconds'] = time.monotonic() - started
        display = {**result['summary'], 'elapsed_seconds': result['elapsed_seconds'], 'regression': result['regression']}
    with args.out.open('x', encoding='utf8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(display, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
