from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v28 as old,full_battle_v29 as current

class StillnessTests(unittest.TestCase):
    def args(self,ctx):
        return dict(first_player=0,seed='stillness-software',game_mode=3,season_mec=10,combat_context=ctx)

    def test_native_boundaries(self):
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',
            str(current.ROOT/'tests/current_stillness_v29_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout),{'passed':True,'scenarios':27})

    def test_frozen_values_and_mapping(self):
        f=current.extension_contract();family=f['families'][0]
        self.assertEqual([c['otherParams'] for c in family['cards']],[[1,20],[2,20],[3,20]])
        self.assertFalse(f['card_specific_opening']);self.assertFalse(f['training_label_allowed'])
        before=old.catalogue()[1];after=current.catalogue()[1]
        self.assertEqual({k:v for k,v in after.items() if k in before},before)
        self.assertEqual(set(after)-set(before),{4000098,4010098,4020098})

    def test_unaffected_complete_battle_unchanged(self):
        row,ctx=start_fixture();a=self.args(ctx)
        first=old.compile_start(row,**a);self.assertEqual(first,current.compile_start(row,**a))
        self.assertEqual(old.simulate_batch([first['battle']])['results'],current.simulate_batch([first['battle']])['results'])

    def test_complete_battle_and_outcome_isolation(self):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[4020098,0,0]
        before=deepcopy(row);c=current.compile_start(row,**self.args(ctx));self.assertEqual(row,before)
        row['outcome']={'hp_delta':999,'winner_snapshot_slot':'p2'}
        self.assertEqual(c,current.compile_start(row,**self.args(ctx)))
        r=current.simulate_batch([c['battle']])['results'][0]
        self.assertTrue(r['terminated']);self.assertFalse(r['used_randomness']);self.assertFalse(r['training_label_allowed'])
        self.assertEqual(r['stillness_v29']['events'][0]['raw_id'],4020098)
        self.assertEqual(r['trace'][0]['before'][0]['max_hp'],r['initial'][0]['max_hp'])
        self.assertEqual(r['trace'][0]['after'][0]['max_hp'],r['initial'][0]['max_hp']+20)

    def test_known_card_does_not_admit_unknown_effect_or_card(self):
        for key,value in [('xian_mo_strategies',[5001]),('board',[4020098,9999999,0])]:
            row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[4020098,0,0]
            row['players'][0]['candidate_start'][key]=value
            with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))

if __name__=='__main__':unittest.main()
