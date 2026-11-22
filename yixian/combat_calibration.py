"""Development replay evidence for S2; never emits calibrated training labels."""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile

from .order_data import CHARACTER, VERSION, game_split
from .replays import game_key, normalize_replay


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False).encode()).hexdigest()


def select_sources(records, *, games):
    """One pinned view per train game, chosen without looking at battle outcomes."""
    if type(games) is not int or not 1 <= games <= 256:
        raise ValueError('Pilot requires 1..256 whole training games')
    groups = defaultdict(dict)
    members = {}
    for row in records:
        group = row['game_id']
        if row.get('split') != 'train' or game_split(group) != 'train':
            raise ValueError('Calibration pilot accepts training groups only')
        source = row['source']
        archive, member, raw_hash = (source[k] for k in ('archive', 'member', 'raw_sha256'))
        if not re.fullmatch(r'\d+\.tar\.zst', archive):
            raise ValueError('Invalid archive name')
        if not re.fullmatch(r'\d+/\d+_p[0-7]\.json', member):
            raise ValueError('Invalid member name')
        if not re.fullmatch(r'[0-9a-f]{64}', raw_hash):
            raise ValueError('Invalid raw hash')
        key = (archive, member)
        value = (group, raw_hash)
        if members.setdefault(key, value) != value:
            raise ValueError('Inconsistent member provenance')
        groups[group][key] = raw_hash
    if len(groups) < games:
        raise ValueError('Insufficient distinct training groups')
    selected = []
    for group in sorted(groups)[:games]:
        archive, member = min(groups[group])
        selected.append({'game_id': group, 'split': 'train', 'archive': archive,
                         'member': member, 'raw_sha256': groups[group][archive, member]})
    return selected


def iter_selected_records(path, selected, *, max_decoded_bytes=512*1024**2):
    """Parse only explicitly selected members. Other JSON payloads stay unread.

    Tar streaming necessarily decompresses intervening bytes; it does not parse,
    inspect or export their game content. No whole archive is extracted to disk.
    """
    wanted = {row['member']: row for row in selected}
    if len(wanted) != len(selected):
        raise ValueError('Duplicate selected archive member')
    seen, total = set(), 0
    with tarfile.open(path, mode='r|zst') as archive:
        for index, member in enumerate(archive):
            total += max(member.size, 0)
            if index >= 25000 or total > max_decoded_bytes:
                raise ValueError('Decoded archive exceeds audit budget')
            parts = PurePosixPath(member.name)
            if parts.is_absolute() or '..' in parts.parts:
                raise ValueError('Unsafe archive member')
            if member.name not in wanted:
                continue
            if member.name in seen or not member.isfile() or member.size > 8*1024**2:
                raise ValueError('Invalid or duplicate selected archive member')
            with archive.extractfile(member) as stream:
                raw = stream.read()
            source = wanted[member.name]
            if hashlib.sha256(raw).hexdigest() != source['raw_sha256']:
                raise ValueError('Selected replay hash mismatch')
            record = json.loads(raw)
            data = record['data']
            if game_key(data['gameId']) != source['game_id']:
                raise ValueError('Selected replay whole-game mismatch')
            if (data.get('version'), data.get('seasonMec'), data.get('gameMode')) != (VERSION, 10, 3):
                raise ValueError('Selected replay version/season/mode mismatch')
            seen.add(member.name)
            yield source, record
    if seen != set(wanted):
        raise ValueError('Selected archive member missing')


def array_evidence(raw, field):
    if field not in raw:
        return {'status': 'missing'}
    value = raw[field]
    if not isinstance(value, list):
        return {'status': 'invalid_type'}
    return {'status': 'nonempty' if value else 'empty', 'entries': len(value),
            'sha256': digest(value)}


def project_rounds(record, source):
    """Retain public combat candidates, not hands or reconstructed decisions."""
    if game_key(record['data']['gameId']) != source['game_id'] or source['split'] != 'train':
        raise ValueError('Only selected training replay evidence is allowed')
    normalized = normalize_replay(record, dict(source, artifact=f"{source['archive']}::{source['member']}"))
    evidence, settlement_rows = [], []
    for raw, row in zip(record['data']['roundStats'], normalized, strict=True):
        if not any(p['character_id'] == CHARACTER and p['is_ai'] is False for p in row['players']):
            continue
        projected = {k: deepcopy(row[k]) for k in ('id', 'game_id', 'source_rules_version', 'round', 'outcome')}
        projected['source'] = dict(source)
        projected['players'] = []
        for p in row['players']:
            start = deepcopy(p['start_snapshot'])
            start.pop('hand', None)
            raw_start = raw[p['snapshot_slot']]['publicData'].get('lastRoundData', {})
            projected['players'].append({k: deepcopy(p[k]) for k in
                ('snapshot_slot', 'character_id', 'career', 'sect', 'is_ai')} | {
                'candidate_start': start,
                'source_start_field_names': sorted(raw_start),
                'direct_hp_field_present': 'hp' in raw_start,
                'direct_max_hp_field_present': 'maxHp' in raw_start or 'max_hp' in raw_start,
                'timing_verified': False})
        # No player alias is needed for diagnostics; winner/first slot is enough.
        projected['outcome'].pop('winner_player_key', None)
        projected['outcome'].pop('first_player_key', None)
        projected['log_evidence'] = array_evidence(raw, 'log')
        projected['battle_params_evidence'] = array_evidence(raw, 'battleParams')
        projected.update({'scope': 'combat_snapshot_readiness_audit', 'split': 'train',
                          'training_label_allowed': False, 'complete_combat_replayed': False,
                          'original_actions_reconstructed': False})
        evidence.append(projected)
        # Only the established settlement checker sees after-state counters.
        # These remain expected outputs, never initial combat or policy inputs.
        settlement_rows.append(row)
    return evidence, settlement_rows


