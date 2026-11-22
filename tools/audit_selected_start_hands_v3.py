"""Read hash-pinned selected training views and add only requested start hands."""
from collections import defaultdict, Counter
from copy import deepcopy
from pathlib import Path
import argparse, hashlib, json, sys, time
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from yixian.combat_calibration import iter_selected_records
from yixian.combat_cohort_projection_v2 import project_record
from yixian.combat_start_hand_projection_v3 import add_start_hands, CONTRACT
from yixian.combat_validation_batch_v7 import verify_sources
from yixian.memory import Memory

read = lambda p: json.loads(Path(p).read_text('utf-8-sig'))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(path, value):
    with path.open('x', encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)


def audit(plan_path, out):
    plan = read(plan_path); verify_sources(ROOT, plan['source_sha256'])
    contexts = read(ROOT / plan['baseline_contexts'])
    rows = {r['id']: r for r in map(json.loads, (ROOT / plan['baseline_rows']).read_text('utf8').splitlines())}
    requests = defaultdict(list)
    for r in plan['requests']: requests[r['record_id']].append(r)
    sources = plan['selected_sources']; groups = defaultdict(list)
    assert len({s['game_id'] for s in sources}) == len(sources)
    assert all(s['split'] == 'train' for s in sources)
    assert {rows[rid]['game_id'] for rid in requests} == {s['game_id'] for s in sources}
    for s in sources: groups[s['archive']].append(s)
    pins = {a['path']: a for a in plan['archives']}
    out.mkdir(parents=True, exist_ok=False); write(out / 'plan.json', plan)
    memory = Memory(ROOT / 'runs/research.sqlite')
    exp = memory.register_experiment(plan, {'kind': 'selected_start_hand_source_audit_v3', 'training_labels': False, 'gpu_jobs': 0}, role='environment')
    memory.record_experiment(exp, 'running', role='environment')
    write(out / 'registration.json', {'experiment_id': exp, 'plan_sha256': sha(plan_path)})
    started = time.monotonic()
    try:
        result_contexts = deepcopy(contexts); receipts = []; seen = set(); verified = []
        for name, selected in sorted(groups.items()):
            path = ROOT / 'data/local/hf-replays' / name
            if path.stat().st_size != pins[name]['bytes'] or sha(path) != pins[name]['sha256']:
                raise ValueError('Archive hash/size mismatch: ' + name)
            for source, record in iter_selected_records(path, selected):
                projected, projected_contexts = project_record(record, source)
                # Verify the entire selected view against the already frozen v2
                # projection before any new hand is added.
                assert {r['id'] for r in projected} == {r['id'] for r in rows.values() if r['game_id'] == source['game_id']}
                for row in projected:
                    rid = row['id']
                    assert row == rows[rid] and projected_contexts[rid] == contexts[rid]
                turns = {t['round']: t for t in record['data']['roundStats']}
                for row in projected:
                    rid = row['id']
                    if rid not in requests: continue
                    assert rid not in seen; seen.add(rid)
                    result_contexts[rid] = add_start_hands(turns[row['round']], source, row, contexts[rid], requests[rid])
                    for request in requests[rid]:
                        h = result_contexts[rid]['players'][request['player_index']][request['required_field']]
                        receipts.append({**request, 'hand_receipt': h})
            verified.append(name)
        assert seen == set(requests)
        stripped = deepcopy(result_contexts)
        for receipt in receipts:
            del stripped[receipt['record_id']]['players'][receipt['player_index']][receipt['required_field']]
        assert stripped == contexts, 'Unexpected context mutation'
        write(out / 'combat-context.json', result_contexts)
        write(out / 'start-hand-bindings.json', {'projection_contract': CONTRACT, 'receipts': receipts,
            'policy_observation': False, 'training_label_allowed': False})
        verify_sources(ROOT, plan['source_sha256'])
        result = {'experiment_id': exp, 'success': True, 'projection_contract': CONTRACT,
            'selected_train_games': len(sources), 'selected_records': len(seen), 'added_hand_receipts': len(receipts),
            'fields': dict(Counter(r['required_field'] for r in receipts)), 'unselected_contexts_unchanged': True,
            'all_v2_fields_unchanged': True, 'selected_views_verified_against_original_projection': True,
            'archives_verified': verified, 'archive_bytes_hashed': sum(pins[n]['bytes'] for n in verified),
            'unselected_members_parsed': False, 'current_private_fields_imported': False, 'outcome_fields_imported': False,
            'missing_fields_defaulted': False, 'holdout_opened': False, 'dataset_download_bytes': 0,
            'raw_archives_uploaded': False, 'training_labels_emitted': 0, 'gpu_jobs': 0,
            'elapsed_seconds': time.monotonic() - started,
            'outputs_sha256': {n: sha(out / n) for n in ['combat-context.json', 'start-hand-bindings.json']}}
        write(out / 'report.json', result); memory.record_experiment(exp, 'completed', result, role='environment')
    except Exception as error:
        result = {'experiment_id': exp, 'success': False, 'error': repr(error)}
        write(out / 'failure.json', result); memory.record_experiment(exp, 'failed', result, role='environment')
        raise
    assert memory.verify_integrity(); return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--plan', type=Path, required=True); parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(); print(json.dumps(audit(args.plan, args.out), ensure_ascii=False))
