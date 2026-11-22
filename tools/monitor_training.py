"""Collect server health and run metadata, locally or through the SSH alias."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from yixian.training_monitor import assess


def gpu_rows(query):
    result = subprocess.run(['nvidia-smi', query, '--format=csv,noheader,nounits'],
                            capture_output=True, text=True, timeout=10, check=True)
    return list(csv.reader(io.StringIO(result.stdout)))


def collect(root):
    result = {'observed_at_utc':datetime.now(timezone.utc).isoformat(),
              'project_directory':str(root), 'collection_errors':[], 'runs':[],
              'training_processes':[], 'gpus':[], 'gpu_processes':[]}
    disk = shutil.disk_usage(root)
    result['disk'] = {'free_gib':round(disk.free/2**30, 3), 'total_gib':round(disk.total/2**30, 3)}
    try:
        for row in gpu_rows('--query-gpu=name,memory.total,memory.used,utilization.gpu,temperature.gpu'):
            result['gpus'].append({'name':row[0].strip(), 'memory_total_mib':int(row[1]),
                'memory_used_mib':int(row[2]), 'utilization_percent':int(row[3]),
                'temperature_celsius':int(row[4])})
        for row in gpu_rows('--query-compute-apps=pid,used_memory'):
            if len(row) == 2:
                result['gpu_processes'].append({'pid':int(row[0]), 'memory_used_mib':int(row[1])})
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        result['collection_errors'].append('gpu_query:' + type(error).__name__)
    if hasattr(os, 'getloadavg'):
        result['load_average'] = list(os.getloadavg())
    meminfo = Path('/proc/meminfo')
    if meminfo.exists():
        values = {line.split(':')[0]:int(line.split()[1]) for line in meminfo.read_text().splitlines()}
        result['memory'] = {'available_gib':round(values['MemAvailable']/2**20, 3),
                            'total_gib':round(values['MemTotal']/2**20, 3)}
    for dirname in ('pretraining', 'training'):
        for path in (root/'runs'/dirname).glob('*/status.json'):
            try:
                status = json.loads(path.read_text())
                result['runs'].append({key:status[key] for key in (
                    'status', 'step', 'optimizer_updates', 'best_step', 'updated_at_utc',
                    'elapsed_seconds', 'stop_reason', 'error', 'scope') if key in status}
                    | {'run_dir':str(path.parent.resolve())})
            except (OSError, ValueError) as error:
                result['collection_errors'].append('status:' + str(path) + ':' + type(error).__name__)
    proc = Path('/proc')
    if not proc.is_dir():
        result['collection_errors'].append('linux_process_inventory_unavailable')
    else:
        for entry in proc.iterdir():
            if not entry.name.isdigit():
                continue
            try:
                args = (entry/'cmdline').read_bytes().decode(errors='replace').strip('\0').split('\0')
                if '--out' not in args or not any(Path(arg).name.startswith('train_')
                    and arg.endswith('.py') for arg in args):
                    continue
                cwd = (entry/'cwd').resolve(strict=True)
                out = Path(args[args.index('--out')+1])
                out = (cwd/out).resolve()
                if not out.is_relative_to(root/'runs'):
                    continue
                result['training_processes'].append({'pid':int(entry.name), 'out_dir':str(out)})
            except (OSError, IndexError):
                continue
    return result


def save_snapshot(value, root):
    directory = root/'runs/monitoring'
    directory.mkdir(parents=True, exist_ok=True)
    name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]+'.json'
    path = directory/name
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
    pointer = directory/'latest.json'
    temporary = pointer.with_suffix('.part')
    temporary.write_text(json.dumps({'report':str(path)}, indent=2)+'\n', encoding='utf-8')
    temporary.replace(pointer)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ssh', action='store_true', help='Use the configured existing SSH alias')
    parser.add_argument('--collect', action='store_true', help='Print raw server telemetry for SSH transport')
    args = parser.parse_args()
    plan = json.loads((ROOT/'configs/training_stages.json').read_text(encoding='utf-8'))
    policy = plan['execution_policy']
    if args.collect:
        print(json.dumps(collect(ROOT)))
        return
    if args.ssh:
        remote = Path(policy['remote_project']).as_posix()
        command = shlex.quote(remote+'/.venv/bin/python')+' '+shlex.quote(remote+'/tools/monitor_training.py')+' --collect'
        try:
            response = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                policy['ssh_alias'], command], capture_output=True, text=True, encoding='utf-8', timeout=35, check=True)
            snapshot = json.loads(response.stdout)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            snapshot = {'observed_at_utc':datetime.now(timezone.utc).isoformat(),
                        'connection_error':type(error).__name__}
    else:
        snapshot = collect(ROOT)
    snapshot['assessment'] = assess(snapshot, policy)
    snapshot['stage_plan'] = 'configs/training_stages.json'
    snapshot['current_stage'] = plan['current_stage']
    path = save_snapshot(snapshot, ROOT)
    print(json.dumps({'report':str(path), 'assessment':snapshot['assessment'],
                      'current_stage':plan['current_stage'], 'runs':snapshot.get('runs', [])}))
    if snapshot['assessment']['health'] != 'healthy':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
