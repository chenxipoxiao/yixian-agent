"""One frozen, preregistered three-model evaluation; no test-based selection."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from yixian.holdout_protocol import claim_and_load_test, validate_selection, within
from yixian.memory import Memory
from yixian.order_checkpoint import load_order_checkpoint
from yixian.order_data import SCOPE, validate_splits
from yixian.order_evaluation import evaluate_orders, position_counts, torch_scorer
from yixian.pretrain_protocol import load_development_corpus


def write_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def evaluate(args):
    import torch
    if args.out.exists():
        raise FileExistsError('Preserve previous evaluations; use a new output directory')
    selection = validate_selection(ROOT, args.selection, args.selection_sha256)
    if args.device == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA requested but unavailable')
    device = torch.device(args.device)
    # Validate every checkpoint before consuming any test bytes.
    models = []
    for run in selection['runs']:
        model, metadata = load_order_checkpoint(within(ROOT, run['checkpoint']), root=ROOT,
            expected_sha256=run['checkpoint_sha256'], device='cpu', expected_config=run['config'],
            expected_manifest_sha256=selection['manifest_sha256'])
        if metadata['step'] != run['selected_step']:
            raise ValueError('Checkpoint step differs from frozen selection')
        models.append((model, metadata))
    manifest, development_rows, development_boards = load_development_corpus(within(ROOT, selection['data']),
        expected_manifest_sha256=selection['manifest_sha256'])
    for _, metadata in models:
        if metadata['vocabulary'] != manifest['vocabulary']:
            raise ValueError('Checkpoint vocabulary differs from corpus')
        if metadata['contract']['split_sha256'] != {key: manifest['split_sha256'][key] for key in ('train', 'validation')}:
            raise ValueError('Checkpoint development partitions differ from corpus')
    torch.set_num_threads(selection['runs'][0]['config']['train']['cpu_threads'])
    positions = position_counts(development_boards['train'], len(manifest['vocabulary'])+1)
    args.out.mkdir(parents=True)
    shutil.copyfile(args.selection, args.out/'selection.json')
    memory = Memory(ROOT/'runs/research.sqlite')
    experiment = memory.register_experiment(
        {'selection_sha256': args.selection_sha256, 'evaluation': selection['evaluation'], 'device': args.device},
        {'scope': SCOPE, 'dataset_manifest_sha256': selection['manifest_sha256'],
         'selection': selection, 'test_used_for_selection': False, 'game_strength_evaluated': False}, role='evaluation')
    memory.record_experiment(experiment, 'running', {'run_dir': str(args.out)}, role='evaluation')
    started, results = time.monotonic(), []
    try:
        rows, boards, claim = claim_and_load_test(ROOT, selection, args.selection_sha256)
        validate_splits(development_rows['train']+development_rows['validation']+rows)
        for run, (model, _) in zip(selection['runs'], models):
            model.to(device)
            metrics, games = evaluate_orders(boards, [row['game_id'] for row in rows],
                [row['id'] for row in rows], torch_scorer(model, device), positions,
                **selection['evaluation'])
            result = {'seed': run['seed'], 'checkpoint_sha256': run['checkpoint_sha256'], 'metrics': metrics}
            write_json(args.out/f"seed-{run['seed']}-games.json", games)
            write_json(args.out/f"seed-{run['seed']}-result.json", result)
            results.append(result)
            model.cpu()
        report = {'status': 'completed', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
                  'experiment_id': experiment, 'scope': SCOPE, 'elapsed_seconds': time.monotonic()-started,
                  'selection_sha256': args.selection_sha256, 'holdout_claim': str(claim),
                  'champion_seed': selection['champion_seed'], 'champion_selected_by': 'validation_only',
                  'models_evaluated': len(results), 'results': results, 'test_used_for_selection': False,
                  'full_match_training': False, 'game_strength_evaluated': False,
                  'metric_scope': 'recorded_order_reproduction_not_combat_strength'}
        write_json(args.out/'report.json', report)
        memory.record_experiment(experiment, 'completed', {'report': str(args.out/'report.json'),
            'holdout_claim': str(claim), 'models_evaluated': len(results)}, role='evaluation')
        print(json.dumps({'report': str(args.out/'report.json'), 'models_evaluated': len(results),
                          'champion_seed': selection['champion_seed'], 'game_strength_evaluated': False}))
    except BaseException as error:
        write_json(args.out/'failure.json', {'status': 'failed', 'error': str(error),
            'elapsed_seconds': time.monotonic()-started, 'completed_models': len(results),
            'holdout_claim_must_be_preserved': True, 'selection_sha256': args.selection_sha256})
        memory.record_experiment(experiment, 'failed', {'error': str(error), 'run_dir': str(args.out)}, role='evaluation')
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', type=Path, required=True)
    parser.add_argument('--selection-sha256', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--device', choices=['cuda', 'cpu'], default='cuda')
    evaluate(parser.parse_args())


if __name__ == '__main__':
    main()
