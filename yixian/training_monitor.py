"""Read-only training health classification; never starts or stops jobs."""
from __future__ import annotations

from datetime import datetime, timezone


def assess(snapshot, policy, *, now=None):
    now = now or datetime.now(timezone.utc)
    alerts = []
    if snapshot.get('connection_error'):
        return {'health':'unreachable', 'alerts':['ssh_unreachable'],
                'training_active':False, 'may_launch_new_job':False}
    if snapshot.get('collection_errors'):
        alerts.append('incomplete_telemetry')
    if not snapshot.get('gpus'):
        alerts.append('gpu_unavailable')
    for gpu in snapshot.get('gpus', []):
        temperature = gpu.get('temperature_celsius')
        if temperature is not None and temperature >= policy['gpu_temperature_warning_celsius']:
            alerts.append('gpu_temperature_high')
    free = snapshot.get('disk', {}).get('free_gib')
    if free is None or free < policy['minimum_free_disk_gib']:
        alerts.append('disk_space_low_or_unknown')
    processes = snapshot.get('training_processes', [])
    active_paths = {row['out_dir'] for row in processes}
    if len(processes) > policy['concurrent_gpu_jobs']:
        alerts.append('multiple_training_jobs')
    for run in snapshot.get('runs', []):
        if run['status'] != 'running':
            continue
        if run['run_dir'] not in active_paths:
            alerts.append('running_status_without_process:' + run['run_dir'])
        try:
            updated = datetime.fromisoformat(run['updated_at_utc'].replace('Z', '+00:00'))
            age = (now-updated).total_seconds()
            if age > policy['stale_progress_minutes']*60:
                alerts.append('stale_training_progress:' + run['run_dir'])
        except (KeyError, TypeError, ValueError):
            alerts.append('missing_progress_timestamp:' + run['run_dir'])
    # A finished run is not stale, and GPU utilization alone never proves that
    # this project's learner is running. Any GPU compute process blocks launch.
    active = bool(processes)
    occupied = bool(snapshot.get('gpu_processes'))
    return {'health':'attention_needed' if alerts else 'healthy',
            'alerts':sorted(set(alerts)), 'training_active':active,
            'gpu_occupied':occupied,
            'may_launch_new_job':not alerts and not active and not occupied,
            'scope':'hardware_and_process_health_only; stage_and_budget_gates_still_required'}
