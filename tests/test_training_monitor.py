from copy import deepcopy
from datetime import datetime, timezone
import unittest

from yixian.training_monitor import assess


class TrainingMonitorTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 11, 13, 0, tzinfo=timezone.utc)
        self.policy = {'gpu_temperature_warning_celsius':85, 'minimum_free_disk_gib':10,
                       'concurrent_gpu_jobs':1, 'stale_progress_minutes':15}
        self.snapshot = {'gpus':[{'temperature_celsius':40}], 'gpu_processes':[],
            'disk':{'free_gib':80}, 'training_processes':[],
            'runs':[{'run_dir':'/runs/a', 'status':'completed', 'updated_at_utc':'2020-01-01T00:00:00+00:00'}]}

    def check(self, snapshot):
        return assess(snapshot, self.policy, now=self.now)

    def test_completed_run_is_not_misclassified_as_stalled(self):
        status = self.check(self.snapshot)
        self.assertEqual(status['health'], 'healthy')
        self.assertTrue(status['may_launch_new_job'])

    def test_running_state_without_process_is_not_allowed_to_restart_blindly(self):
        self.snapshot['runs'][0]['status'] = 'running'
        status = self.check(self.snapshot)
        self.assertFalse(status['may_launch_new_job'])
        self.assertTrue(any('without_process' in alert for alert in status['alerts']))

    def test_live_process_blocks_duplicate_job_even_before_first_status(self):
        self.snapshot['training_processes'] = [{'pid':123, 'out_dir':'/runs/new'}]
        status = self.check(self.snapshot)
        self.assertTrue(status['training_active'])
        self.assertFalse(status['may_launch_new_job'])

    def test_other_gpu_process_blocks_launch_without_claiming_ours_is_running(self):
        self.snapshot['gpu_processes'] = [{'pid':123, 'memory_used_mib':100}]
        status = self.check(self.snapshot)
        self.assertFalse(status['training_active'])
        self.assertFalse(status['may_launch_new_job'])

    def test_stale_progress_and_resource_problems_require_attention(self):
        self.snapshot['runs'][0]['status'] = 'running'
        self.snapshot['training_processes'] = [{'pid':123, 'out_dir':'/runs/a'}]
        self.snapshot['gpus'][0]['temperature_celsius'] = 86
        self.snapshot['disk']['free_gib'] = 5
        status = self.check(self.snapshot)
        self.assertIn('gpu_temperature_high', status['alerts'])
        self.assertIn('disk_space_low_or_unknown', status['alerts'])
        self.assertTrue(any('stale' in alert for alert in status['alerts']))

    def test_ssh_failure_does_not_report_healthy_idle(self):
        status = self.check({'connection_error':'TimeoutExpired'})
        self.assertEqual(status['health'], 'unreachable')
        self.assertFalse(status['may_launch_new_job'])

    def test_incomplete_telemetry_blocks_launch(self):
        self.snapshot['collection_errors'] = ['process_read_failed']
        self.assertFalse(self.check(self.snapshot)['may_launch_new_job'])


if __name__ == '__main__':
    unittest.main()
