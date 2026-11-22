"""Run a read-only replay diagnostic and create a new, non-overwriting report."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from yixian.death_validation import validate_death_fate_replays


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rounds', default='runs/replays/b592caa9bc6c-34499000-g8/rounds.jsonl')
    parser.add_argument('--local-root', default='data/local/2026-11-06')
    parser.add_argument('--output')
    args = parser.parse_args()
    report = validate_death_fate_replays(args.rounds, local_root=args.local_root)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = Path(args.output or f'runs/diagnostics/death-fates-{timestamp}.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'report': str(output.resolve()), 'counts_by_effect': report['counts_by_effect'],
                      'observable_checks': report['observable_checks'],
                      'observable_mismatches': report['observable_mismatches'],
                      'complete_battle_validation': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
