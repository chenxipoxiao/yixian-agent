"""Reproducible local research cycles, inspired by AutoTavern's evidence gates.

The shipped experiment is deliberately a synthetic deck-order curriculum. A
successful software cycle does not promote it to a current-season match agent.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import time
from typing import Callable
import uuid

from .curriculum import fingerprint, make_cases
from .environment import DeckOrderEnv
from .learning import PPOConfig, evaluate, load_checkpoint, train
from .memory import Memory
from .opponents import assert_disjoint_games, build_opponent_library, save_library
from .research import canonical_json, contract_digest, promotion_gate
from .worker import BattleWorker

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_FILES = (
    'yixian/environment.py', 'yixian/learning.py', 'yixian/worker.py',
    'yixian/simulator.py', 'yixian/curriculum.py', 'yixian/opponents.py',
    'yixian/pipeline.py', 'tools/yisim_bridge.mjs',
)


def write_json(path: Path, value):
    # Reject NaN and other values that cannot be faithfully fingerprinted.
    canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def runtime_contract(engine: dict, cases: dict) -> dict:
    import numpy as np
    return {**engine, 'scope': 'synthetic_legacy_deck_order_curriculum',
            'full_match_environment': False,
            'observation_schema': DeckOrderEnv.observation_schema,
            'observation_dim': DeckOrderEnv.obs_dim, 'action_dim': DeckOrderEnv.action_dim,
            'action_schema': 'select-unused-original-slot-v1',
            'shuffle_cards': True,
            'python_version': sys.version.split()[0], 'numpy_version': np.__version__,
            'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                              for name in CONTRACT_FILES},
            'case_sha256': {name: fingerprint(rows) for name, rows in cases.items()}}


def baseline_evaluate(env, seeds, policy='random'):
    """Only reads legal actions; no enemy state, future result, or seed inspection."""
    if policy not in ('random', 'slot_order'):
        raise ValueError('Unknown baseline policy')
    outcomes = []
    for seed in seeds:
        _, initial = env.reset(seed=seed)
        rng = random.Random(f'baseline-actions:{seed}')
        total = 0.0
        for _ in range(8):
            legal = env.legal_actions()
            action = rng.choice(legal) if policy == 'random' else legal[0]
            _, reward, done, truncated, info = env.step(action)
            total += reward
            if done or truncated:
                usable = done and not truncated and info.get('label_usable', True)
                result = {'seed': seed, 'case_id': initial.get('case_id'),
                          'status': 'terminated' if usable else 'excluded'}
                if usable:
                    result['reward'] = total
                outcomes.append(result)
                break
        else:
            outcomes.append({'seed': seed, 'case_id': initial.get('case_id'), 'status': 'step_limit'})
    rewards = [item['reward'] for item in outcomes if item['status'] == 'terminated']
    return {'policy': policy, 'episodes': len(seeds), 'completed': len(rewards),
            'excluded': len(seeds) - len(rewards),
            'mean_reward': sum(rewards) / len(rewards) if rewards else None,
            'win_fraction': sum(r > 0 for r in rewards) / len(rewards) if rewards else None,
            'outcomes': outcomes}


def paired_comparison(candidate, baseline):
    """Paired descriptive result; repeated seeds of a fixture are not iid games."""
    def keyed(report):
        result = {}
        for item in report['outcomes']:
            key = (item['seed'], item.get('case_id'))
            if key in result:
                raise ValueError('Repeated episode in evaluation report')
            result[key] = item
        return result
    left, right = keyed(candidate), keyed(baseline)
    if left.keys() != right.keys():
        raise ValueError('Paired evaluation must use the same cases and seeds')
    pairs = [(left[key]['reward'], right[key]['reward']) for key in left
             if left[key]['status'] == right[key]['status'] == 'terminated']
    differences = [a-b for a, b in pairs]
    return {'paired_episodes': len(pairs), 'excluded_pairs': len(left)-len(pairs),
            'mean_reward_delta': sum(differences)/len(pairs) if pairs else None,
            'better': sum(x > 0 for x in differences), 'same': sum(x == 0 for x in differences),
            'worse': sum(x < 0 for x in differences),
            'strength_claim': False,
            'limitation': 'Descriptive synthetic-fixture comparison; not independent live matches or statistical proof.'}


def _seed_schedule(config):
    count = config['evaluation_episodes']
    if type(count) is not int or count < 1:
        raise ValueError('evaluation_episodes must be positive')
    schedules = {}
    for split in ('validation', 'test'):
        base = config[f'{split}_seed_base']
        if type(base) is not int or base < 0:
            raise ValueError('Evaluation seed bases must be nonnegative integers')
        schedules[split] = list(range(base, base+count))
    if set(schedules['validation']) & set(schedules['test']):
        raise ValueError('Validation/test seed schedules overlap')
    return schedules


def _partitions(config, engine):
    cases = make_cases(config['case_count'], config['case_seed'])
    records = [dict(row, evidence='synthetic') for row in cases]
    library = build_opponent_library(records, engine, split_salt='deck-order-cpu-v1', fractions=(.6, .2, .2))
    partitions = {split: [row for row in library['records'] if row['split'] == split]
                  for split in ('train', 'validation', 'test')}
    if any(not rows for rows in partitions.values()):
        raise ValueError('Every partition needs fixtures; increase case_count')
    assert_disjoint_games(library['games_by_split'])
    return library, partitions


def _evaluate_suite(worker, model, contract, partitions, schedules):
    reports = {}
    for split in ('validation', 'test'):
        env = DeckOrderEnv(partitions[split], simulator=worker)
        candidate = evaluate(env, model, schedules[split], contract=contract)
        baselines = {policy: baseline_evaluate(env, schedules[split], policy)
                     for policy in ('random', 'slot_order')}
        reports[split] = {'candidate': candidate, 'baselines': baselines,
                          'comparison': {name: paired_comparison(candidate, report)
                                         for name, report in baselines.items()}}
    return reports


def run_cycle(config_path=ROOT / 'configs/curriculum.json', *, output_root=ROOT / 'runs',
              progress: Callable[[str], None] = print):
    """Execute tests -> freeze -> train -> held-out checks -> evidence-gated report."""
    config = json.loads(Path(config_path).read_text(encoding='utf-8-sig'))
    schedules = _seed_schedule(config)
    train_config = dict(config['train'], reserved_evaluation_seeds=schedules['validation']+schedules['test'])
    PPOConfig(**train_config).validate()
    output_root = Path(output_root).resolve()
    run_dir = output_root / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
    run_dir.mkdir(parents=True)
    memory = Memory(output_root / 'research.sqlite')
    if not memory.verify_integrity():
        raise ValueError('Research memory integrity check failed')
    write_json(run_dir / 'config.json', config)
    progress('检查环境与训练模块；保存本轮验证结果。')
    started = time.perf_counter()
    checked = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                             cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=180)
    (run_dir / 'tests.log').write_text(checked.stdout + checked.stderr, encoding='utf-8')
    if checked.returncode:
        memory.append('finding', 'environment', {'statement': 'The research cycle stopped because software tests failed.',
                      'claim': 'measured', 'evidence': [str(run_dir / 'tests.log')]})
        raise RuntimeError(f'Software validation failed; see {run_dir / "tests.log"}')
    experiment_id = None
    try:
        with BattleWorker() as worker:
            library, partitions = _partitions(config, worker.contract)
            contract = runtime_contract(worker.contract, partitions)
            digest = contract_digest(contract)
            save_library(library, run_dir / 'opponents.json')
            write_json(run_dir / 'cases.json', partitions)
            write_json(run_dir / 'contract.json', contract)
            experiment_id = memory.register_experiment(config, contract)
            memory.record_experiment(experiment_id, 'running', {'run_dir': str(run_dir)})
            progress('版本和数据划分已固定；开始本机 PPO 排牌课程。')
            checkpoint = run_dir / 'policy.npz'
            def on_update(stats):
                if stats['round'] == 1 or stats['round'] % 6 == 0 or stats['round'] == train_config['updates']:
                    progress(f"训练轮次 {stats['round']}/{train_config['updates']}；本轮有效对局 {stats['eligible_episodes']}。")
            trained = train(DeckOrderEnv(partitions['train'], simulator=worker), train_config,
                            contract, checkpoint, on_update=on_update)
            write_json(run_dir / 'training.json', trained)
            model = load_checkpoint(checkpoint, contract)
            progress('模型已保存并重新加载；在保留对局上比较随机与顺序排牌。')
            evaluations = _evaluate_suite(worker, model, contract, partitions, schedules)
            write_json(run_dir / 'evaluation.json', evaluations)
            decision = promotion_gate(contract, tests_passed=True, full_match_environment=False,
                                      training_ids=library['games_by_split']['train'],
                                      evaluation_ids=library['games_by_split']['validation']+library['games_by_split']['test'],
                                      candidate_contract_digest=model.contract_digest)
            observed_gains = {split: all(c['mean_reward_delta'] is not None and c['mean_reward_delta'] > 0
                                         and c['excluded_pairs'] == 0 for c in result['comparison'].values())
                              for split, result in evaluations.items()}
            report = {'schema_version': 1, 'experiment_id': experiment_id, 'run_dir': str(run_dir),
                      'scope': contract['scope'], 'full_match_agent': False, 'current_season_verified': False,
                      'contract_digest': digest, 'checkpoint': str(checkpoint),
                      'parameter_count': trained['parameter_count'],
                      'training_episodes': trained['episodes_trained'], 'training_excluded': trained['episodes_excluded'],
                      'fixtures': {name: len(rows) for name, rows in partitions.items()},
                      'elapsed_seconds': time.perf_counter()-started,
                      'gates': {
                          'G1_software': {'passed': True, 'artifact': str(run_dir / 'tests.log')},
                          'G2_contract': {'passed': True, 'digest': digest},
                          'G3_comparison': {'executed': True, 'observed_gain_over_both_baselines': observed_gains['validation']},
                          'G4_held_out': {'executed': True, 'observed_gain_over_both_baselines': observed_gains['test'],
                                          'test_not_used_for_training_or_selection': True},
                          'G5_real_game': {'passed': False, 'real_matches': 0}},
                      'full_match_promotion': dict(asdict(decision), blockers=list(decision.blockers)),
                      'metrics': {split: {'candidate_win_fraction': data['candidate']['win_fraction'],
                                         'baseline_win_fractions': {name: result['win_fraction'] for name, result in data['baselines'].items()},
                                         'episodes': data['candidate']['episodes'],
                                         'excluded': data['candidate']['excluded'], 'comparisons': data['comparison']}
                                  for split, data in evaluations.items()},
                      'next_required_work': [
                          'Calibrate current-season combat with independent real-game records.',
                          'Implement and verify complete draw/swap/merge/refine/ascend/fate/season/matchmaking/elimination rules.',
                          'Calibrate opponent distributions and train/evaluate complete matches.'],
                      'limitation': 'This run tests a training workflow on synthetic legacy battles; it cannot establish current-season playing strength.'}
            write_json(run_dir / 'report.json', report)
            memory.append('finding', 'evaluation', {'statement': 'Completed a synthetic deck-order PPO cycle; full-match promotion remains blocked.',
                          'claim': 'measured', 'evidence': [str(run_dir / 'report.json'), str(run_dir / 'evaluation.json')],
                          'experiment_id': experiment_id})
            write_json(output_root / 'latest.json', {'run_dir': str(run_dir), 'report': str(run_dir / 'report.json')})
            progress(f'实验完成，报告：{run_dir / "report.json"}')
            memory.record_experiment(experiment_id, 'completed', {'report': str(run_dir / 'report.json'),
                                     'full_match_ready': False}, role='lead')
            return report
    except BaseException as error:
        if experiment_id:
            try:
                if memory.experiment(experiment_id)['status'] in ('registered', 'running'):
                    memory.record_experiment(experiment_id, 'failed', {'error': f'{type(error).__name__}: {error}'}, role='lead')
            except Exception:
                # A second storage failure must not hide the original failure.
                pass
        raise


def arrange(run_dir, battle):
    """Apply a frozen curriculum model to one explicitly supplied offline battle."""
    run_dir = Path(run_dir).resolve()
    contract = json.loads((run_dir / 'contract.json').read_text(encoding='utf-8'))
    partitions = json.loads((run_dir / 'cases.json').read_text(encoding='utf-8'))
    with BattleWorker() as worker:
        current = runtime_contract(worker.contract, partitions)
        if contract_digest(current) != contract_digest(contract):
            raise ValueError('Runtime or fixture contract changed; use the original build or run a new experiment')
        model = load_checkpoint(run_dir / 'policy.npz', contract)
        env = DeckOrderEnv([battle], simulator=worker)
        observation, _ = env.reset(seed=battle['seed'])
        for _ in range(8):
            action, _, _ = model.act(observation, env.legal_actions(), deterministic=True)
            observation, _, done, truncated, info = env.step(action)
        return {'scope': 'offline_deck_order_curriculum', 'full_match_agent': False,
                'current_season_verified': False, 'contract_digest': model.contract_digest,
                'ordered_cards': info['ordered_cards'], 'terminated': done, 'truncated': truncated,
                'label_usable': info['label_usable'], 'battle_result': info['battle_result']}
