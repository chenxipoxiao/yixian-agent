import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import numpy as np

try:
    import torch
    from yixian.order_model import BoardOrderPolicy, reconstruction_loss
except ImportError:
    torch = None

from yixian.order_data import CHARACTER, VERSION, SCOPE, game_split, teacher_batch, validate_splits


@unittest.skipIf(torch is None, 'Optional GPU training dependencies are not installed')
class OrderModelTests(unittest.TestCase):
    def setUp(self):
        previous = torch.get_num_threads()
        torch.set_num_threads(2)
        self.addCleanup(torch.set_num_threads, previous)
        torch.manual_seed(73)

    def test_mask_and_candidate_permutation_equivariance(self):
        model = BoardOrderPolicy(10, width=32, layers=1, heads=4, dropout=0).eval()
        batch = {k: torch.from_numpy(v) for k, v in teacher_batch(
            [[1, 2, 1, 3]], np.random.default_rng(3), steps=[1]).items()}
        permutation = torch.tensor([7, 1, 5, 3, 0, 2, 4, 6])
        with torch.no_grad():
            logits = model(batch['candidates'], batch['prefix'], batch['available'])
            changed = model(batch['candidates'][:, permutation], batch['prefix'],
                            batch['available'][:, permutation])
        torch.testing.assert_close(changed, logits[:, permutation], atol=1e-5, rtol=1e-5)
        self.assertTrue((logits[~batch['available']] < -1e8).all())

    def test_duplicate_targets_are_marginalized_and_illegal_targets_rejected(self):
        logits = torch.tensor([[0., 0., 0., -1e9]], requires_grad=True)
        targets = torch.tensor([[True, True, False, False]])
        loss = reconstruction_loss(logits, targets)
        self.assertAlmostEqual(loss.item(), -np.log(2/3), places=6)
        loss.mean().backward()
        self.assertTrue(torch.isfinite(logits.grad).all())
        with self.assertRaises(ValueError):
            reconstruction_loss(logits, ~targets)

    def test_learning_reduces_known_pattern_loss(self):
        model = BoardOrderPolicy(10, width=32, layers=1, heads=4, dropout=0)
        optimizer = torch.optim.AdamW(model.parameters(), lr=.005)
        batch = {k: torch.from_numpy(v) for k, v in teacher_batch(
            [[1, 2, 3, 4]]*8, np.random.default_rng(3), steps=[0]*8).items()}
        def loss():
            return reconstruction_loss(model(batch['candidates'], batch['prefix'],
                batch['available']), batch['targets']).mean()
        initial = loss().item()
        for _ in range(20):
            optimizer.zero_grad()
            current = loss()
            current.backward()
            optimizer.step()
        self.assertLess(loss().item(), initial*.3)

    def test_end_to_end_synthetic_run_and_checkpoint_contract(self):
        # This fixture never opens the real reserved test set. On the server it
        # also exercises fp16, CUDA optimizer updates and safe checkpoint load.
        from tools import train_longyao_pretrain as trainer
        from yixian.memory import Memory
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root/'data'
            data.mkdir()
            records, groups = [], {}
            for index in range(1000):
                group = f'synthetic-only-{index}'
                split = game_split(group)
                if split in groups:
                    continue
                groups[split] = group
                for number, board in enumerate(([1, 2, 1, 3], [3, 2, 1], [2, 1, 3, 4])):
                    records.append({'id':f'{group}-{number}', 'game_id':group,
                        'split':split, 'character_id':CHARACTER,
                        'source_rules_version':VERSION, 'scope':SCOPE,
                        'recorded_action_trajectory':False, 'board':board})
                if len(groups) == 3:
                    break
            hashes = {}
            for split in groups:
                path = data/f'{split}.jsonl'
                path.write_text(''.join(json.dumps(row)+'\n' for row in records
                    if row['split'] == split), encoding='utf-8')
                hashes[split] = trainer.sha(path)
            manifest = {'scope':SCOPE, 'rules_version':VERSION, 'vocabulary':[1, 2, 3, 4],
                        'split_sha256':hashes, 'split_summary':validate_splits(records)}
            trainer.write_json(data/'manifest.json', manifest)
            config = json.loads((trainer.ROOT/'configs/longyao_pretrain.json').read_text())
            config['model'] = {'width':32, 'layers':1, 'heads':4, 'dropout':0.0}
            config['train'].update(batch_size=8, max_updates=4, validation_interval=2,
                evaluation_batch_size=8, cpu_threads=2)
            trainer.write_json(root/'config.json', config)
            args = SimpleNamespace(data=data, out=root/'run', config=root/'config.json',
                device='cuda' if torch.cuda.is_available() else 'cpu')
            with mock.patch.object(trainer, 'Memory', side_effect=lambda _:Memory(root/'memory.sqlite')):
                with contextlib.redirect_stdout(io.StringIO()):
                    trainer.train(args)
            status = json.loads((args.out/'status.json').read_text())
            self.assertEqual(status['status'], 'completed')
            self.assertGreater(status['optimizer_updates'], 0)
            self.assertFalse(status['test_used_for_selection'])
            self.assertFalse(status['game_strength_evaluated'])
            checkpoint = torch.load(status['selected_checkpoint'], map_location='cpu', weights_only=True)
            self.assertEqual(checkpoint['contract_digest'], status['contract_digest'])
            self.assertEqual(checkpoint['vocabulary'], [1, 2, 3, 4])
            self.assertTrue(Memory(root/'memory.sqlite').verify_integrity())
            from tools.predict_board_order import predict
            prediction = predict(status['selected_checkpoint'], [2, 1, 2, 3])
            self.assertCountEqual(prediction['ordered_cards'], [2, 1, 2, 3])
            self.assertEqual(prediction['prefix_source'], 'own_previous_predictions')
            with self.assertRaisesRegex(ValueError, 'outside'):
                predict(status['selected_checkpoint'], [1, 2, 999])
            with self.assertRaises(FileExistsError):
                trainer.train(args)


if __name__ == '__main__':
    unittest.main()
