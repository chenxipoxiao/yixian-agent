"""Record-bound compiler/runtime checks. The real terminal is tested by batch only."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import unittest
from yixian import full_battle_v80 as old, full_battle_v81 as current
from yixian.combat_compiler_view_v81 import compiler_modules, isolated_compiler
from tests.test_current_start_context_v80r2 import fixture as software_fixture

ROOT = Path(__file__).resolve().parents[1]


class CloudParameterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads((ROOT / 'data/inspection/current-cloud-parameter-fixture-v81.json').read_text('utf8'))
        x = cls.fixture
        cls.args = dict(combat_context=x['combat_context'], first_player=x['first_player'],
                        seed=x['seed'], game_mode=3, season_mec=10)
        cls.compiled = current.compile_start(x['start'], **cls.args)

    def test_original_identity_and_input_are_preserved(self):
        x = deepcopy(self.fixture); saved = deepcopy(x)
        c = current.compile_start(x['start'], **{**self.args, 'combat_context': x['combat_context']})
        self.assertEqual(x, saved)
        self.assertEqual(c, self.compiled)
        self.assertEqual(c['battle']['players'][0]['cards'][3], '216011')
        self.assertEqual(c['battle']['cloud_sword_parameters']['stream'], [56])
        self.assertFalse(c['cloud_parameter_context_v81']['training_label_allowed'])
        self.assertFalse(c['cloud_parameter_context_v81']['server_hand_classifier_recovered'])

    def test_old_entrypoint_and_globals_remain_isolated(self):
        modules = compiler_modules(old)
        before = {name: (m.compile_start, getattr(m, 'BRIDGE', None))
                  for name, m in modules.items() if hasattr(m, 'compile_start')}
        for unused in range(2):
            with self.assertRaisesRegex(old.UnresolvedBattle, 'cloud_hand_composition_required'):
                old.compile_start(self.fixture['start'], **self.args)
            current.compile_start(self.fixture['start'], **self.args)
        self.assertEqual(before, {name: (modules[name].compile_start, getattr(modules[name], 'BRIDGE', None)) for name in before})
        self.assertIs(current.UnresolvedBattle, old.UnresolvedBattle)

    def test_unbound_and_forged_bindings_are_rejected(self):
        for kind in ['absent', 'new_hash', 'scope', 'hand_source', 'mixed_typed', 'mixed_paper']:
            ctx = deepcopy(self.fixture['combat_context'])
            if kind == 'absent': del ctx['cloud_sword_record']
            elif kind == 'new_hash': ctx['cloud_sword_record']['snapshot_sha256'] = 'f' * 64
            elif kind in ['scope', 'hand_source']: ctx['cloud_sword_record'][{'scope':'scope','hand_source':'hand_source_sha256'}[kind]] = 'changed'
            elif kind == 'mixed_typed': ctx['typed_parameter_record'] = {}
            else: ctx['falling_paper_record'] = {}
            with self.subTest(kind=kind), self.assertRaises(current.UnresolvedBattle):
                current.compile_start(self.fixture['start'], **{**self.args, 'combat_context': ctx})

    def test_start_mutations_cannot_borrow_the_record(self):
        for kind in ['board', 'exp', 'round', 'id', 'source', 'hand_count', 'ownership', 'mode', 'source_context']:
            row = deepcopy(self.fixture['start']); ctx = deepcopy(self.fixture['combat_context'])
            if kind == 'board': row['players'][0]['candidate_start']['board'].reverse()
            if kind == 'exp': row['players'][0]['candidate_start']['exp'] += 1
            if kind == 'round': row['round'] += 1
            if kind == 'id': row['id'] = 'different'
            if kind == 'source': row['source']['raw_sha256'] = 'changed'
            if kind == 'hand_count': ctx['players'][0]['hand_count'] += 1
            if kind == 'ownership': row['players'][0]['candidate_start']['talents'] = []
            if kind == 'mode': ctx['game_mode'] = 99
            if kind == 'source_context': ctx['source_raw_sha256'] = 'changed'
            with self.subTest(kind=kind), self.assertRaises(current.UnresolvedBattle):
                current.compile_start(row, **{**self.args, 'combat_context': ctx})

    def test_parameters_and_provenance_are_complete(self):
        for params in [None, [], [55], [56, 56], [True], [-1], [2147483648]]:
            ctx = deepcopy(self.fixture['combat_context']); ctx['battle_params'] = params
            with self.subTest(params=params), self.assertRaises(current.UnresolvedBattle):
                current.compile_start(self.fixture['start'], **{**self.args, 'combat_context': ctx})
        row = deepcopy(self.fixture['start']); row['battle_params_evidence']['entries'] += 1
        with self.assertRaisesRegex(current.UnresolvedBattle, 'source_parameter_mismatch'):
            current.compile_start(row, **self.args)

    def test_original_initiative_and_runtime_options_required(self):
        for override in [{'first_player':1}, {'first_player':None}, {'seed':'new'}, {'max_turns':8}, {'include_trace':False}]:
            with self.subTest(override=override), self.assertRaises(current.UnresolvedBattle):
                current.compile_start(self.fixture['start'], **{**self.args, **override})

    def test_terminal_comparison_fields_cannot_affect_start(self):
        row = deepcopy(self.fixture['start']); ctx = deepcopy(self.fixture['combat_context'])
        row['outcome'] = {'winner_snapshot_slot':'p2','recorded_hp_delta':999,'recorded_turns':999}
        ctx['players'][0]['after_talent_counters'] = {'27':{'count':999}}
        self.assertEqual(self.compiled, current.compile_start(row, **{**self.args,'combat_context':ctx}))

    def test_plain_old_and_isolated_compilers_agree(self):
        view = isolated_compiler(old)
        for paper, vase in [(False,False),(True,True)]:
            row, ctx = software_fixture(paper,vase)
            args = dict(combat_context=ctx,first_player=0,seed='software-v81-control',game_mode=3,season_mec=10)
            expected = old.compile_start(row, **args)
            self.assertEqual(expected, current.compile_start(row, **args))
            self.assertEqual(expected, view.compile_start(row, **args))

    def test_ordinary_software_battles_unchanged(self):
        row, ctx = software_fixture(False,False)
        b = current.compile_start(row,combat_context=ctx,first_player=0,seed='software-v81-control',game_mode=3,season_mec=10)['battle']
        self.assertEqual(old.simulate_batch([b])['results'], current.simulate_batch([b])['results'])

    def test_bridge_rejects_modified_and_rehashed_battles_before_execution(self):
        battles = []
        for rehash in [False,True]:
            for kind in ['hp','first','seed','limit']:
                b = deepcopy(self.compiled['battle'])
                if kind == 'hp': b['players'][0]['hp'] -= 1
                if kind == 'card': b['players'][0]['cards'][3] = '216012'
                if kind == 'first': b['first_player'] = 1
                if kind == 'seed': b['seed'] = 'changed'
                if kind == 'limit': b['max_turns'] -= 1
                if rehash: b['cloud_sword_parameters']['battle_sha256'] = current.digest_json({k:v for k,v in b.items() if k!='cloud_sword_parameters'})
                battles.append(b)
        for result in current.simulate_batch(battles)['results']:
            self.assertIn('cloud_parameter_unresolved:', result['unresolved_reason'])
            self.assertNotIn('winner', result)

    def test_card_tamper_rejected_by_earlier_original_identity_guard(self):
        from yixian.simulator import SimulatorError
        b = deepcopy(self.compiled['battle']); b['players'][0]['cards'][3] = '216012'
        b['cloud_sword_parameters']['battle_sha256'] = current.digest_json({k:v for k,v in b.items() if k!='cloud_sword_parameters'})
        with self.assertRaisesRegex(SimulatorError, 'Raw transform cards disagree with actual deck'):
            current.simulate_batch([b])

    def test_native_card_parameter_boundary(self):
        p = subprocess.run(['node',str(ROOT/'tests/current_cloud_parameter_v81_probe.mjs')],
            input=json.dumps(self.compiled['battle']),capture_output=True,text=True,encoding='utf8',cwd=ROOT,timeout=60)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        result = json.loads(p.stdout)
        self.assertGreaterEqual(result['software_boundary_scenarios'],20)
        self.assertEqual(result['real_replay_battles'],0)


if __name__ == '__main__': unittest.main()