def summarize_rounds(rows, *, card_mapping, reference_subset, regular_components, season_components):
    games = {r['game_id'] for r in rows}
    kinds = ('cards', 'talents', 'season', 'careers')
    inventory = {side: {kind: defaultdict(set) for kind in kinds} for side in ('longyao', 'opponent')}
    fields, board_lengths, logs, params = Counter(), Counter(), Counter(), Counter()
    both_eight = both_hp = winners = firsts = mapped = subset = 0
    for row in rows:
        logs[row['log_evidence']['status']] += 1
        params[row['battle_params_evidence']['status']] += 1
        winners += row['outcome'].get('winner_snapshot_slot') in ('p1', 'p2')
        firsts += row['outcome'].get('first_player_snapshot_slot') in ('p1', 'p2')
        both_eight += all(len(p['candidate_start'].get('board', [])) == 8 for p in row['players'])
        both_hp += all(p['direct_hp_field_present'] and p['direct_max_hp_field_present'] for p in row['players'])
        cards = [c for p in row['players'] for c in p['candidate_start'].get('board', [])]
        mapped += bool(cards) and all(c in card_mapping for c in cards)
        subset += bool(cards) and all(card_mapping.get(c) in reference_subset for c in cards)
        for p in row['players']:
            role = 'longyao' if p['character_id'] == CHARACTER and p['is_ai'] is False else 'opponent'
            state = p['candidate_start']
            fields.update(p['source_start_field_names'])
            board_lengths[str(len(state.get('board', [])))] += 1
            for kind, key in [('cards', 'board'), ('talents', 'talents'), ('season', 'xian_mo_strategies')]:
                for identifier in set(state.get(key, [])):
                    inventory[role][kind][identifier].add(row['game_id'])
            if p['career'] is not None:
                inventory[role]['careers'][p['career']].add(row['game_id'])
    result_inventory = {}
    for role, kinds in inventory.items():
        result_inventory[role] = {}
        for kind, values in kinds.items():
            result_inventory[role][kind] = []
            for identifier, observed in sorted(values.items(), key=lambda kv: (-len(kv[1]), kv[0])):
                entry = {'raw_id': identifier, 'source_games': len(observed), 'admitted_for_training': False}
                if kind == 'cards':
                    entry.update({'candidate_reference_id': card_mapping.get(identifier),
                                  'in_effect_adapter_subset': card_mapping.get(identifier) in reference_subset,
                                  'effect_parity_verified': False})
                if kind in ('talents', 'season'):
                    components = regular_components if kind == 'talents' else season_components
                    entry.update({'has_registered_component': identifier in components,
                                  'whole_effect_and_interactions_verified': False})
                result_inventory[role][kind].append(entry)
    return {'source_games': len(games), 'human_longyao_round_snapshots': len(rows),
            'log_status_counts': dict(logs), 'battle_params_status_counts': dict(params),
            'recorded_winner_resolved': winners, 'recorded_first_player_resolved': firsts,
            'both_boards_eight_slots': both_eight, 'both_sides_direct_hp_and_max_hp': both_hp,
            'all_cards_have_candidate_mapping': mapped, 'all_cards_in_existing_effect_subset': subset,
            'player_board_length_counts': dict(board_lengths), 'start_field_counts': dict(fields),
            'content_inventory': result_inventory, 'admitted_training_content': [],
            'training_labels_emitted': 0, 'current_version_combat_verified': False,
            'limits': ['One source view per training game; no cross-view player identity inference.',
                       'Counts describe snapshot evidence, not independent wins or strength.',
                       'Catalog mappings/components do not certify executable current-season behavior.',
                       'Missing traces require terminal-outcome calibration and/or new action evidence.',
                       'Initial HP, state timing and cross-effect execution remain unverified.']}
