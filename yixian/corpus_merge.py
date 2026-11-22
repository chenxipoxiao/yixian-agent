"""Freeze approved corpus partitions without recycling used test games."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .order_data import CHARACTER, SCOPE, SPLIT_SALT, VERSION, validate_splits


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compose(registry, root, minimum_games):
    selected, owners, ids, excluded, retired_test = [], {}, set(), set(), set()
    parents, archives, reference = [], {}, None
    entries = registry['corpora']
    if not entries or len({item['id'] for item in entries}) != len(entries):
        raise ValueError('Corpus registry must have unique nonempty source entries')
    for entry in entries:
        roles = entry['allowed_roles_in_next_experiment']
        if not roles or len(set(roles)) != len(roles) or not set(roles) <= {'train','validation','test'}:
            raise ValueError('Invalid approved source roles')
        if 'test' in roles and entry['test_use_status'] != 'never_model_evaluated':
            raise ValueError('A previously evaluated test partition cannot become a new final test')
        directory = root/entry['directory']
        manifest_path = directory/'manifest.json'
        if sha(manifest_path) != entry['manifest_sha256']:
            raise ValueError('Registered source manifest checksum mismatch')
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        expected = (SCOPE, VERSION, SPLIT_SALT, CHARACTER, 10)
        if tuple(manifest[key] for key in ('scope','rules_version','split_salt','character_id','season_mec')) != expected:
            raise ValueError('Source scope, character, season or split contract mismatch')
        identity = {key:manifest[key] for key in ('vocabulary','card_config_sha256','revision')}
        if reference is not None and identity != reference:
            raise ValueError('Source vocabulary, rules snapshot or revision mismatch')
        reference = identity
        allowed = set(manifest['vocabulary'])
        all_rows = []
        parent_counts = {}
        for split in ('train','validation','test'):
            path = directory/f'{split}.jsonl'
            if sha(path) != manifest['split_sha256'][split]:
                raise ValueError('Source partition checksum mismatch')
            count = 0
            with path.open(encoding='utf-8') as stream:
                for line in stream:
                    row = json.loads(line)
                    if row['split'] != split:
                        raise ValueError('Source record is in the wrong partition')
                    group = row['game_id']
                    if owners.setdefault(group, entry['id']) != entry['id']:
                        raise ValueError('Source corpora overlap in whole-game groups')
                    board = row['board']
                    if (not isinstance(board,list) or not 3 <= len(board) <= 8
                            or any(type(card) is not int or card <= 0 or card not in allowed for card in board)
                            or len(set(board)) < 2 or row.get('season_mec') != 10):
                        raise ValueError('Invalid board in registered source')
                    expected_id = hashlib.sha256(json.dumps([group,board],separators=(',',':')).encode()).hexdigest()
                    if row['id'] != expected_id or row['id'] in ids:
                        raise ValueError('Corrupt or duplicate whole-game/board identity')
                    ids.add(row['id'])
                    all_rows.append(row)
                    if split in roles:
                        selected.append(row)
                        count += 1
                    else:
                        excluded.add(group)
                        if split == 'test':
                            retired_test.add(group)
            parent_counts[split] = count
        if validate_splits(all_rows) != manifest['split_summary']:
            raise ValueError('Source split counts disagree with its manifest')
        # Parent exclusions are acquisition-local. Some refer to approved train
        # or validation rows from another source, which are allowed to be reused.
        parents.append({'id':entry['id'],'directory':entry['directory'],
                        'manifest_sha256':entry['manifest_sha256'],
                        'approved_roles':roles,'included_board_counts':parent_counts,
                        'test_use_status':entry['test_use_status'],
                        'acquisition_exclusions':manifest.get('excluded_previously_inspected_games',[])})
        for item in manifest['archives']:
            if item['path'] in archives and archives[item['path']] != item:
                raise ValueError('Source archives disagree on provenance')
            archives[item['path']] = item
    for parent in parents:
        excluded.update(set(parent.pop('acquisition_exclusions'))-set(owners))
    selected_groups = {row['game_id'] for row in selected}
    if selected_groups & excluded:
        raise ValueError('A retired group leaked into the approved corpus')
    summary = validate_splits(selected)
    for split in ('train','validation','test'):
        minimum = minimum_games[split]
        if type(minimum) is not int or minimum < 1:
            raise ValueError('Independent-game minimum must be a positive integer')
        if summary['games'].get(split,0) < minimum:
            raise ValueError(f'Insufficient independent {split} games: {summary["games"].get(split,0)} < {minimum}')
    return sorted(selected,key=lambda row:row['id']), {
        **reference,'schema_version':1,'scope':SCOPE,'rules_version':VERSION,
        'split_salt':SPLIT_SALT,'character_id':CHARACTER,'season_mec':10,
        'source':'sharpobject/yxp_replays','source_corpora':parents,
        'archives':sorted(archives.values(),key=lambda row:row['path']),
        'split_summary':summary,'excluded_previously_inspected_games':sorted(excluded),
        'retired_test_game_count':len(retired_test),'minimum_independent_games':minimum_games,
        'merge_strategy':'preserve original whole-game partitions and approved source roles',
        'holdout_status':'new_group_disjoint_unevaluated','test_model_evaluations':0,
        'recorded_action_trajectory':False,'combat_value_labels':False,
        'inputs':'shuffled recorded board multiset and constructed prefix only',
        'limitation':'Auxiliary reconstruction corpus, not complete human action trajectories or combat-strength labels.'}


def freeze_corpus(registry_path, out, *, root, minimum_games):
    if out.exists():
        raise FileExistsError('Use a new output directory; frozen corpora are immutable')
    registry = json.loads(registry_path.read_text(encoding='utf-8'))
    rows, manifest = compose(registry,root,minimum_games)
    out.mkdir(parents=True,exist_ok=False)
    (out/'source-registry.json').write_bytes(registry_path.read_bytes())
    manifest['source_registry_sha256'] = sha(out/'source-registry.json')
    hashes = {}
    for split in ('train','validation','test'):
        path = out/f'{split}.jsonl'
        with path.open('x',encoding='utf-8') as stream:
            for row in rows:
                if row['split'] == split:
                    stream.write(json.dumps(row,separators=(',',':'))+'\n')
        hashes[split] = sha(path)
    manifest['created_at_utc'] = datetime.now(timezone.utc).isoformat()
    manifest['split_sha256'] = hashes
    manifest['merge_source_sha256'] = sha(Path(__file__))
    with (out/'manifest.json').open('x',encoding='utf-8') as stream:
        json.dump(manifest,stream,indent=2)
    return manifest
