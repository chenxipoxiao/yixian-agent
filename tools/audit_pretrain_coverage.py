"""Audit training-only board coverage without opening validation/test labels."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from yixian.order_data import validate_splits


def audit(data):
    manifest = json.loads((data/'manifest.json').read_text(encoding='utf-8'))
    path = data/'train.jsonl'
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest['split_sha256']['train']:
        raise ValueError('Training source hash mismatch')
    with path.open(encoding='utf-8') as stream:
        rows = [json.loads(line) for line in stream]
    splits = validate_splits(rows)
    if set(splits['boards']) != {'train'}:
        raise ValueError('Coverage audit must contain only training labels')
    cards = {row['id']:row for row in json.loads(
        (ROOT/'data/local/2026-11-06/tables/CardConfig.json').read_text(encoding='utf-8'))}
    by_card = defaultdict(set)
    profession_boards, card_realms, lengths = Counter(), Counter(), Counter()
    for row in rows:
        lengths[len(row['board'])] += 1
        professions = set()
        for identifier in row['board']:
            card = cards[identifier]
            by_card[identifier].add(row['game_id'])
            card_realms[card['level']] += 1
            if card.get('career'):
                professions.add(card['career'])
        for career in professions:
            profession_boards[career] += 1
    histogram = Counter()
    for games in by_card.values():
        count = len(games)
        histogram['1' if count == 1 else '2-4' if count < 5 else '5-19' if count < 20 else '20+'] += 1
    rare = sorted(by_card, key=lambda identifier:(len(by_card[identifier]), identifier))[:30]
    return {'source_manifest':str(data/'manifest.json'), 'training_sha256':manifest['split_sha256']['train'],
        'labels_read':['train'], 'training_games':splits['games']['train'], 'boards':len(rows),
        'board_length_counts':dict(lengths), 'unique_raw_card_ids':len(by_card),
        'raw_card_ids_by_independent_game_frequency':dict(histogram),
        'card_occurrences_by_realm':dict(card_realms),
        'boards_containing_profession_card_id':dict(profession_boards),
        'rarest_examples':[{'raw_card_id':identifier, 'name':cards[identifier]['name'],
                           'independent_games':len(by_card[identifier])} for identifier in rare],
        'limitations':['Recorded board cards do not reveal the full hand or actual profession-choice actions.',
                       'Raw card IDs include card upgrade variants; counts are not complete legal-pool coverage.',
                       'No validation or test labels were opened for this coverage audit.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.data)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({key:result[key] for key in ('training_games', 'boards',
        'unique_raw_card_ids', 'raw_card_ids_by_independent_game_frequency',
        'board_length_counts', 'boards_containing_profession_card_id')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
