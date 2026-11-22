"""Reuse frozen full battles, re-execute the seven gain cases, compare settlement.

The input report contains previous complete simulations. This is not a new
525-battle campaign. Only affected battles are re-executed; all settlements
are recomputed from unchanged compiled starts and outputs, never poststate.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from yixian.full_battle_v46 import simulate_batch
from yixian.terminal_damage_v47 import calculate_terminal_damage


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def check(report_path, target_path, observations):
    plan = json.loads(target_path.read_text('utf8'))
    if sha(report_path) != plan['source_report_sha256']:
        raise ValueError('Frozen source battle report changed')
    report = json.loads(report_path.read_text('utf8'))
    targets = {t['record_id'] for t in plan['targets']}
    cases = report['cases']
    selected = [c for c in cases if c['record_id'] in targets]
    if len(selected) != len(targets) or len(cases) != plan['all_simulated_records']:
        raise ValueError('Unexpected source/target set')
    rerun = simulate_batch([c['compiled']['battle'] for c in selected])['results']
    if rerun != [c['simulation'] for c in selected]:
        raise ValueError('Previously frozen battle outputs changed')
    settlements, target_rows = [], []
    comparisons_unchanged = 0
    for case in cases:
        answer = calculate_terminal_damage(case['compiled'], case['simulation'])
        signed = answer['life_damage']*(1 if case['simulation']['winner'] == 0 else -1) if answer['resolved'] else None
        comparisons = deepcopy(case['comparison'])
        comparisons['destiny_damage'] = signed == case['expected']['recorded_destiny_damage']
        comparisons_unchanged += int(comparisons == case['comparison'])
        settlements.append({'record_id': case['record_id'], 'settlement': answer, 'comparison': comparisons})
        if case['record_id'] not in targets:
            if answer != case['settlement']:
                raise ValueError('Unaffected settlement changed')
            continue
        ledger = answer['civet_settlement']
        observed = observations[case['record_id']]
        predicted = ledger['predicted_destiny_after_terminal_damage']
        before = ledger['destiny_before_battle']
        if before != observed['before_destiny']:
            raise ValueError('Observed source start does not match simulation start')
        balance_comparison = [p == a if type(a) is int else None for p, a in zip(predicted, observed['after_destiny'])]
        target_rows.append({
            'record_id': case['record_id'], 'game_id': case['game_id'], 'round': case['round'],
            'winner': case['simulation']['winner'], 'hp_delta': case['simulation']['hp_delta'],
            'turns': case['simulation']['turns'], 'battle_used_randomness': case['simulation']['used_randomness'],
            'original_all_four_match': case['all_four_match'], 'comparison': comparisons,
            'life_damage': answer['life_damage'], 'civet_settlement': ledger,
            'recorded_before_destiny': before, 'recorded_after_destiny': observed['after_destiny'],
            'balance_comparison': balance_comparison, 'pending_match_effects': answer['pending_match_effects'],
            'has_survival_fate': [bool(set(p['fates']) & {7, 65, 83, 154}) for p in case['compiled']['effect_players']],
            'recorded_counter_comparison_not_used': True,
        })
    return {
        'scope': 'v46 full-battle outputs reused; affected7 re-executed; v47 settlement recomputed for377',
        'source_report_sha256': sha(report_path), 'source_battle_summary_unchanged': report['summary'],
        'target_battles_reexecuted': len(selected), 'target_battle_outputs_identical': True,
        'settlements_recomputed': len(cases), 'unaffected_settlements_identical': len(cases)-len(selected),
        'previous_four_way_comparisons_unchanged': comparisons_unchanged,
        'all_four_matches': sum(all(c['comparison'].values()) for c in settlements),
        'settlement_outputs_sha256': digest(settlements),
        'target_balance_matches': sum(all(x is True for x in c['balance_comparison']) for c in target_rows),
        'target_balance_sides_matches': sum(x is True for c in target_rows for x in c['balance_comparison']),
        'targets': target_rows, 'settlements': settlements,
        'raw_observations_used_as_input': False, 'holdout_read': False,
        'new_gpu_jobs': 0, 'training_labels_emitted': 0, 'S2_accepted': False,
        'limitations': ['No survival or >100 server validation unless observed in these target records.',
                       'Other rewards and counter mutations are pending; not a complete match transition.',
                       'Historical random battle mismatches are retained, not fitted.',
                       'The100-cap and survival-order rules are user confirmed, not inferred from endpoint matching.'],
    }
