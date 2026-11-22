"""Replay the fixed website cohort using owner-bound sound switch observations."""
from pathlib import Path
from collections import Counter
import copy
import hashlib
import json
import subprocess
import sys

sys.setrecursionlimit(20000)
ROOT = Path(__file__).resolve().parents[1]
S = ROOT / 'runs/stages/20261116T121200Z-s2-website-sound-switches'
PRIOR = ROOT / 'runs/stages/20261116T114200Z-s2-website-battles'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'runs/stages/20261116T110900Z-s2-opening-inputs'))
from audit_web_inputs import states
from yixian import website_battles_v133 as adapter, full_battle_v130, terminal_damage_v129


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def extract():
    cases = read(PRIOR / 'cases-v2.json')
    cache = {}
    receipts = []
    for case in cases:
        row = case['row']
        source = row['source']
        path = Path(source['path'])
        if str(path) not in cache:
            assert sha(path) == source['raw_sha256']
            recording = read(path)
            cache[str(path)] = (recording, {n: (before, step) for n, before, after, step in states(recording)})
        recording, boundaries = cache[str(path)]
        before, step = boundaries[source['step']]
        private = before['privatePlayer']
        assert private['uid'] == recording['targetUid']
        assert before['round'] == step['battle']['round'] == row['round']
        assert private['deck'] == row['players'][0]['candidate_start']['board']
        pairs = [m for m in step['battle']['matchups'] if m.get('authoritative') is True
                 and private['uid'] in m['players']]
        assert len(pairs) == 1 and pairs[0]['players'][private['uid']]['deck'] == private['deck']
        refs = {r['id']: r for r in private['selectedXianMoStrategies']}
        owned = sorted(adapter.SOUND_IDS.intersection(row['players'][0]['candidate_start']['xian_mo_strategies']))
        if not owned:
            continue
        assert all(sid in refs and type(refs[sid].get('locked')) is bool for sid in owned)
        receipt = {'origin': adapter.ORIGIN, 'source_raw_sha256': sha(path), 'source_step': source['step'],
                   'case_id': row['id'], 'player_index': 0, 'environment_only': True,
                   'selected_strategy_ids': owned, 'temp_data': {str(sid): int(refs[sid]['locked']) for sid in owned}}
        case['combat_context']['players'][0]['sound_control_switch'] = receipt
        case['mechanisms']['sound_switches'] = {str(sid): refs[sid]['locked'] for sid in owned}
        receipts.append({**receipt, 'url': case['url'], 'source_runtime': {str(sid): refs[sid]['runtime'] for sid in owned}})
    write(S / 'cases.json', cases)
    write(S / 'source-switch-receipts.json', {'receipts': receipts, 'opponent_switches_inferred': 0,
          'disabled': sum(any(r['temp_data'].values()) for r in receipts), 'source_rules_version_certified': False})
    return cases


def simulate(battles, prefix):
    proc = subprocess.run(['node', '--experimental-default-type=module', str(ROOT / 'tools/full_battle_bridge_web_v132.mjs')],
                          input=json.dumps(battles, ensure_ascii=False), text=True, encoding='utf-8',
                          capture_output=True, cwd=ROOT, timeout=120)
    write(S / (prefix + '-process.json'), {'exit_code': proc.returncode, 'stderr': proc.stderr})
    proc.check_returncode()
    result = json.loads(proc.stdout)
    assert len(result) == len(battles)
    return result


def run():
    cases = extract()
    view = adapter.compiler()
    tables = full_battle_v130.catalogue()
    expected = {x['id']: x for x in read(PRIOR / 'observations-v2.json')}
    compiled, rows = [], []
    for case in cases:
        row = {k: copy.deepcopy(case[k]) for k in ('url', 'initiative', 'timing_differences', 'mechanisms')}
        row['id'] = case['row']['id']
        try:
            value = adapter.compile_case(case, view, tables)
            row.update(status='compiled', compiled_index=len(compiled))
            compiled.append(value)
        except Exception as exc:
            row.update(status='input_unresolved', reason=str(exc), error_type=type(exc).__name__)
        rows.append(row)
    write(S / 'compiled.json', compiled)
    write(S / 'input-screening.json', rows)
    result = simulate([c['battle'] for c in compiled], 'website')
    write(S / 'simulations.json', result)
    for row in rows:
        if row['status'] != 'compiled':
            continue
        i = row['compiled_index']
        value = result[i]
        if value.get('unresolved') or not value.get('terminated') or value.get('truncated'):
            row.update(status='runtime_unresolved', reason=value.get('reason', 'not_terminated'))
            continue
        obs = expected[row['id']]
        winner = value['winner']
        row.update(status='complete', used_randomness=value['used_randomness'], predicted_winner=winner,
                   observed_results=obs['result'], winner_match=obs['result'][winner] == 'win',
                   simulated_hp_delta=value['hp_delta'], simulated_turns=value['turns'])
        settlement = terminal_damage_v129.calculate_terminal_damage(compiled[i], value)
        row['settlement'] = settlement
        if settlement.get('resolved'):
            delta = [0, 0]
            delta[1-winner] = -settlement['life_damage']
            row.update(predicted_deduction_delta=delta, observed_deduction_delta=obs['life_delta'], deduction_match=delta == obs['life_delta'])
    complete = [r for r in rows if r['status'] == 'complete']
    deterministic = [r for r in complete if not r['used_randomness']]
    new = [r for r in complete if r['mechanisms'].get('sound_switches')]
    summary = {'records': len(rows), 'complete': len(complete), 'deterministic': len(deterministic),
               'winner_matches': sum(r['winner_match'] for r in complete),
               'deduction_matches': sum(r.get('deduction_match', False) for r in complete),
               'deterministic_both_match': sum(r['winner_match'] and r.get('deduction_match', False) for r in deterministic),
               'sound_complete': len(new), 'sound_nonrandom': sum(not r['used_randomness'] for r in new),
               'sound_nonrandom_both_match': sum(not r['used_randomness'] and r['winner_match'] and r.get('deduction_match', False) for r in new),
               'unresolved': dict(Counter(r.get('reason') for r in rows if r['status'] != 'complete')),
               'training_label_allowed': False, 'S2_accepted': False, 'independent_acceptance': False,
               'source_version_certified': False, 'source_start_completeness_certified': False,
               'missing_terminal_hp_and_turns': True}
    write(S / 'full-battle-report.json', {'summary': summary, 'rows': rows})
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    run()
