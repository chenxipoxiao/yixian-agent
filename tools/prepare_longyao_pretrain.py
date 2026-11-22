"""Collect a bounded, checksum-verified replay corpus for board reconstruction."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.import_replays import request_json, download_archive, iter_records, file_hash
from yixian.order_data import extract_boards, validate_splits, SCOPE, VERSION, SPLIT_SALT
from yixian.corpus_acquisition import (archive_names, checked_metadata, prior_game_groups,
    acquisition_lock, daily_usage, AcquisitionBudget, LOCAL_ZONE)

REVISION = 'b592caa9bc6c3b9fb11bb8b3e7691b9840dd36ce'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--shards', type=int, default=8)
    parser.add_argument('--start-shard', type=int, default=34498000)
    parser.add_argument('--exclude-corpus', type=Path, action='append', default=[])
    args = parser.parse_args()
    cache = ROOT/'data/local/hf-replays'
    with acquisition_lock(cache):
        prepare(args, cache)


def prepare(args, cache):
    names = archive_names(args.start_shard, args.shards)
    args.out.mkdir(parents=True, exist_ok=False)
    # Do not reuse the already inspected 34499000 shard for this first holdout.
    infos = request_json(f'https://huggingface.co/api/datasets/sharpobject/yxp_replays/paths-info/{REVISION}', {'paths': names})
    infos = checked_metadata(infos, names)
    (args.out/'source-archives.json').write_text(json.dumps(infos, indent=2), encoding='utf-8')
    excluded = set()
    exclusions = []
    for corpus in args.exclude_corpus:
        groups, provenance = prior_game_groups(corpus)
        excluded.update(groups)
        exclusions.append(provenance)
    inspected = ROOT/'runs/replays/b592caa9bc6c-34499000-g8/rounds.jsonl'
    if inspected.is_file():
        with inspected.open(encoding='utf-8') as stream:
            for line in stream:
                excluded.add(json.loads(line)['game_id'])
    vocabulary_path = ROOT/'data/local/2026-11-06/tables/CardConfig.json'
    vocabulary = sorted(row['id'] for row in json.loads(vocabulary_path.read_text(encoding='utf-8')) if row['id'] > 0)
    allowed = set(vocabulary)
    day = datetime.now(LOCAL_ZONE).strftime('%Y%m%d')
    ledger_directory = ROOT/'runs/acquisitions'
    policy = json.loads((ROOT/'configs/training_stages.json').read_text(encoding='utf-8'))['execution_policy']
    budget = AcquisitionBudget(ledger_directory, day_used=daily_usage(cache, ledger_directory, day),
        batch_limit=policy['max_download_mib_per_acquisition']*1024**2,
        daily_limit=policy['max_download_mib_per_day']*1024**2, output_directory=args.out)

    def acquire(info):
        for attempt in range(2):
            path = cache/info['path']
            if not path.exists():
                # Reserve before each network attempt; failed transfers count
                # conservatively. One chunk of overrun headroom is included.
                budget.reserve(info['path'], info['size']+1024**2)
            try:
                digest = download_archive(REVISION, info, path, 32*1024**2)
                print(json.dumps({'downloaded':info['path'],'bytes':info['size'],'sha256':digest}), flush=True)
                return path, info
            except (OSError, ValueError):
                if attempt == 1 or path.exists():
                    raise
                time.sleep(1)

    records, counts = {}, Counter()
    with ThreadPoolExecutor(max_workers=2) as executor:
        for path, info in executor.map(acquire, infos):
            for member, raw, replay in iter_records(path, 512*1024**2):
                counts['source_view_records'] += 1
                for row in extract_boards(replay, allowed_cards=allowed, excluded_games=excluded):
                    counts['raw_matching_board_appearances'] += 1
                    if row['id'] not in records:
                        row['source'] = {'archive':info['path'],'member':member,
                                         'raw_sha256':hashlib.sha256(raw).hexdigest()}
                        records[row['id']] = row
            print(json.dumps({'processed':info['path'],'unique_boards':len(records)}), flush=True)
    rows = sorted(records.values(), key=lambda row: row['id'])
    split_summary = validate_splits(rows)
    # These gates protect a pilot from vacuous validation, not a claim that the
    # sample is sufficient for a strong general-purpose Long Yao policy.
    for split, minimum in [('train',20),('validation',5),('test',5)]:
        if split_summary['games'].get(split,0) < minimum:
            raise ValueError(f'Insufficient independent {split} games: {split_summary}')
    hashes = {}
    for split in ('train','validation','test'):
        path = args.out/f'{split}.jsonl'
        with path.open('w', encoding='utf-8') as stream:
            for row in rows:
                if row['split'] == split:
                    stream.write(json.dumps(row, separators=(',',':'))+'\n')
        hashes[split] = file_hash(path)
    manifest = {'schema_version':1,'created_at_utc':datetime.now(timezone.utc).isoformat(),
        'scope':SCOPE,'source':'sharpobject/yxp_replays','revision':REVISION,
        'rules_version':VERSION,'season_mec':10,'character_id':1000003,
        'archives':[{'path':item['path'],'bytes':item['size'],'sha256':item['lfs']['oid']} for item in infos],
        'counts':dict(counts),'split_summary':split_summary,'split_salt':SPLIT_SALT,
        'split_sha256':hashes,'excluded_previously_inspected_games':sorted(excluded),
        'prior_corpus_exclusions':exclusions,'acquisition_budget_ledger':str(budget.path.resolve()),
        'reserved_download_bytes':budget.state['reserved_bytes'],
        'holdout_status':'new_group_disjoint_unevaluated' if exclusions else 'unevaluated',
        'vocabulary':vocabulary,'card_config_sha256':file_hash(vocabulary_path),
        'deduplication':'whole_game_and_ordered_board; conservative, not unique-player identification',
        'inputs':'shuffled recorded board multiset and constructed prefix only',
        'recorded_action_trajectory':False,'combat_value_labels':False,
        'limitation':'Auxiliary reconstruction; no claim to genuine pre-action observations, optimal order, rank, or game strength.'}
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'ready':str(args.out),'split_summary':split_summary}),flush=True)


if __name__ == '__main__':
    main()
