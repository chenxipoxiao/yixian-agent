from copy import deepcopy
import json
import shutil
import subprocess
import unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v23 as old, full_battle_v24 as current


class FullMoonTests(unittest.TestCase):
    def test_native_boundaries(self):
        run=subprocess.run([shutil.which('node'),'--experimental-default-type=module',
            str(current.ROOT/'tests/current_full_moon_v24_probe.mjs')],
            capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(run.returncode,0,run.stderr)
        # 5 agility values × 2 requests × 2 limits × 2 entangle values +14.
        self.assertEqual(json.loads(run.stdout),{'passed':True,'scenarios':54})

    def test_no_ownership_is_exact_compiler_and_full_result_regression(self):
        row,ctx=start_fixture()
        args=dict(first_player=0,seed='full-moon-software',game_mode=3,season_mec=10,combat_context=ctx)
        expected=old.compile_start(row,**args)
        self.assertEqual(current.compile_start(row,**args),expected)
        self.assertEqual(current.simulate_batch([expected['battle']])['results'],
                         old.simulate_batch([expected['battle']])['results'])

    def test_ownership_preserved_without_mutation_or_outcome_inputs(self):
        row,ctx=start_fixture();row['players'][1]['candidate_start']['xian_mo_strategies']=[7065]
        original=deepcopy(row)
        args=dict(first_player=1,seed='full-moon-software',game_mode=3,season_mec=10,combat_context=ctx)
        result=current.compile_start(row,**args)
        self.assertEqual(row,original)
        self.assertEqual(result['battle']['season_full_moon'],{'players':[[],[7065]]})
        self.assertEqual(result['effect_players'][1]['season_choices'],[7065])
        self.assertFalse(result['training_label_allowed'])
        row['outcome']={'winner_snapshot_slot':'p1','recorded_hp_delta':9999}
        self.assertEqual(current.compile_start(row,**args),result)
        with self.assertRaisesRegex(old.UnresolvedBattle,'unsupported_season_combat:7065'):
            old.compile_start(row,**args)

    def test_duplicate_or_unknown_effect_still_rejected(self):
        for ids in ([7065,7065],[7065,999999]):
            row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=ids
            with self.assertRaises(current.UnresolvedBattle):
                current.compile_start(row,first_player=0,seed='full-moon-software',
                    game_mode=3,season_mec=10,combat_context=ctx)

    def test_bridge_rejects_invented_or_duplicate_ownership(self):
        row,ctx=start_fixture()
        battle=current.compile_start(row,first_player=0,seed='full-moon-software',
            game_mode=3,season_mec=10,combat_context=ctx)['battle']
        for value in ({'players':[[7065,7065],[]]}, {'players':[[348],[]]}):
            battle['season_full_moon']=value
            with self.assertRaisesRegex(current.SimulatorError,'ownership'):
                current.simulate_batch([battle])

    def test_fixed_version_contract(self):
        facts=current.extension_contract()
        self.assertEqual(facts['strategy']['id'],7065)
        self.assertEqual(facts['strategy']['otherParams'],[9])
        self.assertEqual(facts['version'],'001.0008.0005')
        self.assertFalse(facts['training_label_allowed'])


if __name__=='__main__':unittest.main()
