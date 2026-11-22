"""Run a frozen three-seed development campaign sequentially with hard limits."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from yixian.holdout_protocol import read_json, validate_plan, verify_sources, within
from yixian.memory import Memory
from yixian.pretrain_protocol import sha
from yixian.training_monitor import assess
from tools.monitor_training import collect


def write_json(path, value):
    temporary = path.with_suffix('.part')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    temporary.replace(path)


@contextmanager
def gpu_job_lock(root):
    path = Path(root)/'runs/gpu-job.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    identity = uuid.uuid4().hex
    with path.open('x', encoding='utf-8') as stream:
        json.dump({'owner': identity, 'pid': os.getpid(), 'created_at_utc': datetime.now(timezone.utc).isoformat()}, stream)
    try:
        yield
    finally:
        if path.exists() and read_json(path).get('owner') == identity:
            path.unlink()


def configured_daily_limit_seconds(policy):
    """None explicitly authorizes uncapped daily use of the monthly GPU.

    Missing/malformed policy is an error, not an implicit uncapped allowance.
    Job duration, concurrency and experiment registration remain independent.
    """
    hours = policy['initial_max_gpu_job_hours_per_day']
    if hours is None:
        return None
    if type(hours) not in (int, float) or not math.isfinite(hours) or hours <= 0:
        raise ValueError('Invalid configured daily GPU limit')
    seconds = int(hours * 3600)
    if seconds < 1:
        raise ValueError('Daily GPU limit must be at least one second')
    return seconds


def reserve_budget(root, plan_sha, seconds, *, now=None, daily_limit_seconds=21600):
    now = now or datetime.now(timezone.utc)
    if (daily_limit_seconds is not None and
            (type(daily_limit_seconds) is not int or daily_limit_seconds < 1)):
        raise ValueError('Invalid daily GPU budget')
    if type(seconds) is not int or seconds < 1 or (daily_limit_seconds is not None and seconds > daily_limit_seconds):
        raise ValueError('Invalid GPU time reservation')
    directory = Path(root)/'runs/gpu-budget'
    directory.mkdir(parents=True, exist_ok=True)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    charged = 0
    for path in directory.glob('*.json'):
        entry = read_json(path)
        created = datetime.fromisoformat(entry['created_at_utc'])
        until = datetime.fromisoformat(entry['reserved_until_utc'])
        if created >= day_start or until >= day_start:
            charged += entry['reserved_seconds']
    if daily_limit_seconds is not None and charged+seconds > daily_limit_seconds:
        raise ValueError('Daily conservative GPU budget would be exceeded')
    path = directory/f"{now.strftime('%Y%m%d')}-{plan_sha[:16]}.json"
    record = {'created_at_utc': now.isoformat(), 'reserved_until_utc': (now+timedelta(seconds=seconds)).isoformat(),
              'plan_sha256': plan_sha, 'reserved_seconds': seconds,
              'previously_charged_seconds': charged, 'daily_limit_seconds': daily_limit_seconds,
              'daily_limit_enforced': daily_limit_seconds is not None,
              'basis': 'conservative wall-clock job reservation; not measured GPU utilization'}
    with path.open('x', encoding='utf-8') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    return path, record


def run(args):
    if sha(args.plan) != args.plan_sha256:
        raise ValueError('Preregistered plan hash mismatch')
    plan = read_json(args.plan)
    validate_plan(ROOT, plan)
    campaign = args.plan.resolve().parent
    if (campaign/'status.json').exists():
        raise FileExistsError('Campaign has already been attempted; do not blindly restart')
    policy = read_json(ROOT/'configs/training_stages.json')['execution_policy']
    hard_seconds = plan['budget']['hard_seconds_per_run']
    if type(hard_seconds) is not int or not 1 <= hard_seconds <= 7200:
        raise ValueError('Hard per-run limit must not exceed two hours')
    for candidate in plan['runs']:
        config = read_json(within(ROOT, candidate['config']))
        if config['train']['max_minutes']*60 >= hard_seconds:
            raise ValueError('Soft training limit must leave room below the hard job deadline')
        if within(ROOT, candidate['run_dir']).exists():
            raise FileExistsError('A planned output directory already exists')
    memory = Memory(ROOT/'runs/research.sqlite')
    with gpu_job_lock(ROOT):
        snapshot = collect(ROOT)
        health = assess(snapshot, policy)
        if not health['may_launch_new_job']:
            raise RuntimeError('Server is not healthy and idle: '+json.dumps(health))
        reservation, budget = reserve_budget(ROOT, args.plan_sha256, hard_seconds*len(plan['runs']),
            daily_limit_seconds=configured_daily_limit_seconds(policy))
        experiment = memory.register_experiment(plan, {'plan_sha256': args.plan_sha256,
            'source_sha256': plan['source_sha256'], 'scope': 'three_seed_development_only_campaign'}, role='training')
        memory.record_experiment(experiment, 'running', {'campaign': str(campaign), 'budget': str(reservation)})
        state = {'status': 'running', 'experiment_id': experiment, 'scope': plan['scope'],
                 'plan_sha256': args.plan_sha256, 'budget': budget, 'runs': [],
                 'test_data_opened': False, 'test_model_evaluations': 0, 'full_match_training': False}
        write_json(campaign/'status.json', state)
        try:
            for candidate in plan['runs']:
                verify_sources(ROOT, plan['source_sha256'])
                health = assess(collect(ROOT), policy)
                if not health['may_launch_new_job']:
                    raise RuntimeError('Server stopped being idle before the next seed')
                out = within(ROOT, candidate['run_dir'])
                log = campaign/f"seed-{candidate['seed']}.log"
                state['active_seed'] = candidate['seed']
                state['updated_at_utc'] = datetime.now(timezone.utc).isoformat()
                write_json(campaign/'status.json', state)
                started = time.monotonic()
                command = [sys.executable, '-u', str(ROOT/'tools/train_longyao_development.py'),
                    '--data', str(within(ROOT, plan['data'])), '--out', str(out),
                    '--config', str(within(ROOT, candidate['config'])), '--device', 'cuda']
                with log.open('x', encoding='utf-8') as stream:
                    completed = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                               timeout=hard_seconds, check=False)
                elapsed = time.monotonic()-started
                if completed.returncode:
                    raise RuntimeError(f"Seed {candidate['seed']} exited {completed.returncode}; see {log}")
                report = read_json(out/'report.json')
                if report['status'] != 'completed' or report['test_data_opened'] is not False:
                    raise RuntimeError('Unexpected development run result')
                state['runs'].append({'seed': candidate['seed'], 'run_dir': str(out),
                    'elapsed_seconds': elapsed, 'selected_step': report['selected_step'],
                    'selected_checkpoint_sha256': report['selected_checkpoint_sha256']})
                state['active_seed'] = None
                write_json(campaign/'status.json', state)
            state.update(status='completed', actual_gpu_job_seconds=sum(run['elapsed_seconds'] for run in state['runs']),
                         updated_at_utc=datetime.now(timezone.utc).isoformat(), final_test_pending=True)
            write_json(campaign/'status.json', state)
            write_json(campaign/'report.json', state)
            memory.record_experiment(experiment, 'completed', {'report': str(campaign/'report.json'),
                'actual_gpu_job_seconds': state['actual_gpu_job_seconds'], 'test_data_opened': False})
        except BaseException as error:
            state.update(status='failed', error=str(error), updated_at_utc=datetime.now(timezone.utc).isoformat())
            write_json(campaign/'status.json', state)
            write_json(campaign/'failure.json', state)
            memory.record_experiment(experiment, 'failed', {'error': str(error), 'campaign': str(campaign)})
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
