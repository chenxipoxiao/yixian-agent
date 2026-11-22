from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from tools.run_longyao_campaign import gpu_job_lock, reserve_budget, configured_daily_limit_seconds


class CampaignBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = datetime(2026, 11, 11, 15, tzinfo=timezone.utc)

    def test_same_plan_cannot_reserve_twice_and_budget_cannot_overflow(self):
        reserve_budget(self.root, 'a'*64, 12000, now=self.now)
        with self.assertRaises(FileExistsError):
            reserve_budget(self.root, 'a'*64, 100, now=self.now)
        with self.assertRaisesRegex(ValueError, 'budget'):
            reserve_budget(self.root, 'b'*64, 10000, now=self.now)

    def test_prior_day_reservation_overlapping_today_is_conservatively_charged(self):
        yesterday = self.now.replace(hour=0)-timedelta(minutes=10)
        reserve_budget(self.root, 'a'*64, 1200, now=yesterday)
        _, record = reserve_budget(self.root, 'b'*64, 1200, now=self.now)
        self.assertEqual(record['previously_charged_seconds'], 1200)

    def test_gpu_lock_rejects_concurrent_or_stale_owner_and_cleans_only_own(self):
        with gpu_job_lock(self.root):
            with self.assertRaises(FileExistsError):
                with gpu_job_lock(self.root):
                    self.fail('Acquired a second GPU lock')
        self.assertFalse((self.root/'runs/gpu-job.lock').exists())
        with gpu_job_lock(self.root):
            (self.root/'runs/gpu-job.lock').write_text(json.dumps({'owner': 'different-or-stale-owner'}))
        self.assertTrue((self.root/'runs/gpu-job.lock').exists())

    def test_monthly_gpu_keeps_accounting_without_six_hour_daily_stop(self):
        reserve_budget(self.root, 'c'*64, 21600, now=self.now)
        _, record = reserve_budget(self.root, 'd'*64, 7200, now=self.now, daily_limit_seconds=None)
        self.assertEqual(record['previously_charged_seconds'], 21600)
        self.assertIsNone(record['daily_limit_seconds'])
        self.assertFalse(record['daily_limit_enforced'])
        with self.assertRaises(FileExistsError):
            reserve_budget(self.root, 'd'*64, 7200, now=self.now, daily_limit_seconds=None)

    def test_uncapped_is_explicit_and_invalid_policy_does_not_disable_budget(self):
        self.assertIsNone(configured_daily_limit_seconds({'initial_max_gpu_job_hours_per_day': None}))
        self.assertEqual(configured_daily_limit_seconds({'initial_max_gpu_job_hours_per_day': 6}), 21600)
        with self.assertRaises(KeyError): configured_daily_limit_seconds({})
        for hours in (False, -1, 0, 'unlimited', float('inf'), float('nan')):
            with self.assertRaises(ValueError):
                configured_daily_limit_seconds({'initial_max_gpu_job_hours_per_day': hours})
        for limit in (-1, 0, False, 'unlimited'):
            with self.assertRaises(ValueError):
                reserve_budget(self.root, 'f'*64, 100, now=self.now, daily_limit_seconds=limit)

    def test_tactical_launcher_honors_monthly_policy_after_old_budget_exhausted(self):
        # Software launch fixture: no GPU process or real training is started.
        import hashlib
        from types import SimpleNamespace
        from unittest.mock import patch
        from tools import run_tactical_pilot as launcher
        for directory in ('configs', 'campaign'):
            (self.root/directory).mkdir()
        (self.root/'configs/training_stages.json').write_text(json.dumps({'execution_policy':
            {'initial_max_gpu_job_hours_per_day': None}}))
        (self.root/'configs/training.json').write_text(json.dumps({'train': {'max_minutes': 1}}))
        plan = self.root/'campaign/plan.json'
        plan.write_text(json.dumps({'scope': 'v3_proposal_only_no_battle_rewards', 'hard_seconds': 120,
            'source_sha256': {}, 'config': 'configs/training.json', 'out': 'runs/proposal', 'data': 'data'}))
        reserve_budget(self.root, 'a'*64, 21600)  # Old conservative reservation stays in ledger.
        def fake_training(*args, **kwargs):
            out = self.root/'runs/proposal'; out.mkdir()
            (out/'report.json').write_text(json.dumps({'status': 'completed', 'test_data_opened': False}))
            return SimpleNamespace(returncode=0)
        with patch.object(launcher, 'ROOT', self.root), patch.object(launcher, 'collect', return_value={}), \
                patch.object(launcher, 'assess', return_value={'may_launch_new_job': True}), \
                patch.object(launcher.subprocess, 'run', side_effect=fake_training):
            launcher.run(plan, hashlib.sha256(plan.read_bytes()).hexdigest())
        status = json.loads((self.root/'campaign/pilot-status.json').read_text())
        self.assertEqual(status['status'], 'completed')
        self.assertFalse(status['budget']['daily_limit_enforced'])
        self.assertEqual(status['budget']['previously_charged_seconds'], 21600)


if __name__ == '__main__':
    unittest.main()
