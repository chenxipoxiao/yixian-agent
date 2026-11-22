"""Apply pinned client base initialization to an already frozen train-only pilot."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.import_replays import file_hash
from yixian.combat_calibration import iter_selected_records
from yixian.combat_initialization import load_initialization_contract, derive_base_combat_state, IncompleteCombatState
from yixian.order_data import game_split
from yixian.memory import Memory


def write(path, data):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if file_hash(args.pilot/'plan.json') != args.plan_sha256:
        raise ValueError('Pilot plan pin mismatch')
    read = lambda p: json.loads(p.read_text(encoding='utf-8'))
    prior_plan, prior_report = read(args.pilot/'plan.json'), read(args.pilot/'report.json')
    if prior_report['plan_sha256'] != args.plan_sha256:
        raise ValueError('Pilot report does not belong to plan')
    rows_path = args.pilot/'evidence-rounds.jsonl'
    if file_hash(rows_path) != prior_report['output_sha256']['evidence-rounds.jsonl']:
        raise ValueError('Pilot evidence hash mismatch')
    rows = [json.loads(line) for line in rows_path.open(encoding='utf-8')]
    expected = {(row['source']['raw_sha256'], row['round']): row for row in rows}
    if len(expected) != len(rows) or any(row.get('split') != 'train' or game_split(row['game_id']) != 'train' for row in rows):
        raise ValueError('Pilot must contain unique training snapshots')
    selected = prior_plan['selected_sources']
    if any(s['split'] != 'train' or game_split(s['game_id']) != 'train' for s in selected):
        raise ValueError('Pilot source not a training game')
    contract = load_initialization_contract()
    sources = ['yixian/combat_initialization.py', 'tools/audit_combat_initialization.py',
               'yixian/combat_calibration.py', 'yixian/order_data.py', 'yixian/replays.py',
               'tools/import_replays.py', 'data/inspection/base-combat-initialization-v1.json',
               'data/local/2026-11-06/tables/LevelConfig.json']
    pins = {name: file_hash(ROOT/name) for name in sources}
    plan = {'scope': 'S2_base_combat_initialization_before_effects',
            'created_at_utc': datetime.now(timezone.utc).isoformat(),
            'pilot_plan_sha256': args.plan_sha256, 'pilot_report_sha256': file_hash(args.pilot/'report.json'),
            'pilot_evidence_sha256': file_hash(rows_path), 'selected_sources': selected,
            'expected_rounds': len(rows), 'contract': contract, 'source_sha256': pins,
            'network_downloads': False, 'training_labels': False, 'gpu_jobs': 0}
    args.out.mkdir(parents=True, exist_ok=False)
    write(args.out/'plan.json', plan)
    for name in sources:
        if name.endswith('.py'):
            p = args.out/'source'/name; p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes((ROOT/name).read_bytes())
    memory = Memory(ROOT/'runs/research.sqlite')
    experiment = memory.register_experiment(plan, contract, role='environment')
    write(args.out/'registration.json', {'experiment_id': experiment})
    memory.record_experiment(experiment, 'running', role='environment')
    try:
        by_archive = defaultdict(list)
        for source in selected:
            by_archive[source['archive']].append(source)
        archives = {a['path']: a for a in prior_plan['archives']}
        results, seen = [], set()
        for name, selection in sorted(by_archive.items()):
            path = ROOT/'data/local/hf-replays'/name
            if path.stat().st_size != archives[name]['bytes'] or file_hash(path) != archives[name]['sha256']:
                raise ValueError('Cached archive pin mismatch')
            for source, record in iter_selected_records(path, selection):
                for turn in record['data']['roundStats']:
                    key = (source['raw_sha256'], turn['round'])
                    if key not in expected:
                        continue
                    original = expected[key]
                    if original['game_id'] != source['game_id'] or key in seen:
                        raise ValueError('Original round/source mismatch')
                    seen.add(key)
                    for slot in ('p1', 'p2'):
                        public = turn[slot]['publicData']
                        result = {'record_id': original['id'], 'game_id': source['game_id'],
                                  'round': turn['round'], 'slot': slot, 'character_id': public['characterId']}
                        try:
                            result.update(status='base_state_derived',
                                          initialization=derive_base_combat_state(public, contract=contract))
                        except IncompleteCombatState as error:
                            result.update(status='incomplete_evidence', error=str(error), training_label_allowed=False)
                        results.append(result)
        if seen != set(expected):
            raise ValueError('Not all frozen pilot rounds were recovered')
        successes = [r for r in results if r['status'] == 'base_state_derived']
        levels = Counter(str(r['initialization']['snapshot_levels_agree']) for r in successes)
        ranges = [r['initialization']['base_combat']['hp'] for r in successes]
        mismatches = [r for r in successes if r['initialization']['snapshot_levels_agree'] is not True]
        with (args.out/'base-states.jsonl').open('x', encoding='utf-8') as stream:
            for row in results:
                stream.write(json.dumps(row, ensure_ascii=False, separators=(',', ':'))+'\n')
        report = {'schema_version': 1, 'scope': plan['scope'], 'experiment_id': experiment,
                  'completed_at_utc': datetime.now(timezone.utc).isoformat(),
                  'plan_sha256': file_hash(args.out/'plan.json'), 'contract': contract,
                  'source_games': len({r['game_id'] for r in results}), 'round_snapshots': len(seen),
                  'player_snapshots': len(results), 'base_states_derived': len(successes),
                  'incomplete_states': len(results)-len(successes), 'public_vs_last_round_level_agreement': dict(levels),
                  'level_disagreement_or_missing_examples': mismatches[:10],
                  'candidate_base_hp_range': [min(ranges), max(ranges)] if ranges else None,
                  'base_states_sha256': file_hash(args.out/'base-states.jsonl'),
                  'prior_s1_test_groups_used': 0, 'unselected_raw_members_parsed': False,
                  'original_acquisition_rewards_reapplied': False,
                  'new_download_bytes': 0, 'gpu_job_seconds': 0, 'current_server_calibration_passed': False,
                  'complete_combat_replayed': False, 'training_labels_emitted': 0,
                  'limits': ['Derived from pinned client initialization instructions, not independently observed initial HP.',
                             'Agreement of two level fields does not prove correct snapshot timing.',
                             'Only base state before InitData/OnBattleStarted hooks; permanent and fate effects pending.',
                             'No battle win rate, order policy evaluation, or full-match strength measurement.']}
        write(args.out/'report.json', report)
        memory.record_experiment(experiment, 'completed', {'report': str(args.out/'report.json'),
            'report_sha256': file_hash(args.out/'report.json'), 'training_labels': 0}, role='environment')
        print(json.dumps({k: v for k, v in report.items() if k not in ('contract', 'level_disagreement_or_missing_examples')}, ensure_ascii=False))
    except Exception as error:
        write(args.out/'failure.json', {'experiment_id': experiment, 'type': type(error).__name__, 'error': str(error)})
        memory.record_experiment(experiment, 'failed', {'failure': str(args.out/'failure.json')}, role='environment')
        raise


if __name__ == '__main__':
    main()
