"""Freeze all development selections before opening a one-use final holdout."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

from .order_data import SCOPE, validate_splits
from .pretrain_protocol import sha, validate_development_config


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def within(root, relative):
    root = Path(root).resolve()
    path = (root/relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Artifact path escapes the project')
    return path


def verify_sources(root, sources):
    if not sources:
        raise ValueError('Frozen sources are required')
    for name, digest in sources.items():
        if sha(within(root, name)) != digest:
            raise ValueError(f'Frozen source changed: {name}')


def validate_plan(root, plan):
    if plan.get('scope') != SCOPE or plan.get('test_policy') != 'once_after_all_three_runs_frozen':
        raise ValueError('Unsupported campaign scope or test policy')
    if len(plan.get('runs', [])) != 3:
        raise ValueError('Exactly three preregistered training runs are required')
    verify_sources(root, plan['source_sha256'])
    corpus = within(root, plan['data'])
    if sha(corpus/'manifest.json') != plan['manifest_sha256']:
        raise ValueError('Campaign corpus manifest changed')
    manifest = read_json(corpus/'manifest.json')
    if manifest.get('holdout_status') != 'new_group_disjoint_unevaluated' or manifest.get('test_model_evaluations') != 0:
        raise ValueError('Corpus was not frozen with a new unevaluated holdout')
    for role, minimum in plan['minimum_games'].items():
        if minimum < 1 or manifest['split_summary']['games'][role] < minimum:
            raise ValueError(f'Independent game minimum not met: {role}')
    configs = []
    for run in plan['runs']:
        path = within(root, run['config'])
        if sha(path) != run['config_sha256']:
            raise ValueError('Preregistered configuration changed')
        config = read_json(path)
        validate_development_config(config)
        if config['train']['seed'] != run['seed'] or config['corpus_manifest_sha256'] != plan['manifest_sha256']:
            raise ValueError('Run seed or dataset disagrees with campaign')
        configs.append(config)
    seeds = [config['train']['seed'] for config in configs]
    if len(set(seeds)) != 3 or len({run['run_dir'] for run in plan['runs']}) != 3:
        raise ValueError('Training seeds and output directories must be unique')
    common = None
    for config in configs:
        shared = json.loads(json.dumps(config))
        shared['train'].pop('seed')
        if common is not None and shared != common:
            raise ValueError('Only the training seed may vary between preregistered runs')
        common = shared
    development_seeds = set(seeds) | {configs[0]['train']['validation_seed'], configs[0]['train']['bootstrap_seed']}
    final_seeds = [plan['evaluation']['seed'], plan['evaluation']['bootstrap_seed']]
    if len(set(final_seeds)) != 2 or development_seeds.intersection(final_seeds):
        raise ValueError('Final-test random streams overlap development')
    return manifest, configs


def build_selection(root, plan_path):
    """Read only frozen configuration, development reports and checkpoints."""
    root, plan_path = Path(root).resolve(), Path(plan_path).resolve()
    plan = read_json(plan_path)
    manifest, configs = validate_plan(root, plan)
    runs = []
    for run, config in zip(plan['runs'], configs):
        directory = within(root, run['run_dir'])
        # Preregistration pins the original file bytes above. The learner saves
        # parsed JSON again, so Windows CRLF -> Linux LF is not a config change.
        if read_json(directory/'config.json') != config:
            raise ValueError('Executed configuration differs from preregistration')
        report = read_json(directory/'report.json')
        if report.get('status') != 'completed' or report.get('test_data_opened') is not False or report.get('test_model_evaluations') != 0:
            raise ValueError('All development runs must complete without test access')
        if report.get('optimizer_updates', 0) <= 0:
            raise ValueError('Development run has no optimizer updates')
        best = read_json(directory/'best.json')
        metrics = report['selected_validation']
        nll = metrics['pooled_metrics']['model']['teacher_nll']
        if not math.isfinite(nll) or nll < -1e-6 or abs(nll-best['validation_nll']) > 1e-5:
            raise ValueError('Selected validation metric disagrees with saved selection')
        if report['selected_step'] != best['step']:
            raise ValueError('Selected validation step disagrees with saved selection')
        if metrics['illegal_predictions'] or metrics['multiset_violations']:
            raise ValueError('Validation predictions violate legality')
        if any(nll >= metrics['pooled_metrics'][baseline]['teacher_nll'] for baseline in ('random', 'position_frequency')):
            raise ValueError('Validation NLL has not beaten both preregistered baselines')
        checkpoint = Path(report['selected_checkpoint']).resolve()
        if not checkpoint.is_relative_to(directory) or checkpoint != Path(best['path']).resolve():
            raise ValueError('Selected checkpoint is outside its run or differs from best.json')
        if sha(checkpoint) != report['selected_checkpoint_sha256']:
            raise ValueError('Selected checkpoint changed')
        runs.append({'seed': run['seed'], 'run_dir': run['run_dir'],
                     'checkpoint': checkpoint.relative_to(root).as_posix(),
                     'checkpoint_sha256': report['selected_checkpoint_sha256'],
                     'selected_step': report['selected_step'], 'validation_teacher_nll': nll,
                     'report_sha256': sha(directory/'report.json'),
                     'executed_config_sha256': sha(directory/'config.json'), 'config': config})
    champion = min(runs, key=lambda run: (run['validation_teacher_nll'], run['seed']))
    return {'schema_version': 1, 'scope': SCOPE, 'plan': plan_path.relative_to(root).as_posix(),
            'plan_sha256': sha(plan_path), 'data': plan['data'], 'manifest_sha256': plan['manifest_sha256'],
            'test_split_sha256': manifest['split_sha256']['test'], 'evaluation': plan['evaluation'],
            'runs': runs, 'champion_seed': champion['seed'],
            'champion_selection': 'minimum_validation_teacher_nll_then_seed',
            'test_used_for_selection': False, 'all_three_models_will_be_reported': True}


def freeze_selection(root, plan_path, destination):
    selection = build_selection(root, plan_path)
    with Path(destination).open('x', encoding='utf-8') as stream:
        json.dump(selection, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return selection


def validate_selection(root, path, expected_sha256):
    if sha(path) != expected_sha256:
        raise ValueError('Frozen selection hash mismatch')
    selection = read_json(path)
    if build_selection(root, within(root, selection['plan'])) != selection:
        raise ValueError('Plan, reports or frozen selections changed')
    return selection


def claim_and_load_test(root, selection, selection_sha256):
    """Claim before even hashing test bytes; failed attempts remain consumed.

    The key is the test-file hash, so changing a manifest or selection does not
    silently authorize a second evaluation of the same frozen test file.
    """
    root = Path(root).resolve()
    directory = within(root, selection['data'])
    if sha(directory/'manifest.json') != selection['manifest_sha256']:
        raise ValueError('Test corpus manifest changed')
    manifest = read_json(directory/'manifest.json')
    test_sha = manifest['split_sha256']['test']
    if test_sha != selection['test_split_sha256']:
        raise ValueError('Reserved test differs from frozen selection')
    uses = root/'runs/evaluations/holdout-use'
    uses.mkdir(parents=True, exist_ok=True)
    claim = uses/f'{test_sha}.json'
    payload = {'claimed_at_utc': datetime.now(timezone.utc).isoformat(),
               'selection_sha256': selection_sha256, 'test_split_sha256': test_sha,
               'manifest_sha256': selection['manifest_sha256'],
               'checkpoint_sha256': [run['checkpoint_sha256'] for run in selection['runs']],
               'status': 'claimed_before_test_read_do_not_delete_or_reuse'}
    # Exclusive creation is also the concurrent-run guard.
    with claim.open('x', encoding='utf-8') as stream:
        json.dump(payload, stream, indent=2)
        stream.write('\n')
    path = directory/'test.jsonl'
    if sha(path) != test_sha:
        raise ValueError('Test data hash mismatch; claim retained')
    with path.open(encoding='utf-8') as stream:
        rows = [json.loads(line) for line in stream]
    mapping = {card: index+1 for index, card in enumerate(manifest['vocabulary'])}
    for row in rows:
        board = row['board']
        if row['split'] != 'test' or row.get('season_mec') != 10 or not 3 <= len(board) <= 8 or len(set(board)) < 2:
            raise ValueError('Invalid final-test record')
        if any(type(card) is not int or card not in mapping for card in board):
            raise ValueError('Unknown final-test card')
        identity = hashlib.sha256(json.dumps([row['game_id'], board], separators=(',', ':')).encode()).hexdigest()
        if row['id'] != identity:
            raise ValueError('Final-test identity mismatch')
    summary = validate_splits(rows)
    for dimension in ('boards', 'games'):
        if summary[dimension].get('test', 0) != manifest['split_summary'][dimension]['test']:
            raise ValueError('Final-test counts disagree with manifest')
    return rows, [[mapping[card] for card in row['board']] for row in rows], claim
