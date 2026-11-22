"""Vocabulary-gated training from a hash-checked, same-engine reward cache.

The failed r3 source and output stay immutable. This is a new experiment with
fresh optimizer state, not a resume of a completed optimizer checkpoint.
"""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import argparse, fcntl, json, subprocess, sys, time, traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.run_battle_subset_v185 import read, write, sha, verify, train, Worker
from yixian.battle_subset_v185 import SCOPE, digest, policy_observation, summarize_matrix, battle_input
from yixian.memory import Memory


def verified_records(config, out):
    import torch
    inherited = config['inherited_search']
    old_root = Path(inherited['release'])
    old_out = Path(inherited['run_dir'])
    if sha(old_root/'package-manifest.json') != inherited['package_sha256']:
        raise ValueError('Inherited engine package identity changed')
    old_manifest = read(old_root/'package-manifest.json')
    current_manifest = read(ROOT/'package-manifest.json')
    for name, expected in old_manifest['sha256'].items():
        source = (old_root/name).resolve()
        if not source.is_relative_to(old_root) or sha(source) != expected:
            raise ValueError('Inherited source changed: '+name)
        if name != 'run-config.json' and current_manifest['sha256'][name] != expected:
            raise ValueError('Reward engine source changed; cache is not transferable: '+name)
    if sha(old_out/'reward-records.json') != inherited['reward_records_sha256']:
        raise ValueError('Inherited labels changed')
    rows = read(ROOT/'data/starts.json')
    rebuilt = []; cached = {}; cache_hashes = {}; reasons = Counter()
    for row in rows:
        path = old_out/'search'/(digest(row['id'])+'.json')
        result = read(path); cache_hashes[path.name] = sha(path)
        if result['id'] != row['id'] or result['start_digest'] != digest(row):
            raise ValueError('Cached starting state changed')
        try:
            matrix, values = summarize_matrix(result['results'], row, len(row['candidate_orders']))
        except ValueError:
            if result['status'] != 'excluded':raise
            reasons.update(result.get('failure_counts',{})); continue
        if result['status'] != 'admitted' or matrix != result['matrix'] or values != result['utilities']:
            raise ValueError('Cached reward formula or panel changed')
        record = {'id':row['id'],'game_id':row['game_id'],'split':row['split'],
            'own_cards':policy_observation(row)['owned_cards'],'candidate_orders':row['candidate_orders'],
            'utilities':values,'oracle_gain':max(values)-min(values)}
        rebuilt.append(record); cached[row['id']] = result
    if rebuilt != read(old_out/'reward-records.json'):
        raise ValueError('Full reward reconstruction changed')
    packet = torch.load(ROOT/config['warm_start'],map_location='cpu',weights_only=True)
    vocabulary = set(packet['vocabulary']); kept = []; excluded = []
    for record in rebuilt:
        unknown = sorted(set(record['own_cards'])-vocabulary)
        if unknown:
            excluded.append({'id':record['id'],'split':record['split'],'raw_card_ids':unknown,
                             'reason':'outside_frozen_model_vocabulary'})
        else:kept.append(record)
    if {c for r in excluded for c in r['raw_card_ids']} != {0}:
        raise ValueError('Unexpected additional vocabulary gap')
    if len(kept)!=525 or len(excluded)!=42:
        raise ValueError('Predeclared vocabulary-gated cohort changed')
    # Re-execute fixed multiset-selected examples in the unchanged engine.
    kept_ids={r['id'] for r in kept}
    checks=sorted((r for r in rows if r['id'] in kept_ids),key=lambda r:digest(r['id']))[:8]
    worker=Worker(out/'cache-verification-engine.stderr'); replayed=0
    try:
        for row in checks:
            base=dict(row['battle']);base['include_trace']=False
            result=worker.run([base])[0]
            if any(result.get(k)!=v for k,v in row['baseline_check'].items()):
                raise ValueError('Inherited baseline terminal no longer reproduced')
            inputs=[battle_input(row,a,b) for a in row['candidate_orders'] for b in row['opponent_orders']]
            if worker.run(inputs)!=cached[row['id']]['results']:
                raise ValueError('Cached candidate outcomes no longer reproduced')
            replayed+=len(inputs)+1
    finally:worker.close()
    write(out/'cache-verification.json',{'status':'passed','source':inherited,'source_states_checked':len(rows),
          'source_labels_rebuilt':len(rebuilt),'cache_file_sha256':cache_hashes,'reexecuted_states':len(checks),
          'reexecuted_full_battles':replayed,'all_reexecuted_outputs_exact':True,
          'old_rules_reward_migration':False,'current_frozen_engine_identical':True,
          'excluded_battle_reasons':dict(reasons),'vocabulary_excluded':excluded})
    write(out/'reward-records.json',kept)
    write(out/'search-summary.json',{'source_states':len(rows),'battle_admitted':len(rebuilt),
          'battle_excluded':len(rows)-len(rebuilt),'vocabulary_excluded':len(excluded),'admitted':len(kept),
          'split_records':dict(Counter(r['split'] for r in kept)),
          'informative_states':sum(r['oracle_gain']>1e-9 for r in kept),
          'split_games':{s:len({r['game_id'] for r in kept if r['split']==s}) for s in ['train','validation']},
          'reward_records_sha256':sha(out/'reward-records.json'),'cached_labels_verified_before_reuse':True,
          'new_gpu_job_is_exact_resume':False,'no_card_removed_from_any_retained_multiset':True})
    return kept


def main(args):
    cfg=read(ROOT/'run-config.json');started=time.monotonic();deadline=started+cfg['segment_seconds']
    args.out.mkdir(parents=True,exist_ok=args.resume);status={}
    memory=Memory(Path(cfg['project_root'])/'runs/research.sqlite')
    if not args.resume:memory.record_experiment(args.experiment_id,'running',{'run_dir':str(args.out)},role='training')
    def emit(**values):
        status.update(values);status.update(updated_at_utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-started)
        write(args.out/'status.json',status)
        with (args.out/'metrics.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(status)+'\n')
        print(json.dumps(status),flush=True)
    lock=Path(cfg['project_root'])/'runs/tactical-gpu.lock'
    try:
        with lock.open('a') as handle:
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():
                raise RuntimeError('Another GPU process is active')
            manifest=verify(ROOT/'package-manifest.json')
            emit(status='running',phase='verified_cache_preflight',scope=SCOPE,package_files_verified=len(manifest['sha256']))
            records=verified_records(cfg,args.out)
            emit(phase='training_start',admitted_states=len(records))
            train(records,cfg,args.out,deadline,emit,args.resume)
            verify(ROOT/'package-manifest.json')
            if status['status']=='completed':memory.record_experiment(args.experiment_id,'completed',status,role='training')
            else:memory.append('finding','training',{'statement':'Restricted trainer saved a resumable segment','claim':'measured','evidence':[str(args.out/'status.json')]})
    except BaseException:
        failure={'traceback':traceback.format_exc(),'run_dir':str(args.out)}
        write(args.out/f'failure-{int(time.time())}.json',failure);emit(status='failed')
        memory.record_experiment(args.experiment_id,'failed',failure,role='training');raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--resume',action='store_true');p.add_argument('--experiment-id',required=True)
    main(p.parse_args())
