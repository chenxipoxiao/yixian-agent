"""Train a v3 numeric-rule-aware tactical PROPOSAL using train/validation ONLY.

This separate entrypoint preserves the original v1 trainer and weight contract.
It cannot evaluate the final test set. A later frozen-selection evaluation must
use a different entrypoint after all planned development runs are complete.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from yixian.memory import Memory
from yixian.order_data import SCOPE, teacher_batch
from yixian.order_evaluation import evaluate_orders, position_counts, torch_scorer
from yixian.order_model import reconstruction_loss
from yixian.order_checkpoint import load_order_checkpoint
from yixian.tactical_model import TacticalProposalPolicy
from yixian.tactical_rules import TacticalCatalogue, digest as feature_digest
from yixian.tactical_checkpoint import SCOPE as TACTICAL_SCOPE
from yixian.pretrain_protocol import load_development_corpus, sha, validate_development_config
from yixian.research import contract_digest

SOURCE_FILES = ('yixian/order_data.py', 'yixian/order_model.py', 'yixian/order_evaluation.py',
                'yixian/pretrain_protocol.py', 'tools/train_longyao_development.py',
                'yixian/order_checkpoint.py', 'yixian/tactical_rules.py', 'yixian/tactical_model.py',
                'yixian/tactical_checkpoint.py', 'tools/train_tactical_proposal.py')


def write_json(path, value):
    temporary = path.with_suffix(path.suffix+'.part')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    temporary.replace(path)


def train(args):
    if args.out.exists():
        raise FileExistsError('Use a new directory; previous experiments are immutable')
    config = json.loads(args.config.read_text(encoding='utf-8'))
    validate_development_config(config)
    manifest, records, boards = load_development_corpus(args.data,
        expected_manifest_sha256=config['corpus_manifest_sha256'])
    settings = config['train']
    if config.get('model_scope') != TACTICAL_SCOPE:
        raise ValueError('Require explicit v3 proposal scope')
    catalogue = TacticalCatalogue.load(ROOT/config['card_table'],
        rules_version=manifest['rules_version'], expected_sha256=config['card_table_sha256'])
    if catalogue.fingerprint != config['card_rule_fingerprint']:
        raise ValueError('Card rule contract changed')
    if args.device == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA requested but unavailable')
    device = torch.device(args.device)
    torch.set_num_threads(settings['cpu_threads'])
    torch.manual_seed(settings['seed'])
    rng = np.random.default_rng(settings['seed'])
    vocabulary_size = len(manifest['vocabulary'])+1
    positions = position_counts(boards['train'], vocabulary_size)
    contract = {
        'schema_version': 3, 'scope': TACTICAL_SCOPE, 'corpus_scope': SCOPE,
        'rules_version': manifest['rules_version'],
        'card_rule_fingerprint': catalogue.fingerprint, 'card_contract': catalogue.contract,
        'vocabulary_digest': feature_digest(manifest['vocabulary']),
        'warm_start_sha256': config['warm_start_sha256'],
        'dataset_manifest_sha256': sha(args.data/'manifest.json'),
        'split_sha256': {role: manifest['split_sha256'][role] for role in ('train', 'validation')},
        'model': config['model'],
        'vocabulary_sha256': hashlib.sha256(json.dumps(manifest['vocabulary']).encode()).hexdigest(),
        'source_sha256': {name: sha(ROOT/name) for name in SOURCE_FILES},
        'observation': 'shuffled owned-board bag plus current numeric card metadata, generated prefix, occurrence mask',
        'action': 'one of eight candidate occurrences; matching duplicate copies marginalized',
        'test_data_opened': False, 'full_match_environment': False,
        'current_server_verified': False, 'battle_labels_used': False,
        'checkpoint_selection': 'validation_teacher_nll',
        'exact_resume_interface_available': False,
    }
    digest = contract_digest(contract)
    args.out.mkdir(parents=True)
    for name in SOURCE_FILES:
        target = args.out/'source'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, target)
    write_json(args.out/'config.json', config)
    write_json(args.out/'contract.json', contract)
    memory = Memory(ROOT/'runs/research.sqlite')
    experiment = memory.register_experiment(config, contract)
    memory.record_experiment(experiment, 'running', {'run_dir': str(args.out), 'device': str(device)})
    started = time.monotonic()
    status = {'status': 'running', 'experiment_id': experiment, 'scope': TACTICAL_SCOPE,
              'device': str(device), 'contract_digest': digest, 'step': 0,
              'test_data_opened': False, 'test_model_evaluations': 0,
              'training_boards': len(boards['train']), 'validation_boards': len(boards['validation']),
              'full_match_training': False, 'game_strength_evaluated': False}

    def emit(values):
        status.update(values)
        status.update(elapsed_seconds=time.monotonic()-started,
                      updated_at_utc=datetime.now(timezone.utc).isoformat())
        write_json(args.out/'status.json', status)
        with (args.out/'metrics.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(status, allow_nan=False)+'\n')
        print(json.dumps(status, allow_nan=False), flush=True)

    try:
        old_model, old_meta = load_order_checkpoint(ROOT/config['warm_start'], root=ROOT,
            expected_sha256=config['warm_start_sha256'], device='cpu')
        model = TacticalProposalPolicy(vocabulary_size, rule_features=catalogue.matrix(manifest['vocabulary']),
                                       **config['model'])
        transfer = model.warm_start(old_model, old_vocabulary=old_meta['vocabulary'], vocabulary=manifest['vocabulary'])
        write_json(args.out/'warm-start.json', transfer)
        del old_model
        model.to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=settings['learning_rate'],
                                     weight_decay=settings['weight_decay'])
        scaler = torch.amp.GradScaler('cuda', enabled=device.type == 'cuda', init_scale=1024)
        status['parameter_count'] = sum(p.numel() for p in model.parameters())

        def evaluate():
            return evaluate_orders(boards['validation'],
                [row['game_id'] for row in records['validation']],
                [row['id'] for row in records['validation']], torch_scorer(model, device), positions,
                seed=settings['validation_seed'], batch_size=settings['evaluation_batch_size'],
                bootstrap_seed=settings['bootstrap_seed'], bootstrap_samples=settings['bootstrap_samples'])

        def save(step):
            destination = args.out/f'checkpoint-{step:06d}.pt'
            if destination.exists():
                raise FileExistsError(destination)
            packet = {'model': model.state_dict(), 'optimizer': optimizer.state_dict(),
                      'scaler': scaler.state_dict(), 'step': step, 'config': config,
                      'contract': contract, 'contract_digest': digest, 'vocabulary': manifest['vocabulary'],
                      'numpy_rng_state': rng.bit_generator.state, 'torch_rng_state': torch.get_rng_state(),
                      'cuda_rng_state': torch.cuda.get_rng_state_all() if device.type == 'cuda' else [],
                      'exact_resume_interface_available': False}
            temporary = destination.with_suffix('.part')
            torch.save(packet, temporary)
            temporary.replace(destination)
            return destination

        initial, _ = evaluate()
        best_loss = initial['pooled_metrics']['model']['teacher_nll']
        best_step, stale = 0, 0
        best_path, best_metrics = save(0), initial
        write_json(args.out/'best.json', {'step': 0, 'path': str(best_path), 'validation_nll': best_loss})
        emit({'validation': initial, 'checkpoint': str(best_path), 'best_step': 0, 'optimizer_updates': 0})
        losses, optimizer_updates, skipped = [], 0, 0
        stop_reason = 'maximum_updates'
        for step in range(1, settings['max_updates']+1):
            if time.monotonic()-started >= settings['max_minutes']*60:
                stop_reason = 'development_time_limit'
                break
            model.train()
            indices = rng.integers(0, len(boards['train']), size=settings['batch_size'])
            batch = teacher_batch([boards['train'][int(i)] for i in indices], rng)
            values = {key: torch.as_tensor(value, device=device) for key, value in batch.items()}
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=device.type == 'cuda'):
                logits = model(values['candidates'], values['prefix'], values['available'])
                loss = reconstruction_loss(logits, values['targets']).mean()
            if not torch.isfinite(loss):
                raise RuntimeError('Non-finite training loss')
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), settings['max_grad_norm'])
            previous_scale = scaler.get_scale()
            scaler.step(optimizer)
            scaler.update()
            if scaler.get_scale() < previous_scale:
                skipped += 1
            else:
                optimizer_updates += 1
            losses.append(float(loss.detach().cpu()))
            timed_out = time.monotonic()-started >= settings['max_minutes']*60
            if step % settings['validation_interval'] == 0 or step == settings['max_updates'] or timed_out:
                metrics, _ = evaluate()
                checkpoint = save(step)
                nll = metrics['pooled_metrics']['model']['teacher_nll']
                if nll < best_loss-settings['minimum_improvement']:
                    best_loss, best_step, best_path, best_metrics, stale = nll, step, checkpoint, metrics, 0
                    write_json(args.out/'best.json', {'step': step, 'path': str(best_path), 'validation_nll': nll})
                else:
                    stale += 1
                emit({'step': step, 'train_nll': float(np.mean(losses)), 'validation': metrics,
                      'checkpoint': str(checkpoint), 'best_step': best_step,
                      'optimizer_updates': optimizer_updates, 'skipped_fp16_updates': skipped,
                      'peak_allocated_mib': torch.cuda.max_memory_allocated()/2**20 if device.type == 'cuda' else None})
                losses.clear()
                if stale >= settings['early_stopping_patience']:
                    stop_reason = 'validation_early_stopping'
                    break
                if timed_out:
                    stop_reason = 'development_time_limit'
                    break
        selected = torch.load(best_path, map_location=device, weights_only=True)
        if selected['contract_digest'] != digest:
            raise ValueError('Selected checkpoint contract mismatch')
        model.load_state_dict(selected['model'])
        selected_metrics, game_metrics = evaluate()
        # This recheck still uses validation only, including complete-board prefixes.
        if abs(selected_metrics['pooled_metrics']['model']['teacher_nll']-best_loss) > 1e-5:
            raise ValueError('Reloaded selected checkpoint changed validation NLL')
        write_json(args.out/'selected-validation-games.json', game_metrics)
        export = args.out/'selected-policy.pt'
        torch.save({key: selected[key] for key in ('model', 'step', 'config', 'contract', 'contract_digest', 'vocabulary')}, export)
        status.update(proposal_only=True, opponent_belief_trained=False,
                      rule_projection_norm=float(model.rule_projection.weight.norm().detach().cpu()),
                      inference_export=str(export), inference_export_sha256=sha(export),
                      final_test_pending=False, new_independent_test_required_before_acceptance=True)
        emit({'status': 'completed', 'stop_reason': stop_reason, 'selected_step': best_step,
              'selected_checkpoint': str(best_path), 'selected_checkpoint_sha256': sha(best_path),
              'selected_validation': selected_metrics, 'final_test_pending': False,
              'test_used_for_selection': False, 'optimizer_updates': optimizer_updates,
              'skipped_fp16_updates': skipped})
        write_json(args.out/'report.json', status)
        memory.record_experiment(experiment, 'completed', {'report': str(args.out/'report.json'),
            'selected_checkpoint': str(best_path), 'test_data_opened': False, 'game_strength_evaluated': False})
    except BaseException as error:
        emit({'status': 'failed', 'error': str(error)})
        memory.record_experiment(experiment, 'failed', {'error': str(error), 'run_dir': str(args.out)})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--device', choices=['cuda', 'cpu'], default='cuda')
    train(parser.parse_args())


if __name__ == '__main__':
    main()
