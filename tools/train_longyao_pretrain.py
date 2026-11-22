"""GPU auxiliary pretraining on human Long Yao board orders, with grouped eval."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from yixian.memory import Memory
from yixian.order_data import SCOPE, teacher_batch, informative_steps, validate_splits
from yixian.order_model import BoardOrderPolicy, reconstruction_loss
from yixian.research import contract_digest


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    temporary = path.with_suffix(path.suffix+'.part')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    temporary.replace(path)


def load_split(directory, split, manifest, mapping):
    path = directory/f'{split}.jsonl'
    if sha(path) != manifest['split_sha256'][split]:
        raise ValueError(f'{split} data hash mismatch')
    records = [json.loads(line) for line in path.open(encoding='utf-8')]
    validate_splits(records)
    if any(row['split'] != split for row in records):
        raise ValueError('A record is in the wrong split file')
    return records, [[mapping[card] for card in row['board']] for row in records]


def tensor_batch(batch, device):
    return {key:torch.as_tensor(value, device=device) for key,value in batch.items()}


def evaluate(model, boards, position_counts, *, seed, batch_size, device):
    """Fixed teacher prefixes; model/frequency/random see identical decisions."""
    rng = np.random.default_rng(seed)
    cases = [(board,step) for board in boards for step in informative_steps(board)]
    totals = Counter()
    model.eval()
    with torch.inference_mode():
        for start in range(0,len(cases),batch_size):
            part = cases[start:start+batch_size]
            batch = teacher_batch([row[0] for row in part], rng, steps=[row[1] for row in part])
            values = tensor_batch(batch,device)
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=device.type=='cuda'):
                logits = model(values['candidates'],values['prefix'],values['available'])
            losses = reconstruction_loss(logits,values['targets'])
            correct = values['targets'].gather(1,logits.argmax(dim=1,keepdim=True)).float()
            totals['nll'] += losses.sum().item()
            totals['correct'] += correct.sum().item()
            for index,(_,step) in enumerate(part):
                legal = batch['available'][index]
                target = batch['targets'][index]
                probability = float(target.sum()/legal.sum())
                totals['random_nll'] -= float(np.log(probability))
                totals['random_correct'] += probability
                scores = position_counts[step,batch['candidates'][index]] * legal
                totals['frequency_nll'] -= float(np.log(scores[target].sum()/scores.sum()))
                totals['frequency_correct'] += int(target[int(scores.argmax())])
            totals['decisions'] += len(part)
    count = totals['decisions']
    if not count:
        raise ValueError('Evaluation has no informative ordering choices')
    return {'boards':len(boards),'informative_decisions':count,
            'nll':totals['nll']/count,'next_card_accuracy':totals['correct']/count,
            'random_nll':totals['random_nll']/count,'random_accuracy':totals['random_correct']/count,
            'position_frequency_nll':totals['frequency_nll']/count,
            'position_frequency_accuracy':totals['frequency_correct']/count,
            'metric_scope':'teacher_prefix_reconstruction_not_game_win_rate'}


def train(args):
    if args.out.exists():
        raise FileExistsError('Use a new run directory; previous experiments are preserved')
    config = json.loads(args.config.read_text())
    manifest = json.loads((args.data/'manifest.json').read_text())
    if config['scope'] != SCOPE or manifest['scope'] != SCOPE or config.get('full_match_training') is not False:
        raise ValueError('Unsupported training scope')
    settings = config['train']
    seeds = [settings[name] for name in ('seed','validation_seed','test_seed')]
    if len(set(seeds)) != 3:
        raise ValueError('Training and evaluation seeds must be distinct')
    if args.device == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA was requested but is unavailable')
    device = torch.device(args.device)
    torch.set_num_threads(settings['cpu_threads'])
    torch.manual_seed(settings['seed'])
    rng = np.random.default_rng(settings['seed'])
    mapping = {identifier:index+1 for index,identifier in enumerate(manifest['vocabulary'])}
    train_rows, train_boards = load_split(args.data,'train',manifest,mapping)
    val_rows, val_boards = load_split(args.data,'validation',manifest,mapping)
    validate_splits(train_rows+val_rows)
    if not train_boards or not val_boards:
        raise ValueError('Training and validation data are required')
    positions = np.ones((8,len(mapping)+1),dtype=np.float64)
    for board in train_boards:
        for step,card in enumerate(board):
            positions[step,card] += 1
    model = BoardOrderPolicy(len(mapping)+1,**config['model']).to(device)
    optimizer = torch.optim.AdamW(model.parameters(),lr=settings['learning_rate'],weight_decay=settings['weight_decay'])
    scaler = torch.amp.GradScaler('cuda',enabled=device.type=='cuda',init_scale=1024)
    contract = {'scope':SCOPE,'rules_version':manifest['rules_version'],
        'dataset_manifest_sha256':sha(args.data/'manifest.json'),
        'split_sha256':manifest['split_sha256'],'model':config['model'],
        'vocabulary_sha256':hashlib.sha256(json.dumps(manifest['vocabulary']).encode()).hexdigest(),
        'source_sha256':{name:sha(ROOT/name) for name in ['yixian/order_data.py','yixian/order_model.py','tools/train_longyao_pretrain.py']},
        'observation':'shuffled owned-board bag, constructed prefix, remaining occurrence mask',
        'action':'one of eight candidate occurrences; matching duplicate copies marginalized',
        'full_match_environment':False,'current_server_verified':False,'battle_labels_used':False}
    digest = contract_digest(contract)
    args.out.mkdir(parents=True)
    write_json(args.out/'config.json',config)
    write_json(args.out/'contract.json',contract)
    memory = Memory(ROOT/'runs/research.sqlite')
    experiment = memory.register_experiment(config,contract)
    memory.record_experiment(experiment,'running',{'run_dir':str(args.out),'device':str(device)})
    started = time.monotonic()
    parameter_count = sum(p.numel() for p in model.parameters())
    status = {'status':'running','experiment_id':experiment,'scope':SCOPE,'device':str(device),
              'parameter_count':parameter_count,'training_boards':len(train_boards),
              'validation_boards':len(val_boards),'split_summary':manifest['split_summary'],
              'contract_digest':digest,'full_match_training':False,'step':0}

    def emit(values):
        status.update(values)
        status['elapsed_seconds'] = time.monotonic()-started
        status['updated_at_utc'] = datetime.now(timezone.utc).isoformat()
        write_json(args.out/'status.json',status)
        with (args.out/'metrics.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(status,allow_nan=False)+'\n')
        print(json.dumps(status,allow_nan=False),flush=True)

    def save(step):
        destination = args.out/f'checkpoint-{step:06d}.pt'
        if destination.exists():
            raise FileExistsError(destination)
        temporary = destination.with_suffix('.part')
        packet = {'model':model.state_dict(),'optimizer':optimizer.state_dict(),'scaler':scaler.state_dict(),
                  'step':step,'config':config,'contract':contract,'contract_digest':digest,
                  'vocabulary':manifest['vocabulary'],'numpy_rng_state':rng.bit_generator.state,
                  'torch_rng_state':torch.get_rng_state(),
                  'cuda_rng_state':torch.cuda.get_rng_state_all() if device.type=='cuda' else []}
        torch.save(packet,temporary)
        temporary.replace(destination)
        return destination

    try:
        initial = evaluate(model,val_boards,positions,seed=settings['validation_seed'],
                           batch_size=settings['evaluation_batch_size'],device=device)
        best_loss, best_step, stale = initial['nll'], 0, 0
        best_path = save(0)
        write_json(args.out/'best.json',{'step':0,'path':str(best_path),'validation_nll':best_loss})
        emit({'validation':initial,'checkpoint':str(best_path),'best_step':0,'optimizer_updates':0})
        losses, optimizer_updates, skipped_updates = [], 0, 0
        stop_reason = 'maximum_updates'
        for step in range(1,settings['max_updates']+1):
            model.train()
            indices = rng.integers(0,len(train_boards),size=settings['batch_size'])
            values = tensor_batch(teacher_batch([train_boards[int(i)] for i in indices],rng),device)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type,dtype=torch.float16,enabled=device.type=='cuda'):
                logits = model(values['candidates'],values['prefix'],values['available'])
                loss = reconstruction_loss(logits,values['targets']).mean()
            if not torch.isfinite(loss):
                raise RuntimeError('Non-finite training loss')
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(),settings['max_grad_norm'])
            scale_before = scaler.get_scale()
            scaler.step(optimizer)
            scaler.update()
            if scaler.get_scale() < scale_before:
                skipped_updates += 1
            else:
                optimizer_updates += 1
            losses.append(float(loss.detach().cpu()))
            timed_out = time.monotonic()-started >= settings['max_minutes']*60
            if step % settings['validation_interval'] == 0 or step == settings['max_updates'] or timed_out:
                metrics = evaluate(model,val_boards,positions,seed=settings['validation_seed'],
                                   batch_size=settings['evaluation_batch_size'],device=device)
                checkpoint = save(step)
                if metrics['nll'] < best_loss-settings['minimum_improvement']:
                    best_loss,best_step,best_path,stale = metrics['nll'],step,checkpoint,0
                    write_json(args.out/'best.json',{'step':best_step,'path':str(best_path),'validation_nll':best_loss})
                else:
                    stale += 1
                emit({'step':step,'train_nll':float(np.mean(losses)),'validation':metrics,
                      'checkpoint':str(checkpoint),'best_step':best_step,'optimizer_updates':optimizer_updates,
                      'skipped_fp16_updates':skipped_updates,
                      'peak_allocated_mib':torch.cuda.max_memory_allocated()/2**20 if device.type=='cuda' else None})
                losses.clear()
                if stale >= settings['early_stopping_patience']:
                    stop_reason='validation_early_stopping'
                    break
                if timed_out:
                    stop_reason='pilot_time_limit'
                    break
        selected = torch.load(best_path,map_location=device,weights_only=True)
        if selected['contract_digest'] != digest:
            raise ValueError('Checkpoint contract mismatch')
        model.load_state_dict(selected['model'])
        # Test labels are evaluated only after the validation-selected checkpoint
        # has been frozen. The test result never changes the selected checkpoint.
        test_rows,test_boards = load_split(args.data,'test',manifest,mapping)
        validate_splits(train_rows+val_rows+test_rows)
        test_metrics = evaluate(model,test_boards,positions,seed=settings['test_seed'],
                                batch_size=settings['evaluation_batch_size'],device=device)
        emit({'status':'completed','stop_reason':stop_reason,'selected_checkpoint':str(best_path),
              'test':test_metrics,'test_used_for_selection':False,
              'game_strength_evaluated':False,'full_match_training':False})
        write_json(args.out/'report.json',status)
        memory.record_experiment(experiment,'completed',{'report':str(args.out/'report.json'),
            'scope':SCOPE,'selected_checkpoint':str(best_path),'game_strength_evaluated':False})
    except BaseException as error:
        emit({'status':'failed','error':str(error)})
        memory.record_experiment(experiment,'failed',{'error':str(error),'run_dir':str(args.out)})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--config',type=Path,default=ROOT/'configs/longyao_pretrain.json')
    parser.add_argument('--device',choices=['cuda','cpu'],default='cuda')
    train(parser.parse_args())


if __name__ == '__main__':
    main()
