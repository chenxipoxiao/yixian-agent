"""One preregistered v3 proposal job, serialized with all other GPU campaigns."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.run_longyao_campaign import gpu_job_lock, reserve_budget, write_json, configured_daily_limit_seconds
from tools.monitor_training import collect
from yixian.training_monitor import assess
from yixian.pretrain_protocol import sha
from yixian.memory import Memory


def run(plan_path, expected):
    if sha(plan_path) != expected:
        raise ValueError('Plan hash mismatch')
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    if plan['scope'] != 'v3_proposal_only_no_battle_rewards' or not 1 <= plan['hard_seconds'] <= 7200:
        raise ValueError('Unexpected scope or runtime budget')
    for name, checksum in plan['source_sha256'].items():
        if sha(ROOT/name) != checksum:
            raise ValueError('Frozen source changed: '+name)
    config = json.loads((ROOT/plan['config']).read_text(encoding='utf-8'))
    if config['train']['max_minutes']*60 >= plan['hard_seconds']:
        raise ValueError('No time left for final reporting')
    out = ROOT/plan['out']
    status = plan_path.parent/'pilot-status.json'
    if out.exists() or status.exists():
        raise FileExistsError('This experiment was already attempted')
    policy = json.loads((ROOT/'configs/training_stages.json').read_text(encoding='utf-8-sig'))['execution_policy']
    memory = Memory(ROOT/'runs/research.sqlite')
    with gpu_job_lock(ROOT):
        health = assess(collect(ROOT), policy)
        if not health['may_launch_new_job']:
            raise RuntimeError('Server is not healthy and idle')
        budget_path, budget = reserve_budget(ROOT, expected, plan['hard_seconds'],
            daily_limit_seconds=configured_daily_limit_seconds(policy))
        experiment = memory.register_experiment(plan, {'scope': plan['scope'], 'plan_sha256': expected}, role='training')
        memory.record_experiment(experiment, 'running', {'budget': str(budget_path)}, role='training')
        state = {'status': 'running', 'experiment_id': experiment, 'budget': budget, 'test_data_opened': False,
                 'battle_rewards_used': False, 'full_match_training': False}
        write_json(status, state)
        started = time.monotonic()
        try:
            with (plan_path.parent/'training.log').open('x', encoding='utf-8') as stream:
                job = subprocess.run([sys.executable, '-u', str(ROOT/'tools/train_tactical_proposal.py'),
                    '--data', str(ROOT/plan['data']), '--out', str(out), '--config', str(ROOT/plan['config']),
                    '--device', 'cuda'], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                    timeout=plan['hard_seconds'], check=False)
            if job.returncode:
                raise RuntimeError(f'Trainer exited {job.returncode}; preserve logs before diagnosing')
            report = json.loads((out/'report.json').read_text(encoding='utf-8'))
            if report['status'] != 'completed' or report['test_data_opened'] is not False:
                raise RuntimeError('Unexpected training result')
            state.update(status='completed', report=str(out/'report.json'),
                         actual_gpu_job_seconds=time.monotonic()-started,
                         completed_at_utc=datetime.now(timezone.utc).isoformat())
            write_json(status, state)
            memory.record_experiment(experiment, 'completed', state, role='training')
        except BaseException as error:
            state.update(status='failed', error=str(error), actual_gpu_job_seconds=time.monotonic()-started)
            write_json(status, state); write_json(plan_path.parent/'pilot-failure.json', state)
            memory.record_experiment(experiment, 'failed', state, role='training')
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    args = parser.parse_args()
    run(args.plan, args.plan_sha256)
