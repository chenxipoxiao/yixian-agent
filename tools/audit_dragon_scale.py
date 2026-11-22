"""Audit the ordinary fate 27 cap using a previously pinned training pilot."""
from collections import defaultdict
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.import_replays import file_hash
from yixian.combat_calibration import iter_selected_records
from yixian.dragon_scale_validation import audit_dragon_scale
from yixian.effects import EffectEngine
from yixian.memory import Memory
from yixian.order_data import game_split, CHARACTER
from yixian.replays import normalize_replay


def write(path, data):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--resonance-evidence', type=Path, required=True)
    args = parser.parse_args()
    if file_hash(args.pilot/'plan.json') != args.plan_sha256:
        raise ValueError('Pilot plan hash mismatch')
    prior = json.loads((args.pilot/'plan.json').read_text(encoding='utf-8'))
    prior_report = json.loads((args.pilot/'report.json').read_text(encoding='utf-8'))
    if prior_report['plan_sha256'] != args.plan_sha256:
        raise ValueError('Pilot report does not belong to plan')
    evidence = args.pilot/'evidence-rounds.jsonl'
    if file_hash(evidence) != prior_report['output_sha256']['evidence-rounds.jsonl']:
        raise ValueError('Pilot evidence hash mismatch')
    expected = {(r['source']['raw_sha256'], r['round']) for r in
                (json.loads(line) for line in evidence.open(encoding='utf-8'))}
    selected = prior['selected_sources']
    if any(s['split'] != 'train' or game_split(s['game_id']) != 'train' for s in selected):
        raise ValueError('Calibration accepts training games only')
    engine = EffectEngine.from_local()
    sources = ['yixian/dragon_scale.py', 'yixian/dragon_scale_validation.py', 'tools/audit_dragon_scale.py',
               'yixian/effects.py', 'yixian/effect_validation.py', 'yixian/settlement.py',
               'yixian/death_fates.py', 'yixian/season_start.py', 'yixian/replays.py',
               'yixian/order_data.py', 'yixian/combat_calibration.py', 'tools/import_replays.py',
               'data/inspection/dragon-scale-cap-v1.json']
    plan = {'created_at_utc': datetime.now(timezone.utc).isoformat(),
            'scope': 'S2_ordinary_dragon_scale_cap_and_counter_evidence',
            'pilot_plan_sha256': args.plan_sha256, 'pilot_report_sha256': file_hash(args.pilot/'report.json'),
            'pilot_evidence_sha256': file_hash(evidence), 'selected_sources': selected,
            'expected_rounds': len(expected), 'effect_contract': engine.contract(),
            'source_sha256': {name: file_hash(ROOT/name) for name in sources},
            'heldout_test_groups_used': 0, 'new_download_bytes': 0, 'gpu_jobs': 0,
            'training_labels': False, 'counter_inference_scope': 'descriptive_only_no_import_mapping_change'}
    plan['resonance_context_evidence'] = {'path': args.resonance_evidence.as_posix(),
                                         'sha256': file_hash(args.resonance_evidence)}
    args.out.mkdir(parents=True, exist_ok=False)
    write(args.out/'plan.json', plan)
    for name in sources:
        target = args.out/'source'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes())
    (args.out/'resonance-context-evidence.json').write_bytes(args.resonance_evidence.read_bytes())
    memory = Memory(ROOT/'runs/research.sqlite')
    experiment = memory.register_experiment(plan, engine.contract(), role='environment')
    write(args.out/'registration.json', {'experiment_id': experiment})
    memory.record_experiment(experiment, 'running', role='environment')
    try:
        by_archive = defaultdict(list)
        for source in selected:
            by_archive[source['archive']].append(source)
        archives = {r['path']: r for r in prior['archives']}
        records, seen = [], set()
        for name, selection in sorted(by_archive.items()):
            path = ROOT/'data/local/hf-replays'/name
            if path.stat().st_size != archives[name]['bytes'] or file_hash(path) != archives[name]['sha256']:
                raise ValueError('Cached archive hash mismatch')
            for source, raw in iter_selected_records(path, selection):
                normalized = normalize_replay(raw, dict(source, artifact=f'{name}::{source["member"]}'))
                for turn, row in zip(raw['data']['roundStats'], normalized, strict=True):
                    key = (source['raw_sha256'], row['round'])
                    if key not in expected:
                        continue
                    if key in seen or not any(p['character_id'] == CHARACTER and p['is_ai'] is False for p in row['players']):
                        raise ValueError('Duplicate or changed pilot round')
                    seen.add(key)
                    for player in row['players']:
                        raw_player = turn[player['snapshot_slot']]
                        selection = raw_player.get('privateData', {}).get('talentResonanceData', {}).get('selectionData', {})
                        player['audit_context'] = {'is_mirror': raw_player['publicData'].get('isMirror'),
                                                   'resonance_selected': selection.get('selected')}
                    records.append(row)
        if seen != expected:
            raise ValueError('Not all frozen pilot rounds recovered')
        result = audit_dragon_scale(records, engine=engine)
        comparisons = result.pop('records')
        counters = result.pop('counter_observations')
        # Per-round evidence stays local. Deployment only needs the summary.
        for name, rows in [('comparisons.jsonl', comparisons), ('counter-observations.jsonl', counters)]:
            with (args.out/name).open('x', encoding='utf-8') as stream:
                for row in rows:
                    stream.write(json.dumps(row, ensure_ascii=False, separators=(',', ':'))+'\n')
        report = dict(result, schema_version=1, experiment_id=experiment,
                      completed_at_utc=datetime.now(timezone.utc).isoformat(),
                      plan_sha256=file_hash(args.out/'plan.json'),
                      source_games=len(selected), round_snapshots=len(records),
                      output_sha256={name: file_hash(args.out/name) for name in ('comparisons.jsonl', 'counter-observations.jsonl')},
                      heldout_test_groups_used=0, new_download_bytes=0, gpu_job_seconds=0)
        write(args.out/'report.json', report)
        memory.record_experiment(experiment, 'completed', {'report': str(args.out/'report.json'),
            'report_sha256': file_hash(args.out/'report.json'), 'training_labels': 0}, role='environment')
        print(json.dumps(report, ensure_ascii=False))
    except Exception as error:
        write(args.out/'failure.json', {'experiment_id': experiment, 'error_type': type(error).__name__, 'error': str(error)})
        memory.record_experiment(experiment, 'failed', {'failure': str(args.out/'failure.json')}, role='environment')
        raise


if __name__ == '__main__':
    main()
