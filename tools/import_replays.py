"""Download one pinned HF shard and import a bounded, whole-game sample.

Python 3.14 supplies streaming Zstandard support. Archive members are read as
data; no tar paths are extracted and no code from the dataset is executed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from yixian.replays import game_key, normalize_replay
from yixian.opponents import split_for_game_id

DATASET = 'sharpobject/yxp_replays'
BASE = 'https://huggingface.co'


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def request_json(url, body=None):
    payload = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url, data=payload,
        headers={'User-Agent': 'YiXianAgent-local-research/0.1', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=40) as response:
        content = response.read(4*1024*1024+1)
    if len(content) > 4*1024*1024:
        raise ValueError('Metadata response exceeds limit')
    return json.loads(content)


def file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def download_archive(revision, info, path, cap):
    expected = info.get('lfs', {}).get('oid')
    if not expected or not re.fullmatch('[a-f0-9]{64}', expected):
        raise ValueError('Archive has no authoritative LFS SHA256')
    if info['size'] > cap:
        raise ValueError('Archive exceeds download budget')
    if path.exists():
        if path.stat().st_size != info['size'] or file_hash(path) != expected:
            raise ValueError('Cached archive does not match pinned source')
        return expected
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix+'.part')
    request = urllib.request.Request(f'{BASE}/datasets/{DATASET}/resolve/{revision}/{info["path"]}',
                                    headers={'User-Agent': 'YiXianAgent-local-research/0.1'})
    digest = hashlib.sha256()
    try:
        with urllib.request.urlopen(request, timeout=40) as response, partial.open('wb') as output:
            size = 0
            while block := response.read(1024*1024):
                size += len(block)
                if size > cap or size > info['size']:
                    raise ValueError('Download exceeds expected size')
                digest.update(block)
                output.write(block)
        if size != info['size'] or digest.hexdigest() != expected:
            raise ValueError('Downloaded shard checksum/size mismatch')
        partial.replace(path)
    finally:
        partial.unlink(missing_ok=True)
    return expected


def iter_records(path, max_decoded_bytes):
    total = 0
    seen_members = set()
    with tarfile.open(path, mode='r|zst') as archive:
        for index, member in enumerate(archive):
            if index >= 25000:
                raise ValueError('Archive member count exceeds budget')
            total += max(member.size, 0)
            if total > max_decoded_bytes:
                raise ValueError('Decoded archive exceeds budget')
            if not member.isfile() or not member.name.endswith('.json'):
                continue
            parts = PurePosixPath(member.name).parts
            if '..' in parts or PurePosixPath(member.name).is_absolute():
                raise ValueError('Unsafe archive member name')
            if not re.fullmatch(r'\d+_p[0-7]\.json', parts[-1]):
                continue
            if member.name in seen_members:
                raise ValueError('Duplicate replay archive member')
            seen_members.add(member.name)
            if member.size > 8*1024*1024:
                raise ValueError('Individual replay exceeds budget')
            with archive.extractfile(member) as stream:
                raw = stream.read()
            record = json.loads(raw)
            if isinstance(record, dict) and isinstance(record.get('data'), dict):
                yield member.name, raw, record


def import_sample(*, games=4, season=10, mode=3, archive=None, revision=None,
                  cache=ROOT/'data/local/hf-replays', out=None, max_download_mb=32, max_decoded_mb=512):
    if type(games) is not int or not 1 <= games <= 20:
        raise ValueError('Sample between 1 and 20 games')
    for value in (max_download_mb, max_decoded_mb):
        if type(value) is not int or value < 1:
            raise ValueError('Download and decoded budgets must be positive integer MB')
    if type(season) is not int or type(mode) is not int:
        raise ValueError('Season and mode must be integer configuration IDs')
    if revision is not None and not re.fullmatch('[a-f0-9]{40}', revision):
        raise ValueError('Use a pinned 40-character dataset commit')
    metadata = request_json(f'{BASE}/api/datasets/{DATASET}' + (f'/revision/{revision}' if revision else ''))
    revision = metadata['sha']
    paths = [x['rfilename'] for x in metadata['siblings'] if re.fullmatch(r'\d+\.tar\.zst', x['rfilename'])]
    archive = archive or max(paths, key=lambda name: int(name.split('.')[0]))
    if archive not in paths:
        raise ValueError('Archive is absent from the pinned dataset revision')
    infos = request_json(f'{BASE}/api/datasets/{DATASET}/paths-info/{revision}', {'paths': [archive]})
    if len(infos) != 1 or infos[0]['path'] != archive:
        raise ValueError('Archive metadata mismatch')
    info = infos[0]
    cache = Path(cache).resolve()
    archive_path = cache/archive
    digest = download_archive(revision, info, archive_path, max_download_mb*1024*1024)
    out = Path(out).resolve() if out else ROOT/'runs/replays'/f'{revision[:12]}-{archive.split(".")[0]}-g{games}'
    if (out/'manifest.json').exists():
        raise ValueError(f'An import already exists at {out}; use a new output directory to preserve provenance')
    selected, counts = {}, Counter()
    # First pass chooses whole games. isDaoXinRank is perspective-specific;
    # after a game is chosen, the second pass retains all available viewpoints.
    for name, raw, record in iter_records(archive_path, max_decoded_mb*1024*1024):
        data = record['data']
        counts[f"season={data.get('seasonMec')},mode={data.get('gameMode')},dao_xin={data.get('isDaoXinRank')}"] += 1
        if data.get('seasonMec') != season or data.get('gameMode') != mode or data.get('isDaoXinRank') is not True:
            continue
        key = game_key(data.get('gameId'))
        if key not in selected and len(selected) < games:
            selected[key] = {'members': [], 'round_records': 0, 'versions': set(), 'perspective_indices': set()}
    if not selected:
        raise ValueError('This shard has no games matching the requested season/mode')
    out.mkdir(parents=True, exist_ok=True)
    raw_dir = cache/'samples'/revision/archive.split('.')[0]
    all_rounds, sources = [], []
    for name, raw, record in iter_records(archive_path, max_decoded_mb*1024*1024):
        data = record['data']
        key = game_key(data.get('gameId'))
        if key not in selected:
            continue
        if data.get('seasonMec') != season or data.get('gameMode') != mode:
            raise ValueError('Perspectives of a selected whole game disagree on season or mode')
        raw_path = raw_dir/PurePosixPath(name).name
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        if raw_path.exists() and raw_path.read_bytes() != raw:
            raise ValueError('Existing pinned sample differs from archive')
        raw_path.write_bytes(raw)
        source = {'dataset': DATASET, 'revision': revision, 'archive': archive,
                  'archive_sha256': digest, 'member': name, 'artifact': str(raw_path),
                  'raw_sha256': hashlib.sha256(raw).hexdigest(), 'whole_game_id': key}
        rounds = normalize_replay(record, source)
        split = split_for_game_id(key, salt='raw-replay-v1', fractions=(.6, .2, .2))
        for row in rounds:
            row['dataset_split'] = split
        all_rounds.extend(rounds)
        sources.append(source)
        selected[key]['members'].append(name)
        selected[key]['round_records'] += len(rounds)
        selected[key]['versions'].add(data.get('version'))
        selected[key]['perspective_indices'].add(int(PurePosixPath(name).stem.rsplit('_p', 1)[1]))
    with (out/'rounds.jsonl').open('w', encoding='utf-8') as stream:
        for row in all_rounds:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False)+'\n')
    for game in selected.values():
        game['versions'] = sorted(game['versions'], key=str)
        game['available_perspectives'] = len(game['members'])
        game['perspective_indices'] = sorted(game['perspective_indices'])
        game['unique_perspective_indices'] = len(game['perspective_indices'])
        game['all_eight_json_perspectives_present'] = game['perspective_indices'] == list(range(8))
    manifest = {'schema_version': 1, 'dataset': DATASET, 'revision': revision,
                'archive': archive, 'archive_sha256': digest, 'download_bytes': info['size'],
                'archive_population': dict(counts), 'selection': {'season_mec': season, 'mode': mode,
                    'require_one_dao_xin_perspective': True, 'requested_games': games,
                    'method': 'First matching whole games in pinned archive order; not a representative random sample'},
                'games': selected, 'whole_games': len(selected), 'perspective_records': len(sources),
                'round_records': len(all_rounds), 'sources': sources,
                'normalized_sha256': file_hash(out/'rounds.jsonl'),
                'simulator_input_verified': False, 'policy_observation_verified': False,
                'limitation': 'Round snapshots and season choices; not a complete action log or verified current-season simulator input.'}
    write_json(out/'manifest.json', manifest)
    return out, manifest


def main():
    parser = argparse.ArgumentParser(description='按整局抽取少量当前赛季公开回放')
    parser.add_argument('--games', type=int, default=4)
    parser.add_argument('--archive')
    parser.add_argument('--revision')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    out, manifest = import_sample(games=args.games, archive=args.archive, revision=args.revision, out=args.out)
    print(json.dumps({'out': str(out), **{key:manifest[key] for key in
                      ('revision','archive','download_bytes','whole_games','perspective_records','round_records')}},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
