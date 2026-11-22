"""Bind verified original replay preparation fields; selected train members only."""
from pathlib import Path
from copy import deepcopy
from collections import defaultdict, Counter
import argparse, hashlib, json, sys, time
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from yixian.combat_calibration import iter_selected_records
from yixian.combat_cohort_projection_v2 import project_record
from yixian.combat_start_context_bindings_v6 import bind_preparation, validate_additions
from yixian.combat_validation_batch_v7 import verify_sources
from yixian.memory import Memory
read = lambda p: json.loads(Path(p).read_text('utf-8-sig'))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
digest = lambda d: hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def write(p, value):
    with p.open('x', encoding='utf8') as f: json.dump(value, f, ensure_ascii=False, indent=2)


def audit(plan_path, out):
    plan = read(plan_path); verify_sources(ROOT, plan['source_sha256'])
    rows = {r['id']: r for r in map(json.loads, (ROOT / plan['rows']).read_text('utf8').splitlines())}
    v2 = read(ROOT / plan['v2_contexts']); previous = read(ROOT / plan['previous_contexts']); contexts = deepcopy(previous)
    requests = {r['record_id']: r for r in plan['source_requests']}; groups = defaultdict(list)
    for s in plan['selected_sources']: groups[s['archive']].append(s)
    assert all(s['split'] == 'train' for s in plan['selected_sources'])
    assert {rows[r]['game_id'] for r in requests} == {s['game_id'] for s in plan['selected_sources']}
    out.mkdir(parents=True, exist_ok=False); write(out / 'plan.json', plan)
    memory = Memory(ROOT / 'runs/research.sqlite')
    exp = memory.register_experiment(plan, {'kind': 'original_preparation_source_binding_v6', 'training_labels': False, 'gpu_jobs': 0}, role='environment')
    memory.record_experiment(exp, 'running', role='environment'); write(out / 'registration.json', {'experiment_id': exp})
    started = time.monotonic()
    try:
        pins = {a['path']: a for a in plan['archives']}; verified = []; seen = set(); inventory = []; additions = []
        for name, sources in sorted(groups.items()):
            p = ROOT / 'data/local/hf-replays' / name
            assert p.stat().st_size == pins[name]['bytes'] and sha(p) == pins[name]['sha256']
            for source, record in iter_selected_records(p, sources):
                projected, projected_contexts = project_record(record, source)
                assert {r['id'] for r in projected} == {r['id'] for r in rows.values() if r['game_id'] == source['game_id']}
                for row in projected:
                    assert row == rows[row['id']] and projected_contexts[row['id']] == v2[row['id']]
                turns = {t['round']: t for t in record['data']['roundStats']}
                for row in projected:
                    rid = row['id']
                    if rid not in requests: continue
                    assert rid not in seen; seen.add(rid); request = requests[rid]
                    assert request['kind'] == 'preparation_phase_receipt'
                    contexts[rid] = bind_preparation(turns[row['round']], source, row, contexts[rid])
            verified.append(name)
        assert seen == set(requests)
        admissions = validate_additions(list(rows.values()), previous, contexts, set(requests))
        write(out / 'combat-context.json', contexts); write(out / 'admitted-records.json', admissions)
        verify_sources(ROOT, plan['source_sha256'])
        result = {'experiment_id': exp, 'success': True, 'selected_train_games': len(plan['selected_sources']),
            'selected_raw_records': len(seen), 'bound_preparation_records': len(admissions),
            'archives_verified': verified, 'archive_bytes_hashed': sum(pins[n]['bytes'] for n in verified),
            'existing_context_unchanged_except_declared_additions': True,
            'source': 'original BattleResult private map through verified client reference chain',
            'missing_complete_map_defaulted': False, 'private_hands_exported': False,
            'policy_observation_allowed': False, 'counterfactual_reuse_allowed': False,
            'unselected_members_parsed': False, 'holdout_opened': False,
            'download_bytes': 0, 'gpu_jobs': 0, 'training_labels_emitted': 0,
            'elapsed_seconds': time.monotonic() - started,
            'outputs_sha256': {n: sha(out / n) for n in ('combat-context.json', 'admitted-records.json')}}
        write(out / 'report.json', result); memory.record_experiment(exp, 'completed', result, role='environment')
    except Exception as error:
        result = {'success': False, 'experiment_id': exp, 'error': repr(error)}
        write(out / 'failure.json', result); memory.record_experiment(exp, 'failed', result, role='environment'); raise
    assert memory.verify_integrity(); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--plan', type=Path, required=True); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); print(json.dumps(audit(a.plan, a.out), ensure_ascii=False))
