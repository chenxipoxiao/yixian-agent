"""Frozen single-battle reward search followed by GPU proposal distillation.

One process owns a project-wide GPU lock. Search uses persistent CPU workers;
only the distiller uses CUDA. Partial searches/checkpoints survive interruptions.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter,defaultdict
from datetime import datetime,timezone
import argparse,hashlib,json,os,queue,subprocess,sys,time,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from yixian.battle_subset_v185 import SCOPE,digest,battle_input,summarize_matrix,policy_observation

def read(p):return json.loads(Path(p).read_text('utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,value):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    q=p.with_suffix(p.suffix+'.part');q.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8');q.replace(p)

class Worker:
    def __init__(self,log):
        self.error=log.open('a',encoding='utf8')
        self.p=subprocess.Popen(['node','--experimental-default-type=module',str(ROOT/'tools/battle_subset_worker_v185r3.mjs')],
            cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.error,text=True,encoding='utf8',bufsize=1)
    def run(self,battles):
        self.p.stdin.write(json.dumps(battles,ensure_ascii=False,separators=(',',':'))+'\n');self.p.stdin.flush()
        line=self.p.stdout.readline()
        if not line:raise RuntimeError('Engine worker exited; inspect retained stderr')
        result=json.loads(line)
        if not isinstance(result,list) or len(result)!=len(battles):raise ValueError(result)
        return result
    def close(self):
        self.p.stdin.close();self.p.wait(timeout=30);self.error.close()

def verify(package):
    manifest=read(package)
    for name,expected in manifest['sha256'].items():
        p=(ROOT/name).resolve()
        if not p.is_relative_to(ROOT) or sha(p)!=expected:raise ValueError('Frozen file changed: '+name)
    return manifest

def labels(rows,out,workers,deadline,emit):
    directory=out/'search';directory.mkdir(exist_ok=True)
    pool=queue.Queue();all_workers=[Worker(out/f'engine-worker-{i}.stderr') for i in range(workers)]
    for w in all_workers:pool.put(w)
    def one(row):
        p=directory/(digest(row['id'])+'.json')
        if p.exists():
            old=read(p)
            if old['start_digest']!=digest(row):raise ValueError('Search continuation input changed')
            return old
        if time.monotonic()>deadline:raise TimeoutError('Search segment time limit; resume cached states')
        w=pool.get()
        try:
            base=dict(row['battle']);base['include_trace']=False
            baseline=w.run([base])[0]
            if any(baseline.get(k)!=v for k,v in row['baseline_check'].items()):
                raise ValueError('Baseline no longer reproduces frozen calibrated terminal')
            inputs=[battle_input(row,a,b) for a in row['candidate_orders'] for b in row['opponent_orders']]
            results=w.run(inputs)
            result={'id':row['id'],'start_digest':digest(row),'simulations':len(inputs)+1,'results':results}
            try:
                matrix,values=summarize_matrix(results,row,len(row['candidate_orders']))
                result.update(status='admitted',matrix=matrix,utilities=values)
            except ValueError as e:
                # Whole-state rejection, never selectively discard weak actions.
                result.update(status='excluded',reason=str(e),failure_counts=dict(Counter(
                    r.get('reason','randomness' if r.get('used_randomness') else 'truncated')
                    for r in results if r.get('unresolved') or r.get('used_randomness') or not r.get('terminated'))))
            write(p,result);return result
        finally:pool.put(w)
    results=[]
    try:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for result in executor.map(one,rows):
                results.append(result)
                if len(results)%20==0 or len(results)==len(rows):
                    emit(phase='search',states_done=len(results),states_total=len(rows),
                         admitted=sum(r['status']=='admitted' for r in results))
    finally:
        for w in all_workers:w.close()
    records=[]
    for row,result in zip(rows,results,strict=True):
        if result['status']!='admitted':continue
        records.append({'id':row['id'],'game_id':row['game_id'],'split':row['split'],
            'own_cards':policy_observation(row)['owned_cards'],'candidate_orders':row['candidate_orders'],
            'utilities':result['utilities'],'oracle_gain':max(result['utilities'])-min(result['utilities'])})
    write(out/'reward-records.json',records)
    write(out/'search-summary.json',{'states':len(rows),'admitted':len(records),'excluded':len(rows)-len(records),
        'split_records':dict(Counter(r['split'] for r in records)),
        'informative_states':sum(r['oracle_gain']>1e-9 for r in records),
        'simulations':sum(r['simulations'] for r in results),
        'excluded_reasons':dict(Counter(r.get('reason') for r in results if r['status']!='admitted')),
        'reward_records_sha256':sha(out/'reward-records.json'),'engine':'v183r2',
        'fixed_same_opponent_panel_for_every_candidate':True,'randomness_rewards_allowed':False,
        'future_replay_continuation':False,'S2_accepted':False})
    return records

def train(records,config,out,deadline,emit,resume):
    import numpy as np
    import torch
    from yixian.tactical_checkpoint import load_tactical_checkpoint
    from yixian.tactical_rules import TacticalCatalogue
    from yixian.order_data import teacher_batch
    from yixian.order_model import reconstruction_loss
    if not torch.cuda.is_available():raise RuntimeError('T4 required')
    torch.set_num_threads(4);torch.manual_seed(config['seed']);np_rng=np.random.default_rng(config['seed'])
    torch.backends.cuda.matmul.allow_tf32=False
    catalogue=TacticalCatalogue.load(ROOT/config['card_table'],rules_version='001.0008.0005',expected_sha256=config['card_table_sha256'])
    model,metadata=load_tactical_checkpoint(ROOT/config['warm_start'],root=ROOT,
        expected_sha256=config['warm_start_sha256'],catalogue=catalogue,device='cuda')
    vocabulary=metadata['vocabulary'];mapping={c:i+1 for i,c in enumerate(vocabulary)}
    def tokens(order):return [mapping[c] for c in order]
    groups={s:defaultdict(list) for s in ['train','validation']}
    for r in records:
        assert all(c in mapping for c in r['own_cards'])
        groups[r['split']][r['game_id']].append(r)
    if set(groups['train'])&set(groups['validation']):raise ValueError('Whole-game split leak')
    if min(map(len,groups.values()))<8:raise ValueError('Insufficient admitted development games')
    training=[r for game in groups['train'].values() for r in game if r['oracle_gain']>1e-9]
    validation=[r for game in groups['validation'].values() for r in game]
    if len(training)<16:raise ValueError('Insufficient informative training states')
    train_games=defaultdict(list)
    for r in training:train_games[r['game_id']].append(r)
    game_ids=sorted(train_games)
    optimizer=torch.optim.AdamW(model.parameters(),lr=config['learning_rate'],weight_decay=.01)
    scaler=torch.amp.GradScaler('cuda',init_scale=1024)
    contract={'scope':SCOPE,'engine_package_sha256':sha(ROOT/'package-manifest.json'),
        'reward_records_sha256':sha(out/'reward-records.json'),'config_digest':digest(config),
        'policy_input':'owned multiset plus numerical card metadata and own generated prefix only',
        'selection':'validation mean of source-game mean utility, then validation oracle NLL',
        'warm_start':metadata,'warm_start_is_exact_resume':False,'full_match_training':False,'S2_accepted':False,
        'test_opened':False,'inference_action_space':'12 frozen multiset-only candidates; max sequence likelihood',
        'numeric_features_sha256':catalogue.fingerprint}
    write(out/'training-contract.json',contract)

    def evaluate():
        model.eval();flat=[];spans=[];total=0
        for row in validation:
            spans.append((total,total+len(row['candidate_orders'])));total+=len(row['candidate_orders'])
            flat.extend(tokens(o) for o in row['candidate_orders'])
        scores=[]
        with torch.inference_mode(),torch.autocast('cuda',dtype=torch.float16):
            for offset in range(0,len(flat),config['eval_batch_size']):
                batch=flat[offset:offset+config['eval_batch_size']];n=len(batch)
                bag=torch.zeros((n,8),dtype=torch.long,device='cuda');prefix=torch.zeros_like(bag)
                for i,board in enumerate(batch):bag[i,:len(board)]=torch.tensor(sorted(board),device='cuda')
                available=bag.ne(0);ll=torch.zeros(n,device='cuda')
                for step in range(8):
                    active=torch.tensor([step<len(b) for b in batch],device='cuda');idx=active.nonzero().flatten()
                    if not len(idx):break
                    logits=model(bag[idx],prefix[idx],available[idx])
                    wanted=torch.tensor([batch[i][step] for i in idx.tolist()],device='cuda')
                    target=available[idx]&bag[idx].eq(wanted[:,None]);loss=reconstruction_loss(logits,target)
                    ll[idx]-=loss
                    prefix[idx,step]=wanted
                    chosen=target.long().argmax(1);available[idx,chosen]=False
                scores.extend(ll.float().cpu().tolist())
        values=defaultdict(list);nll=[];selected=[];oracle=defaultdict(list)
        for row,(a,b) in zip(validation,spans):
            choice=max(range(b-a),key=lambda i:scores[a+i]);utility=row['utilities'][choice]
            values[row['game_id']].append(utility);oracle[row['game_id']].append(max(row['utilities']))
            best=max(range(b-a),key=lambda i:row['utilities'][i]);nll.append(-scores[a+best]/len(row['own_cards']))
            selected.append({'id':row['id'],'choice':choice,'utility':utility})
        game_means={g:sum(v)/len(v) for g,v in values.items()}
        return {'game_mean_utility':sum(game_means.values())/len(game_means),'oracle_nll':float(np.mean(nll)),
                'games':len(values),'states':len(validation),'game_means':game_means,'selected':selected}

    best=None;best_step=0;start_step=0;updates=0;skipped=0;stale=0
    def save(step,metrics):
        p=out/f'checkpoint-{step:06d}.pt'
        packet={'model':model.state_dict(),'optimizer':optimizer.state_dict(),'scaler':scaler.state_dict(),
            'step':step,'contract':contract,'vocabulary':vocabulary,'config':config,
            'numpy_rng':np_rng.bit_generator.state,'torch_rng':torch.get_rng_state(),
            'cuda_rng':torch.cuda.get_rng_state_all(),'best':best,'best_step':best_step,
            'updates':updates,'skipped':skipped,'stale':stale,'validation':metrics,
            'resume_state_available':True}
        if p.exists():raise FileExistsError(p)
        q=p.with_suffix('.part');torch.save(packet,q);q.replace(p)
        write(out/'resume.json',{'checkpoint':p.name,'sha256':sha(p)})
        return p
    if resume and (out/'resume.json').exists():
        receipt=read(out/'resume.json');p=out/receipt['checkpoint'];assert sha(p)==receipt['sha256']
        packet=torch.load(p,map_location='cpu',weights_only=True)
        if packet['contract']!=contract:raise ValueError('Resume contract changed')
        model.load_state_dict(packet['model']);optimizer.load_state_dict(packet['optimizer']);scaler.load_state_dict(packet['scaler'])
        np_rng.bit_generator.state=packet['numpy_rng'];torch.set_rng_state(packet['torch_rng']);torch.cuda.set_rng_state_all(packet['cuda_rng'])
        start_step=packet['step'];best=packet['best'];best_step=packet['best_step'];updates=packet['updates'];skipped=packet['skipped'];stale=packet['stale']
    else:
        best=evaluate();save(0,best);write(out/'baseline-validation.json',best)
        emit(phase='training',step=0,validation_utility=best['game_mean_utility'],best_step=0)
    losses=[];stop='maximum_updates'
    for step in range(start_step+1,config['max_updates']+1):
        if time.monotonic()>deadline:
            stop='segment_time_limit';break
        boards=[]
        for _ in range(config['batch_size']):
            game=game_ids[int(np_rng.integers(len(game_ids)))];choices=train_games[game]
            row=choices[int(np_rng.integers(len(choices)))];maximum=max(row['utilities'])
            top=[i for i,v in enumerate(row['utilities']) if v>=maximum-1e-10]
            boards.append(tokens(row['candidate_orders'][int(np_rng.choice(top))]))
        batch=teacher_batch(boards,np_rng);values={k:torch.as_tensor(v,device='cuda') for k,v in batch.items()}
        model.train();optimizer.zero_grad(set_to_none=True)
        with torch.autocast('cuda',dtype=torch.float16):
            loss=reconstruction_loss(model(values['candidates'],values['prefix'],values['available']),values['targets']).mean()
        if not torch.isfinite(loss):raise RuntimeError('Non-finite loss')
        scaler.scale(loss).backward();scaler.unscale_(optimizer);torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
        old_scale=scaler.get_scale();scaler.step(optimizer);scaler.update()
        skipped+=int(scaler.get_scale()<old_scale);updates+=int(scaler.get_scale()>=old_scale);losses.append(float(loss.detach().cpu()))
        if step%config['validation_interval']==0 or step==config['max_updates'] or time.monotonic()>deadline-90:
            metrics=evaluate();score=(metrics['game_mean_utility'],-metrics['oracle_nll']);old=(best['game_mean_utility'],-best['oracle_nll'])
            if score>old:best=metrics;best_step=step;stale=0
            else:stale+=1
            save(step,metrics)
            emit(phase='training',step=step,optimizer_updates=updates,fp16_skips=skipped,train_nll=float(np.mean(losses)),
                validation_utility=metrics['game_mean_utility'],best_step=best_step,
                peak_gpu_mib=torch.cuda.max_memory_allocated()/2**20)
            losses=[]
            if time.monotonic()>deadline-90:stop='segment_time_limit';break
            if stale>=config['patience']:stop='validation_early_stop';break
    if stop=='segment_time_limit':
        emit(status='segment_complete',phase='training',stop_reason=stop);return
    selected=torch.load(out/f'checkpoint-{best_step:06d}.pt',map_location='cpu',weights_only=True)
    torch.save({k:selected[k] for k in ['model','contract','config','vocabulary','step']},out/'selected-policy.pt')
    write(out/'selected-validation.json',best)
    baseline=read(out/'baseline-validation.json')
    diffs=np.array([best['game_means'][g]-baseline['game_means'][g] for g in sorted(best['game_means'])])
    bootstrap=np.random.default_rng(config['bootstrap_seed']);ci=np.quantile([float(bootstrap.choice(diffs,len(diffs),replace=True).mean()) for _ in range(2000)],[.025,.975]).tolist()
    summary={'scope':SCOPE,'selected_step':best_step,'updates':updates,'stop_reason':stop,
        'baseline_validation_utility':baseline['game_mean_utility'],'selected_validation_utility':best['game_mean_utility'],
        'paired_validation_gain':float(diffs.mean()),'descriptive_source_game_bootstrap_95':ci,
        'validation_games':len(groups['validation']),'training_games':len(groups['train']),
        'training_states':sum(map(len,groups['train'].values())),'informative_training_states':len(training),
        'validation_states':len(validation),'selected_policy_sha256':sha(out/'selected-policy.pt'),
        'model_selection_uses_validation':True,'independent_acceptance':False,'battle_proposal_trained':True,
        'opponent_probability_trained':False,'full_match_training':False,'S2_accepted':False,
        'strength_claim':'frozen-engine, finite-candidate, three scripted reactive opponent orders only'}
    write(out/'result-summary.json',summary);emit(status='completed',phase='complete',**summary)

def main(args):
    started=time.monotonic();args.out.mkdir(parents=True,exist_ok=args.resume)
    cfg=read(ROOT/'run-config.json');package=verify(ROOT/'package-manifest.json')
    deadline=started+cfg['segment_seconds'];status={}
    def emit(**values):
        status.update(values);status.update(updated_at_utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-started)
        write(args.out/'status.json',status)
        with (args.out/'metrics.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(status,ensure_ascii=False)+'\n')
        print(json.dumps({k:v for k,v in status.items() if k!='selected'},ensure_ascii=False),flush=True)
    # This Linux advisory lock is common to all v185 runs; the live GPU/process
    # check also catches earlier trainers which predate the lock convention.
    import fcntl
    lock=Path(cfg['project_root'])/'runs/tactical-gpu.lock';lock.parent.mkdir(exist_ok=True)
    with lock.open('a') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        gpu=subprocess.run(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],capture_output=True,text=True,check=True)
        if gpu.stdout.strip():raise RuntimeError('GPU already has a compute process')
        try:
            emit(status='running',phase='preflight',scope=SCOPE,package_files_verified=len(package['sha256']))
            rows=read(ROOT/'data/starts.json');records=labels(rows,args.out,cfg['workers'],deadline-300,emit)
            train(records,cfg,args.out,deadline,emit,args.resume)
            verify(ROOT/'package-manifest.json')
        except Exception:
            write(args.out/f'failure-{int(time.time())}.json',{'traceback':traceback.format_exc()})
            emit(status='failed');raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--resume',action='store_true')
    main(p.parse_args())
