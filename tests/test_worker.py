import json
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from yixian.simulator import is_available, simulate_battle, SimulatorError
from yixian.worker import BattleWorker


@unittest.skipUnless(is_available(), 'external reference not installed')
class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.battle = json.loads((Path(__file__).resolve().parents[1] / 'examples/battle.json').read_text())

    def test_worker_matches_fresh_process_and_recovers_from_bad_input(self):
        battle = json.loads((Path(__file__).resolve().parents[1] / 'examples/battle.json').read_text())
        expected = simulate_battle(battle)
        with BattleWorker() as worker:
            self.assertEqual(worker(battle), expected)
            with self.assertRaises(SimulatorError):
                worker({'seed': 1})
            self.assertEqual(worker(battle), expected)
        with self.assertRaises(SimulatorError):
            worker(battle)

    def test_interleaved_random_capped_and_reversed_battles_are_isolated(self):
        random_battle = deepcopy(self.battle)
        for player in random_battle['players']:
            player['cards'] = ['121081'] * 8
            player['hp'] = player['max_hp'] = 80
        random_battle['include_log'] = True
        capped = dict(deepcopy(random_battle), seed=19, max_turns=1, first_player=1)
        reversed_battle = dict(deepcopy(self.battle), first_player=1, seed=23)
        cases = [random_battle, capped, reversed_battle]
        expected = [simulate_battle(case) for case in cases]
        with BattleWorker() as worker:
            for index in (0, 1, 2, 0, 2, 1, 0):
                self.assertEqual(worker(cases[index]), expected[index])
        self.assertTrue(expected[0]['used_randomness'])
        self.assertTrue(expected[1]['truncated'])
        self.assertIsNone(expected[1]['winner'])

    def test_malformed_protocol_closes_worker_instead_of_returning_labels(self):
        valid = simulate_battle(self.battle)
        invalid_status = dict(valid, terminated=True, truncated=True)
        wrong_seed = dict(valid, seed='different-battle')
        packets = [[], {'ok': True, 'result': []},
                   {'ok': True, 'result': invalid_status}, {'ok': True, 'result': wrong_seed},
                   {'ok': False, 'error': 'engine failed', 'recoverable': False}]
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'broken.mjs'
            for packet in packets:
                with self.subTest(packet=packet):
                    response = json.dumps(json.dumps(packet) + '\n')
                    script.write_text("process.stdin.once('data', () => process.stdout.write(" + response + "));", encoding='utf-8')
                    with patch('yixian.worker.BRIDGE', script), BattleWorker() as worker:
                        with self.assertRaises(SimulatorError):
                            worker(self.battle)
                        self.assertIsNotNone(worker._process.poll())
                        with self.assertRaisesRegex(SimulatorError, 'closed'):
                            worker(self.battle)

    def test_timeout_kills_process_and_rejects_future_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'stalled.mjs'
            script.write_text("process.stdin.resume();", encoding='utf-8')
            with patch('yixian.worker.BRIDGE', script), BattleWorker(timeout=.05) as worker:
                with self.assertRaisesRegex(SimulatorError, 'timed out'):
                    worker(self.battle)
                self.assertIsNotNone(worker._process.poll())
                with self.assertRaisesRegex(SimulatorError, 'closed'):
                    worker(self.battle)

    def test_invalid_timeouts_are_rejected(self):
        for timeout in (0, -1, float('nan'), float('inf'), True):
            with self.assertRaises(ValueError):
                BattleWorker(timeout=timeout)


if __name__ == '__main__':
    unittest.main()
