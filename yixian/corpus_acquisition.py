"""Bounded replay acquisition and whole-game exclusion, without model labels."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import threading
import uuid

from .order_data import SCOPE, SPLIT_SALT, VERSION, game_split

LOCAL_ZONE = timezone(timedelta(hours=8))


def archive_names(start, count):
    if type(start) is not int or start % 1000 or not 1000 <= start <= 34498000:
        raise ValueError('Start must be a pinned-era thousand boundary, excluding inspected shard 34499000')
    if type(count) is not int or not 1 <= count <= 12 or start-(count-1)*1000 < 0:
        raise ValueError('Acquire 1..12 valid shards')
    return [f'{start-index*1000}.tar.zst' for index in range(count)]


def checked_metadata(infos, names, cap=192*1024**2):
    if len(infos) != len(names) or {item['path'] for item in infos} != set(names):
        raise ValueError('Archive metadata paths do not exactly match the request')
    for item in infos:
        if type(item['size']) is not int or not 0 < item['size'] <= 32*1024**2:
            raise ValueError('Invalid archive size')
        if not re.fullmatch('[a-f0-9]{64}', item.get('lfs', {}).get('oid', '')):
            raise ValueError('Missing authoritative archive SHA256')
    if sum(item['size'] for item in infos) > cap:
        raise ValueError('Acquisition exceeds compressed payload budget')
    return sorted(infos, key=lambda item:names.index(item['path']))


def prior_game_groups(directory):
    """Read group IDs only, including used test groups; never emit their boards."""
    manifest_path = directory/'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if (manifest['scope'], manifest['rules_version'], manifest['split_salt']) != (SCOPE, VERSION, SPLIT_SALT):
        raise ValueError('Excluded corpus has an incompatible split contract')
    groups = set(manifest.get('excluded_previously_inspected_games', []))
    for split in ('train', 'validation', 'test'):
        path = directory/f'{split}.jsonl'
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest['split_sha256'][split]:
            raise ValueError('Excluded corpus checksum mismatch')
        with path.open(encoding='utf-8') as stream:
            for line in stream:
                row = json.loads(line)
                if row['split'] != split or game_split(row['game_id']) != split:
                    raise ValueError('Excluded corpus whole-game split mismatch')
                groups.add(row['game_id'])
    return groups, {'manifest':str(manifest_path.resolve()),
        'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        'excluded_groups_including_prior_exclusions':len(groups),
        'fields_used_from_prior_records':['game_id', 'split']}


@contextmanager
def acquisition_lock(cache):
    cache.mkdir(parents=True, exist_ok=True)
    path = cache/'.acquisition.lock'
    # A crash leaves evidence; a subsequent run must inspect it, not assume it
    # can erase another downloader's lock and duplicate its work.
    with path.open('x', encoding='utf-8') as stream:
        stream.write(datetime.now(timezone.utc).isoformat())
    try:
        yield
    finally:
        path.unlink()


def daily_usage(cache, ledger_directory, day):
    charged, names = 0, set()
    for path in ledger_directory.glob(day+'-*.json'):
        ledger = json.loads(path.read_text(encoding='utf-8'))
        if ledger['local_day'] != day:
            raise ValueError('Acquisition ledger date mismatch')
        entries = ledger['reservations']
        if ledger['reserved_bytes'] != sum(item['bytes'] for item in entries):
            raise ValueError('Acquisition ledger total mismatch')
        charged += ledger['reserved_bytes']
        names.update(item['archive'] for item in entries)
    # The initial pilot predates this reservation ledger. Account for those
    # same-day cached files once; conservatively charge failed reserved attempts.
    for path in cache.glob('*.tar.zst'):
        if path.name not in names and datetime.fromtimestamp(path.stat().st_mtime, LOCAL_ZONE).strftime('%Y%m%d') == day:
            charged += path.stat().st_size
    return charged


class AcquisitionBudget:
    def __init__(self, ledger_directory, *, day_used, batch_limit, daily_limit, output_directory):
        now = datetime.now(timezone.utc)
        self.lock = threading.Lock()
        self.batch_limit, self.daily_limit, self.day_used = batch_limit, daily_limit, day_used
        self.state = {'created_at_utc':now.isoformat(), 'local_day':now.astimezone(LOCAL_ZONE).strftime('%Y%m%d'),
                      'output_directory':str(output_directory), 'reserved_bytes':0, 'reservations':[]}
        ledger_directory.mkdir(parents=True, exist_ok=True)
        self.path = ledger_directory/(self.state['local_day']+'-'+uuid.uuid4().hex+'.json')
        self.save()

    def save(self):
        temporary = self.path.with_suffix('.part')
        temporary.write_text(json.dumps(self.state, indent=2)+'\n', encoding='utf-8')
        temporary.replace(self.path)

    def reserve(self, archive, size):
        with self.lock:
            total = self.state['reserved_bytes']+size
            if total > self.batch_limit or self.day_used+total > self.daily_limit:
                raise ValueError('Download reservation exceeds batch or daily budget')
            self.state['reserved_bytes'] = total
            self.state['reservations'].append({'archive':archive, 'bytes':size})
            self.save()
