from copy import deepcopy
import json
import shutil
import subprocess
import unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v20 as old, full_battle_v21 as current


class TransformEngravingTests(unittest.TestCase):
    def fixture(self,identifier=13003,board=None):
        row,ctx=start_fixture()
        row['players'][0]['candidate_start']['board']=board or [1000004,0,0]
        row['players'][0]['candidate_start']['xian_mo_strategies']=[identifier]
        ctx['players'][0]['season_engraving_input']={'origin':current.ORIGIN,
            'selected_strategy_ids':[identifier],'slots':{str(identifier):0}}
        return row,ctx

    def compile(self,row,ctx):
        return current.compile_start(row,first_player=0,seed='software-v21',
            game_mode=3,season_mec=10,combat_context=ctx)

    def test_native_boundaries(self):
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',
            str(current.ROOT/'tests/current_engraving_effects_v21_probe.mjs')],
            capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertTrue(json.loads(p.stdout)['passed'])

    def test_full_combat_and_preserved_input(self):
        row,ctx=self.fixture();before=deepcopy((row,ctx));c=self.compile(row,ctx)
        self.assertEqual((row,ctx),before)
        self.assertEqual(c['battle']['season_transform_cards']['players'],[[1000004,0,0],[0,0,0]])
        r=current.simulate_batch([c['battle']])['results'][0]
        self.assertTrue(r['terminated']);self.assertFalse(r['training_label_allowed'])
        self.assertEqual(sum('current engraving 13003 first use' in x for x in r['log']),1)

    def test_prior_eight_effect_results_preserved(self):
        for identifier in sorted(old.SUPPORTED):
            row,ctx=self.fixture(identifier);battle=self.compile(row,ctx)['battle']
            self.assertNotIn('season_transform_cards',battle)
            self.assertEqual(old.simulate_batch([battle])['results'],current.simulate_batch([battle])['results'])

    def test_old_contract_rejects_new_mechanics(self):
        for identifier in [13003,13007]:
            row,ctx=self.fixture(identifier)
            with self.assertRaisesRegex(old.UnresolvedBattle,'unsupported_season_combat'):
                old.compile_start(row,first_player=0,seed='software',game_mode=3,season_mec=10,combat_context=ctx)

    def test_missing_selected_grid_stays_unknown(self):
        for identifier in [13003,13007]:
            row,ctx=self.fixture(identifier);ctx['players'][0]['season_engraving_input']['slots']={}
            with self.assertRaisesRegex(current.UnresolvedBattle,'engraving_preparation_slot_missing'):
                self.compile(row,ctx)

    def test_no_result_or_usage_counter_backflow(self):
        row,ctx=self.fixture();before=self.compile(row,ctx)
        row['outcome']={'recorded_hp_delta':999,'recorded_destiny_damage':999}
        ctx['players'][0]['after_talent_counters']={'560':999,'13003':999}
        self.assertEqual(self.compile(row,ctx),before)

    def test_unmapped_transform_returns_unresolved_without_false_winner(self):
        row,ctx=self.fixture(13007,[0,0,0]);row['players'][1]['candidate_start']['board']=[20019,0,0]
        battle=self.compile(row,ctx)['battle']
        good=self.compile(*self.fixture())['battle']
        r=current.simulate_batch([battle,good])['results']
        self.assertEqual(r[0],{'unresolved_reason':'engraving_transform_unresolved:unmapped_target:10019',
                              'training_label_allowed':False})
        self.assertTrue(r[1]['terminated'])


if __name__=='__main__':unittest.main()
