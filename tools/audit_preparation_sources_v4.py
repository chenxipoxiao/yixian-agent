"""Inventory private preparation fields as evidence only; add explicit start hands."""
from pathlib import Path
from copy import deepcopy
from collections import defaultdict, Counter
import argparse, hashlib, json, sys, time
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from yixian.combat_calibration import iter_selected_records
from yixian.combat_cohort_projection_v2 import project_record
from yixian.combat_start_hand_projection_v3 import add_start_hands
from yixian.combat_start_context_bindings_v4 import bind_paper_opening
from yixian.combat_validation_batch_v7 import verify_sources
from yixian.memory import Memory
read = lambda p: json.loads(Path(p).read_text('utf-8-sig'))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
digest = lambda d: hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def write(p, value):
    with p.open('x', encoding='utf8') as f: json.dump(value, f, ensure_ascii=False, indent=2)


def inspect_preparation(turn, row, request):
    result = {'record_id': row['id'], 'game_id': row['game_id'], 'round': row['round'],
        'source_raw_sha256': row['source']['raw_sha256'], 'first_blocker': request['reason'], 'players': [],
        'comparison_only': True, 'combat_input_allowed': False}
    for i, slot in enumerate(('p1', 'p2')):
        start = turn[slot]['publicData']['lastRoundData']
        owned = row['players'][i]['candidate_start']['xian_mo_strategies']
        private = turn[slot].get('privateData'); season = private.get('xianMoData') if isinstance(private, dict) else None
        temp = season.get('tempDatas') if isinstance(season, dict) else None
        choices = season.get('strategies') if isinstance(season, dict) else None
        selected = [s.get('selected') for s in choices] if isinstance(choices, list) and all(isinstance(s, dict) for s in choices) else None
        result['players'].append({'snapshot_slot': slot, 'start_field_names': sorted(start),
            'start_has_xianMoData': 'xianMoData' in start, 'start_has_tempDatas': 'tempDatas' in start,
            'start_ownership': owned, 'private_season_field_names': sorted(season) if isinstance(season, dict) else None,
            'private_complete_temp_map_present': isinstance(temp, dict),
            'private_temp_map_sha256': digest(temp) if isinstance(temp, dict) else None,
            'private_relevant_values_comparison_only': {str(x): deepcopy(temp[str(x)]) for x in owned if str(x) in temp} if isinstance(temp, dict) else None,
            'private_selected_ids_comparison_only': selected,
            'private_selected_matches_start': set(selected) == set(owned) if selected is not None else None,
            'timing_verified_by_this_audit': False})
    return result


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
    exp = memory.register_experiment(plan, {'kind': 'preparation_source_inventory_and_original_bindings_v4', 'training_labels': False, 'gpu_jobs': 0}, role='environment')
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
                    if request['kind'] == 'lastRoundData_hand':
                        contexts[rid] = add_start_hands(turns[row['round']], source, row, contexts[rid], [request])
                        i = request['player_index']; field = request['required_field']
                        additions.append({'record_id': rid, 'player_index': i, 'field': field, 'value': contexts[rid]['players'][i][field]})
                    else:
                        assert request['kind'] == 'preparation_phase_receipt'
                        inventory.append(inspect_preparation(turns[row['round']], row, request))
            verified.append(name)
        assert seen == set(requests)
        for request in plan['paper_requests']:
            rid = request['record_id']; contexts[rid] = bind_paper_opening(rows[rid], contexts[rid])
            additions.append({'record_id': rid, 'player_index': None, 'field': 'falling_paper_record', 'value': contexts[rid]['falling_paper_record']})
        stripped = deepcopy(contexts)
        for a in additions:
            target = stripped[a['record_id']] if a['player_index'] is None else stripped[a['record_id']]['players'][a['player_index']]
            del target[a['field']]
        assert stripped == previous, 'Private inventory or other data leaked into combat inputs'
        write(out / 'combat-context.json', contexts); write(out / 'additions.json', additions)
        write(out / 'preparation-inventory.json', {'records': inventory, 'combat_input_allowed': False, 'comparison_only': True})
        verify_sources(ROOT, plan['source_sha256'])
        players = [p for r in inventory for p in r['players']]
        result = {'experiment_id': exp, 'success': True, 'selected_train_games': len(plan['selected_sources']),
            'selected_raw_records': len(seen), 'preparation_records_inspected': len(inventory),
            'preparation_player_states': len(players), 'start_season_maps_present': sum(p['start_has_xianMoData'] for p in players),
            'private_complete_maps_present': sum(p['private_complete_temp_map_present'] for p in players),
            'private_ownership_equal_to_start': sum(p['private_selected_matches_start'] is True for p in players),
            'additions_by_field': dict(Counter(a['field'] for a in additions)),
            'archives_verified': verified, 'archive_bytes_hashed': sum(pins[n]['bytes'] for n in verified),
            'existing_context_unchanged_except_declared_additions': True, 'private_preparation_fields_imported': False,
            'preparation_timing_proven_by_field_presence': False, 'unselected_members_parsed': False,
            'holdout_opened': False, 'download_bytes': 0, 'gpu_jobs': 0, 'training_labels_emitted': 0,
            'elapsed_seconds': time.monotonic() - started,
            'outputs_sha256': {n: sha(out / n) for n in ('combat-context.json', 'additions.json', 'preparation-inventory.json')}}
        write(out / 'report.json', result); memory.record_experiment(exp, 'completed', result, role='environment')
    except Exception as error:
        result = {'success': False, 'experiment_id': exp, 'error': repr(error)}
        write(out / 'failure.json', result); memory.record_experiment(exp, 'failed', result, role='environment'); raise
    assert memory.verify_integrity(); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--plan', type=Path, required=True); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); print(json.dumps(audit(a.plan, a.out), ensure_ascii=False))
