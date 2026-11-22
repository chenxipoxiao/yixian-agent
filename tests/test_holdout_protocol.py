"""Synthetic artifacts only; none of these tests opens the reserved real holdout."""
from concurrent.futures import ThreadPoolExecutor
import contextlib
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from yixian.holdout_protocol import (build_selection, claim_and_load_test, freeze_selection,
    validate_plan, validate_selection)
from yixian.order_data import CHARACTER, SCOPE, SPLIT_SALT, VERSION, game_split, validate_splits
from yixian.pretrain_protocol import sha

try:
    import torch
except ImportError:
    torch = None


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')


def fixture(root):
    data = root/'data'
    data.mkdir()
    groups = {}
    for i in range(1000):
        group = f'holdout-software-fixture-{i}'
        groups.setdefault(game_split(group), group)
        if len(groups) == 3:
            break
    rows, hashes = [], {}
    for split, group in groups.items():
        board = [1, 2, 1, 3]
        row = {'id': hashlib.sha256(json.dumps([group, board], separators=(',', ':')).encode()).hexdigest(),
               'game_id': group, 'board': board, 'split': split, 'scope': SCOPE,
               'character_id': CHARACTER, 'source_rules_version': VERSION, 'season_mec': 10,
               'recorded_action_trajectory': False}
        rows.append(row)
        p = data/f'{split}.jsonl'
        p.write_text(json.dumps(row)+'\n', encoding='utf-8')
        hashes[split] = sha(p)
    manifest = {'scope': SCOPE, 'rules_version': VERSION, 'character_id': CHARACTER, 'season_mec': 10,
                'split_salt': SPLIT_SALT, 'vocabulary': [1, 2, 3], 'split_sha256': hashes,
                'split_summary': validate_splits(rows), 'holdout_status': 'new_group_disjoint_unevaluated',
                'test_model_evaluations': 0}
    write(data/'manifest.json', manifest)
    (root/'fixture-source.txt').write_text('synthetic protocol fixture; not model code')
    plan = {'scope': SCOPE, 'test_policy': 'once_after_all_three_runs_frozen', 'data': 'data',
            'manifest_sha256': sha(data/'manifest.json'), 'minimum_games': {role: 1 for role in groups},
            'source_sha256': {'fixture-source.txt': sha(root/'fixture-source.txt')},
            'evaluation': {'seed': 41, 'bootstrap_seed': 42, 'batch_size': 8, 'bootstrap_samples': 20},
            'runs': []}
    for seed, nll in ((11, .3), (12, .2), (13, .4)):
        config = {'scope': SCOPE, 'full_match_training': False, 'corpus_manifest_sha256': plan['manifest_sha256'],
                  'evaluation_roles': ['train', 'validation'], 'test_evaluation_enabled': False,
                  'selection_metric': 'validation_teacher_nll',
                  'model': {'width': 32, 'layers': 1, 'heads': 4, 'dropout': 0.},
                  'train': {'seed': seed, 'validation_seed': 31, 'bootstrap_seed': 32,
                            'batch_size': 8, 'max_updates': 2, 'validation_interval': 1,
                            'early_stopping_patience': 4, 'evaluation_batch_size': 8,
                            'cpu_threads': 2, 'bootstrap_samples': 20, 'max_minutes': 1}}
        config_path = root/f'config-{seed}.json'
        write(config_path, config)
        directory = root/f'runs/pretraining/fixture-{seed}'
        write(directory/'config.json', config)
        checkpoint = directory/'checkpoint-000001.pt'
        checkpoint.write_bytes(f'synthetic-protocol-weights-{seed}'.encode())
        write(directory/'best.json', {'step': 1, 'path': str(checkpoint), 'validation_nll': nll})
        write(directory/'report.json', {'status': 'completed', 'test_data_opened': False,
            'test_model_evaluations': 0, 'optimizer_updates': 2, 'selected_step': 1,
            'selected_checkpoint': str(checkpoint), 'selected_checkpoint_sha256': sha(checkpoint),
            'selected_validation': {'illegal_predictions': 0, 'multiset_violations': 0,
                'pooled_metrics': {'model': {'teacher_nll': nll}, 'random': {'teacher_nll': 1.5},
                                   'position_frequency': {'teacher_nll': 1.1}}}})
        plan['runs'].append({'seed': seed, 'config': config_path.name, 'config_sha256': sha(config_path),
                             'run_dir': directory.relative_to(root).as_posix()})
    write(root/'plan.json', plan)
    return plan


class HoldoutProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plan = fixture(self.root)

    def selection(self):
        return build_selection(self.root, self.root/'plan.json')

    def test_freeze_chooses_validation_champion_without_opening_test(self):
        original = Path.open
        def guarded(path, *args, **kwargs):
            if path.name == 'test.jsonl':
                raise AssertionError('Test opened before selection freeze')
            return original(path, *args, **kwargs)
        destination = self.root/'selection.json'
        with mock.patch.object(Path, 'open', guarded):
            selection = freeze_selection(self.root, self.root/'plan.json', destination)
            checked = validate_selection(self.root, destination, sha(destination))
        self.assertEqual(selection, checked)
        self.assertEqual(selection['champion_seed'], 12)
        self.assertEqual(len(selection['runs']), 3)
        with self.assertRaises(FileExistsError):
            freeze_selection(self.root, self.root/'plan.json', destination)

    def test_missing_or_failed_seed_cannot_unlock_test(self):
        path = self.root/self.plan['runs'][1]['run_dir']/'report.json'
        report = json.loads(path.read_text())
        report['status'] = 'failed'
        write(path, report)
        with self.assertRaisesRegex(ValueError, 'complete'):
            self.selection()
        self.assertFalse((self.root/'runs/evaluations/holdout-use').exists())

    def test_configuration_or_source_tampering_is_rejected(self):
        (self.root/'fixture-source.txt').write_text('changed source')
        with self.assertRaisesRegex(ValueError, 'source changed'):
            self.selection()

    def test_cross_platform_config_newlines_do_not_change_frozen_settings(self):
        for run in self.plan['runs']:
            path = self.root/run['run_dir']/'config.json'
            content = path.read_bytes().replace(b'\r\n', b'\n')
            path.write_bytes(content)
        selected = self.selection()
        self.assertEqual(selected['champion_seed'], 12)
        for run in selected['runs']:
            self.assertEqual(run['executed_config_sha256'], sha(self.root/run['run_dir']/'config.json'))

    def test_executed_hyperparameter_change_is_still_rejected(self):
        path = self.root/self.plan['runs'][0]['run_dir']/'config.json'
        config = json.loads(path.read_text())
        config['train']['max_updates'] += 1
        write(path, config)
        with self.assertRaisesRegex(ValueError, 'configuration differs'):
            self.selection()

    def test_final_test_seeds_cannot_overlap_training_or_validation(self):
        self.plan['evaluation']['seed'] = 31
        with self.assertRaisesRegex(ValueError, 'overlap'):
            validate_plan(self.root, self.plan)

    def test_after_freeze_report_edits_are_detected(self):
        path = self.root/'selection.json'
        freeze_selection(self.root, self.root/'plan.json', path)
        report_path = self.root/self.plan['runs'][0]['run_dir']/'report.json'
        report = json.loads(report_path.read_text())
        report['extra_edit'] = True
        write(report_path, report)
        with self.assertRaisesRegex(ValueError, 'changed'):
            validate_selection(self.root, path, sha(path))

    def test_bad_validation_gate_does_not_consume_holdout(self):
        directory = self.root/self.plan['runs'][0]['run_dir']
        report = json.loads((directory/'report.json').read_text())
        report['selected_validation']['pooled_metrics']['model']['teacher_nll'] = 2.
        write(directory/'report.json', report)
        best = json.loads((directory/'best.json').read_text())
        best['validation_nll'] = 2.
        write(directory/'best.json', best)
        with self.assertRaisesRegex(ValueError, 'baselines'):
            self.selection()
        self.assertFalse((self.root/'runs/evaluations/holdout-use').exists())

    def test_one_claim_covers_exact_frozen_models_and_blocks_second_selection(self):
        selection = self.selection()
        rows, boards, claim = claim_and_load_test(self.root, selection, 'selection-one')
        self.assertEqual(boards, [[1, 2, 1, 3]])
        self.assertEqual(rows[0]['split'], 'test')
        self.assertEqual(len(json.loads(claim.read_text())['checkpoint_sha256']), 3)
        with self.assertRaises(FileExistsError):
            claim_and_load_test(self.root, selection, 'another-selection')

    def test_concurrent_claims_allow_only_one_reader(self):
        selection = self.selection()
        def attempt(index):
            try:
                claim_and_load_test(self.root, selection, str(index))
                return 'opened'
            except FileExistsError:
                return 'refused'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, range(2)))
        self.assertCountEqual(results, ['opened', 'refused'])

    def test_corrupted_test_retains_claim_and_cannot_be_blindly_retried(self):
        selection = self.selection()
        (self.root/'data/test.jsonl').write_text('corrupt test')
        with self.assertRaisesRegex(ValueError, 'claim retained'):
            claim_and_load_test(self.root, selection, 'failed-attempt')
        with self.assertRaises(FileExistsError):
            claim_and_load_test(self.root, selection, 'blind-retry')

    @unittest.skipIf(torch is None, 'Torch contract loading is verified on the server')
    def test_v2_checkpoint_load_inference_and_wrong_contract_rejection(self):
        from yixian.order_checkpoint import TRAINING_SOURCES, load_order_checkpoint
        from yixian.order_model import BoardOrderPolicy
        from yixian.order_evaluation import decode_own_prefix, torch_scorer
        from yixian.research import contract_digest
        project = Path(__file__).resolve().parents[1]
        config = json.loads((self.root/'config-11.json').read_text())
        vocabulary = [1, 2, 3]
        contract = {'schema_version': 2, 'scope': SCOPE, 'model': config['model'],
                    'dataset_manifest_sha256': self.plan['manifest_sha256'],
                    'source_sha256': {name: sha(project/name) for name in TRAINING_SOURCES},
                    'vocabulary_sha256': hashlib.sha256(json.dumps(vocabulary).encode()).hexdigest(),
                    'test_data_opened': False, 'split_sha256': {'train': 'x', 'validation': 'y'}}
        model = BoardOrderPolicy(4, **config['model'])
        packet = {'model': model.state_dict(), 'config': config, 'vocabulary': vocabulary,
                  'contract': contract, 'contract_digest': contract_digest(contract), 'step': 2}
        path = self.root/'real-torch-fixture.pt'
        torch.save(packet, path)
        loaded, metadata = load_order_checkpoint(path, root=project, expected_sha256=sha(path),
            expected_config=config, expected_manifest_sha256=self.plan['manifest_sha256'])
        prediction = decode_own_prefix([[2, 1, 1, 3, 0, 0, 0, 0]], torch_scorer(loaded, torch.device('cpu')))
        self.assertCountEqual(prediction[0], [2, 1, 1, 3])
        self.assertEqual(metadata['step'], 2)
        with self.assertRaisesRegex(ValueError, 'dataset'):
            load_order_checkpoint(path, root=project, expected_sha256=sha(path), expected_manifest_sha256='wrong')
        with self.assertRaisesRegex(ValueError, 'file hash'):
            load_order_checkpoint(path, root=project, expected_sha256='wrong')
        contract['source_sha256']['yixian/order_model.py'] = 'changed'
        packet['contract_digest'] = contract_digest(contract)
        torch.save(packet, path)
        with self.assertRaisesRegex(ValueError, 'source contract'):
            load_order_checkpoint(path, root=project, expected_sha256=sha(path))

    @unittest.skipIf(torch is None, 'Torch end-to-end evaluation is verified on the server')
    def test_final_entrypoint_reports_all_three_and_never_reselects_by_test(self):
        from tools import evaluate_longyao_holdout as evaluator
        from yixian.order_checkpoint import TRAINING_SOURCES
        from yixian.order_model import BoardOrderPolicy
        from yixian.research import contract_digest
        from yixian.memory import Memory
        project = Path(__file__).resolve().parents[1]
        for name in TRAINING_SOURCES:
            destination = self.root/name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(project/name, destination)
        manifest = json.loads((self.root/'data/manifest.json').read_text())
        for run in self.plan['runs']:
            config = json.loads((self.root/run['config']).read_text())
            model = BoardOrderPolicy(4, **config['model'])
            contract = {'schema_version': 2, 'scope': SCOPE, 'model': config['model'],
                'dataset_manifest_sha256': self.plan['manifest_sha256'],
                'source_sha256': {name: sha(project/name) for name in TRAINING_SOURCES},
                'vocabulary_sha256': hashlib.sha256(json.dumps([1, 2, 3]).encode()).hexdigest(),
                'test_data_opened': False, 'split_sha256': {role: manifest['split_sha256'][role] for role in ('train', 'validation')}}
            packet = {'model': model.state_dict(), 'config': config, 'vocabulary': [1, 2, 3],
                      'contract': contract, 'contract_digest': contract_digest(contract), 'step': 1}
            directory = self.root/run['run_dir']
            path = directory/'checkpoint-000001.pt'
            torch.save(packet, path)
            report = json.loads((directory/'report.json').read_text())
            report['selected_checkpoint_sha256'] = sha(path)
            write(directory/'report.json', report)
        selection_path = self.root/'selection.json'
        freeze_selection(self.root, self.root/'plan.json', selection_path)
        args = SimpleNamespace(selection=selection_path, selection_sha256=sha(selection_path),
                               out=self.root/'evaluation', device='cpu')
        previous_threads = torch.get_num_threads()
        self.addCleanup(torch.set_num_threads, previous_threads)
        with mock.patch.object(evaluator, 'ROOT', self.root), contextlib.redirect_stdout(io.StringIO()):
            evaluator.evaluate(args)
        result = json.loads((args.out/'report.json').read_text())
        self.assertEqual(result['models_evaluated'], 3)
        self.assertEqual(result['champion_seed'], 12)
        self.assertFalse(result['test_used_for_selection'])
        self.assertFalse(result['game_strength_evaluated'])
        self.assertTrue(Memory(self.root/'runs/research.sqlite').verify_integrity())
        args.out = self.root/'forbidden-repeat'
        with mock.patch.object(evaluator, 'ROOT', self.root), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(FileExistsError):
                evaluator.evaluate(args)
        self.assertTrue((args.out/'failure.json').exists())


if __name__ == '__main__':
    unittest.main()
