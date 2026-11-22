"""Recheck pinned training terminal evidence by version; never infer card parity.

Uses recorded life difference, NOT simulated life difference. The two checks
are deliberately separate so a settlement match cannot certify an engine.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from yixian.settlement import ordinary_destiny_damage


def audit(rows, cards):
    versions = defaultdict(Counter); mismatches = []; observed = defaultdict(set)
    games = set(); seen = set()
    for row in rows:
        if row.get('split') != 'train' or not row.get('source_rules_version'):
            raise ValueError('Require versioned development-only evidence')
        if row['id'] in seen:
            raise ValueError('Duplicate replay perspective record')
        seen.add(row['id']); games.add(row['game_id'])
        stats = versions[row['source_rules_version']]; stats['snapshots'] += 1
        outcome = row['outcome']
        hp, actual = outcome.get('recorded_hp_delta'), outcome.get('recorded_destiny_damage')
        if type(hp) not in (int, float) or type(actual) not in (int, float):
            stats['missing_settlement_inputs'] += 1
            continue
        expected = ordinary_destiny_damage(row['round'], abs(hp))
        matches = expected == abs(actual)
        stats['base_match' if matches else 'base_mismatch'] += 1
        player_rows = []
        for player in row['players']:
            state = player['candidate_start']
            for card in state.get('board', []):
                observed[(row['source_rules_version'], card)].add(row['game_id'])
            player_rows.append({'slot': player['snapshot_slot'], 'character': player['character_id'],
                                'talents': state.get('talents'), 'season': state.get('xian_mo_strategies'),
                                'board': state.get('board')})
        if not matches:
            mismatches.append({'record_id': row['id'], 'game_id': row['game_id'],
                'rules_version': row['source_rules_version'], 'round': row['round'],
                'recorded_hp_delta': hp, 'recorded_turn_count': outcome.get('recorded_turn_count'),
                'recorded_damage': abs(actual), 'base_damage': expected,
                'damage_difference': abs(actual)-expected, 'players': player_rows,
                'cause': 'unresolved; settlement effects, input timing and version must be checked'})
    coverage = [{'rules_version': version, 'card_id': card, 'source_games': len(sources),
                 'name': cards.get(card, {}).get('name'), 'sect': cards.get(card, {}).get('sect'),
                 'owner': cards.get(card, {}).get('owner'), 'mechanism_verified': False,
                 'current_engine_parity': False}
                for (version, card), sources in sorted(observed.items())]
    return {'source_games': len(games), 'snapshots': len(seen),
            'by_version': {v: dict(c) for v, c in versions.items()},
            'mismatch_difference_counts': dict(Counter(str(m['damage_difference']) for m in mismatches)),
            'mismatches': mismatches, 'observed_card_coverage': coverage,
            'all_catalog_cards': len(cards), 'observed_distinct_cards': len({c for _, c in observed}),
            'scope': 'recorded_terminal_hp_difference_to_base_destiny_damage',
            'resimulated_battles': 0, 'card_mechanisms_verified': 0,
            'winner_hp_turn_parity_verified': False, 'training_labels_emitted': 0,
            'heldout_test_opened': False,
            'limitations': ['Base mismatch is not proof of a formula or card bug.',
                           'Different versions remain separate; this pilot does not sample every version.',
                           'No per-action logs; terminal outcomes alone need not uniquely identify mechanics.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = json.loads((args.pilot/'report.json').read_text(encoding='utf-8-sig'))
    source = args.pilot/'evidence-rounds.jsonl'
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    if actual != report['output_sha256']['evidence-rounds.jsonl']:
        raise ValueError('Frozen replay evidence changed')
    rows = [json.loads(line) for line in source.read_text(encoding='utf-8').splitlines()]
    cards = json.loads((ROOT/'data/local/2026-11-06/tables/CardConfig.json').read_text(encoding='utf-8-sig'))
    result = audit(rows, {c['id']: c for c in cards})
    result['source_evidence_sha256'] = actual
    result['original_pilot_report'] = str(args.pilot/'report.json')
    with args.out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('mismatches', 'observed_card_coverage')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
