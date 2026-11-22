import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from yixian.order_data import CHARACTER, SCOPE, SPLIT_SALT, VERSION, game_split, validate_splits
from yixian.pretrain_protocol import load_development_corpus, sha, validate_development_config

try:
    import torch
except ImportError:
    torch = None


def fixture(root):
    data = root/'data'
    data.mkdir()
    groups = {}
    for index in range(1000):
        group = f'synthetic-development-only-{index}'
        split = game_split(group)
        if split in ('train', 'validation'):
            groups.setdefault(split, group)
        if len(groups) == 2:
            break
    records = []
    for split, group in groups.items():
        for board in ([1, 2, 1, 3], [3, 2, 1], [2, 1, 3, 4]):
            identity = hashlib.sha256(json.dumps([group, board], separators=(',', ':')).encode()).hexdigest()
            records.append({'id': identity, 'game_id': group, 'split': split, 'character_id': CHARACTER,
                'source_rules_version': VERSION, 'scope': SCOPE, 'season_mec': 10,
                'recorded_action_trajectory': False, 'board': board})
    hashes = {'test': 'not-opened-and-no-such-file'}
    for split in groups:
        path = data/f'{split}.jsonl'
        path.write_text(''.join(json.dumps(row)+'\n' for row in records if row['split'] == split), encoding='utf-8')
        hashes[split] = sha(path)
    manifest = {'scope': SCOPE, 'rules_version': VERSION, 'character_id': CHARACTER,
                'season_mec': 10, 'split_salt': SPLIT_SALT, 'vocabulary': [1, 2, 3, 4],
                'split_sha256': hashes, 'split_summary': validate_splits(records)}
    (data/'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    config = {'scope': SCOPE, 'full_match_training': False,
              'corpus_manifest_sha256': sha(data/'manifest.json'),
              'evaluation_roles': ['train', 'validation'], 'test_evaluation_enabled': False,
              'selection_metric': 'validation_teacher_nll',
              'model': {'width': 32, 'layers': 1, 'heads': 4, 'dropout': 0.},
              'train': {'seed': 73, 'validation_seed': 74, 'bootstrap_seed': 75,
                        'batch_size': 8, 'max_updates': 2, 'validation_interval': 1,
                        'early_stopping_patience': 4, 'minimum_improvement': .0001,
                        'learning_rate': .001, 'weight_decay': .01, 'max_grad_norm': 1.,
                        'max_minutes': 1, 'evaluation_batch_size': 8, 'cpu_threads': 2,
                        'bootstrap_samples': 20}}
    return data, config


class DevelopmentProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data, self.config = fixture(self.root)

    def test_development_loads_when_final_test_file_is_absent(self):
        self.assertFalse((self.data/'test.jsonl').exists())
        manifest, rows, boards = load_development_corpus(self.data,
            expected_manifest_sha256=self.config['corpus_manifest_sha256'])
        self.assertEqual(set(rows), {'train', 'validation'})
        self.assertEqual(len(boards['validation']), 3)
        self.assertEqual(manifest['split_sha256']['test'], 'not-opened-and-no-such-file')

    def test_manifest_and_development_checksum_tampering_rejected(self):
        with self.assertRaisesRegex(ValueError, 'manifest hash'):
            load_development_corpus(self.data, expected_manifest_sha256='0'*64)
        with (self.data/'train.jsonl').open('a', encoding='utf-8') as stream:
            stream.write('tampered')
        with self.assertRaisesRegex(ValueError, 'train data hash'):
            load_development_corpus(self.data, expected_manifest_sha256=self.config['corpus_manifest_sha256'])

    def test_semantic_identity_rejected_even_with_new_file_hash(self):
        path = self.data/'train.jsonl'
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows[0]['id'] = 'wrong-id'
        path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
        manifest_path = self.data/'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['split_sha256']['train'] = sha(path)
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'identity'):
            load_development_corpus(self.data, expected_manifest_sha256=sha(manifest_path))

    def test_test_role_and_test_stream_are_not_allowed_in_training(self):
        validate_development_config(self.config)
        for key, value in (('test_evaluation_enabled', True), ('evaluation_roles', ['train', 'validation', 'test'])):
            changed = dict(self.config, **{key: value})
            with self.assertRaises(ValueError):
                validate_development_config(changed)
        self.config['train']['test_seed'] = 90
        with self.assertRaisesRegex(ValueError, 'Final-test'):
            validate_development_config(self.config)

    def test_seed_overlap_and_unbounded_runtime_are_rejected(self):
        self.config['train']['validation_seed'] = self.config['train']['seed']
        with self.assertRaisesRegex(ValueError, 'distinct'):
            validate_development_config(self.config)
        self.config['train']['validation_seed'] += 1
        self.config['train']['max_minutes'] = 121
        with self.assertRaisesRegex(ValueError, 'two hours'):
            validate_development_config(self.config)

    @unittest.skipIf(torch is None, 'Optional Torch dependency is installed on the server only')
    def test_two_update_training_with_no_test_file_and_selected_checkpoint_reload(self):
        from tools import train_longyao_development as trainer
        from yixian.memory import Memory
        previous_threads = torch.get_num_threads()
        self.addCleanup(torch.set_num_threads, previous_threads)
        config_path = self.root/'config.json'
        config_path.write_text(json.dumps(self.config))
        args = SimpleNamespace(data=self.data, out=self.root/'run', config=config_path, device='cpu')
        with mock.patch.object(trainer, 'Memory', side_effect=lambda _: Memory(self.root/'memory.sqlite')):
            with contextlib.redirect_stdout(io.StringIO()):
                trainer.train(args)
        report = json.loads((args.out/'report.json').read_text())
        self.assertEqual(report['status'], 'completed')
        self.assertEqual(report['optimizer_updates'], 2)
        self.assertEqual(report['test_model_evaluations'], 0)
        self.assertFalse(report['test_data_opened'])
        self.assertNotIn('test', report)
        self.assertTrue(report['final_test_pending'])
        self.assertEqual(report['selected_validation']['multiset_violations'], 0)
        packet = torch.load(report['selected_checkpoint'], map_location='cpu', weights_only=True)
        self.assertEqual(packet['step'], report['selected_step'])
        self.assertEqual(set(packet['contract']['split_sha256']), {'train', 'validation'})
        for name, expected in packet['contract']['source_sha256'].items():
            self.assertEqual(sha(args.out/'source'/name), expected)
        self.assertTrue(Memory(self.root/'memory.sqlite').verify_integrity())
        with self.assertRaises(FileExistsError):
            trainer.train(args)


if __name__ == '__main__':
    unittest.main()
