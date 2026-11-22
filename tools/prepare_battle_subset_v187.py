"""Freeze corrected numeric panels without inheriting any old reward labels."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import shutil
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from yixian.battle_subset_v187 import candidate_orders, reactive_orders, digest

STAGE = ROOT/'runs/stages/20261118T025300Z-s2-corrected-subset-v187'
BASE = ROOT/'runs/tactical-releases/verified-subset-v185r4'
OUT = ROOT/'runs/tactical-releases/verified-subset-v187'
read = lambda p: json.loads(Path(p).read_text('utf-8-sig'))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')


def main():
    assert not OUT.exists()
    base_manifest = read(BASE/'package-manifest.json')
    for name, expected in base_manifest['sha256'].items():
        assert sha(BASE/name) == expected, name
    old = read(BASE/'data/starts.json')
    contract = read(ROOT/'runs/tactical/20261118T022800Z-verified-subset-v185r4/training-contract.json')
    vocabulary = set(contract['warm_start']['vocabulary'])
    cards = {c['id']: c for c in read(ROOT/'data/local/2026-11-06/tables/CardConfig.json')}
    rows = []; excluded = []; changes = []
    for source in old:
        own = source['raw_cards'][source['learner']]
        unknown = sorted(set(own)-vocabulary)
        if unknown:
            excluded.append({'id':source['id'], 'reason':'outside_frozen_model_vocabulary', 'raw_ids':unknown})
            continue
        row = deepcopy(source)
        history = row['opponent_visible_learner_history']
        for c in set(sum(row['raw_cards'], [])) | set(history['board'] if history else []):
            assert {'anima', 'def', 'attack', 'attackCount'} <= cards[c].keys(), c
        row['candidate_orders'] = candidate_orders(own, cards)
        row['opponent_orders'] = reactive_orders(row['raw_cards'][1-row['learner']], history, row['round'], cards)
        # Candidate generation must not depend on the order passed as a bag.
        assert row['candidate_orders'] == candidate_orders(list(reversed(own)), cards)
        assert row['opponent_orders'] == reactive_orders(sorted(row['raw_cards'][1-row['learner']]), history, row['round'], cards)
        for order in row['candidate_orders']:
            assert Counter(order) == Counter(own)
        for order in row['opponent_orders']:
            assert Counter(order) == Counter(row['raw_cards'][1-row['learner']])
        assert row['opponent_observation_digest'] == digest({'own_cards':sorted(row['raw_cards'][1-row['learner']]), 'earlier_public_target':history})
        changed = {k:row[k]!=source[k] for k in ['candidate_orders','opponent_orders']}
        changes.append({'id':row['id'], **changed})
        for key in source.keys()-changed.keys():
            assert row[key] == source[key], key
        rows.append(row)
    assert {c for r in excluded for c in r['raw_ids']} == {0}
    train = {r['game_id'] for r in rows if r['split']=='train'}
    validation = {r['game_id'] for r in rows if r['split']=='validation'}
    assert not train & validation
    # The two opposite signed-qi cases establish the corrected resource meaning.
    from yixian.battle_subset_numeric_v186 import numeric_priority
    assert cards[332]['anima'] == 2 and numeric_priority(332, cards, 1., 0)[0] == -8.
    assert cards[7000043]['anima'] == -1 and numeric_priority(7000043, cards, 1., 0)[0] == 2.
    try:
        reactive_orders(own, {'round':16, 'board':own}, 16, cards)
    except ValueError:
        pass
    else:
        raise AssertionError('Current sealed opponent order was accepted')
    shutil.copytree(BASE, OUT)
    additions = ['yixian/battle_subset_v187.py', 'yixian/battle_subset_numeric_v186.py',
        'yixian/battle_subset_checkpoint_v187.py', 'tools/run_battle_subset_v187.py',
        'tools/train_battle_subset_v187.py', 'tools/prepare_battle_subset_v187.py']
    for name in additions:
        shutil.copyfile(ROOT/name, OUT/name)
    write(OUT/'data/starts.json', rows)
    source_manifest = read(BASE/'data/source-manifest.json')
    source_manifest.update(schema='verified-subset-input-v187', starts=len(rows),
        starts_sha256=sha(OUT/'data/starts.json'), parent_starts_sha256=sha(BASE/'data/starts.json'),
        numeric_protocol='signed anima qi gain/cost corrected; full candidate panels recomputed',
        old_rewards_reused=False, vocabulary_excluded=excluded,
        split_records=dict(Counter(r['split'] for r in rows)),
        split_games={'train':len(train),'validation':len(validation)},
        games=len(train|validation), unique_battles=len({r['record_id'] for r in rows}),
        public_history_available=sum(r['opponent_visible_learner_history'] is not None for r in rows))
    write(OUT/'data/source-manifest.json', source_manifest)
    config = read(BASE/'run-config.json'); config.pop('inherited_search')
    config.update(scope='longyao_verified_subset_battle_order_v187', revision='v187',
        protocol_change='Correct anima sign for candidate generation and all three opponent scripts',
        reward_cache_policy='fresh rewards for all retained states; no v185 cache reuse',
        comparison_limit='Different action and opponent panels; compare step 0 and updates within v187 only')
    write(OUT/'run-config.json', config)
    manifest = deepcopy(base_manifest)
    manifest.update(schema='isolated-battle-training-release-v187',
        created_utc=datetime.now(timezone.utc).isoformat(),
        base_package_sha256=sha(BASE/'package-manifest.json'),
        sha256={p.relative_to(OUT).as_posix():sha(p) for p in sorted(OUT.rglob('*'))
                if p.is_file() and p.name!='package-manifest.json' and '__pycache__' not in p.parts})
    write(OUT/'package-manifest.json', manifest)
    changed = [n for n,h in manifest['sha256'].items() if base_manifest['sha256'].get(n)!=h]
    archive = OUT.with_suffix('.overlay.tar.gz')
    with tarfile.open(archive, 'w:gz') as tar:
        for name in changed+['package-manifest.json']:
            tar.add(OUT/name, arcname=name)
    report = {'status':'passed', 'protocol':'v187', 'source_states':len(old), 'retained_states':len(rows),
        'vocabulary_excluded':len(excluded), 'splits':source_manifest['split_records'],
        'games':source_manifest['split_games'],
        'changed_candidate_states':sum(r['candidate_orders'] for r in changes),
        'changed_opponent_states':sum(r['opponent_orders'] for r in changes),
        'changed_any_states':sum(r['candidate_orders'] or r['opponent_orders'] for r in changes),
        'changes':changes, 'old_rewards_reused':False, 'all_other_row_fields_unchanged':True,
        'whole_game_split_unchanged':True, 'training_hyperparameters_unchanged':True,
        'fresh_optimizer':True, 'independent_acceptance':False, 'S2_accepted':False}
    write(STAGE/'preflight.json', report)
    write(OUT.with_suffix('.receipt.json'), {'manifest_sha256':sha(OUT/'package-manifest.json'),
        'base_manifest_sha256':sha(BASE/'package-manifest.json'), 'files':len(manifest['sha256']),
        'overlay_sha256':sha(archive), 'overlay_bytes':archive.stat().st_size, 'changed_files':changed})
    print(json.dumps({k:v for k,v in report.items() if k!='changes'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
