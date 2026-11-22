from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v30 as old,full_battle_v31 as current

class EchoFormationTests(unittest.TestCase):
    def args(self,ctx):
        return dict(first_player=0,seed='echo-formation-software',game_mode=3,season_mec=10,combat_context=ctx)

    def test_native_boundaries(self):
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',
            str(current.ROOT/'tests/current_echo_formation_v31_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout),{'passed':True,'scenarios':28})

    def test_frozen_values_and_mapping_unchanged(self):
        f=current.extension_contract()
        self.assertEqual([c['hp_and_max_hp'] for c in f['cards']],[2,5,8])
        self.assertEqual([c['upgrade_times'] for c in f['cards']],[0,1,2])
        self.assertFalse(f['training_label_allowed'])
        self.assertFalse(f['dream_echo_supported'])
        self.assertEqual(current.catalogue(),old.catalogue())

    def test_old_complete_battle_unchanged(self):
        row,ctx=start_fixture();a=self.args(ctx)
        first=old.compile_start(row,**a);self.assertEqual(first,current.compile_start(row,**a))
        self.assertEqual(old.simulate_batch([first['battle']])['results'],current.simulate_batch([first['battle']])['results'])

    def test_complete_battle_outcome_isolation(self):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[4020098,8020012,4020106]
        before=deepcopy(row);c=current.compile_start(row,**self.args(ctx));self.assertEqual(row,before)
        row['outcome']={'hp_delta':999,'winner_snapshot_slot':'p2'}
        self.assertEqual(c,current.compile_start(row,**self.args(ctx)))
        r=current.simulate_batch([c['battle']])['results'][0]
        self.assertTrue(r['terminated']);self.assertFalse(r['used_randomness']);self.assertFalse(r['training_label_allowed'])
        self.assertTrue(r['echo_formation_v31']['events']);self.assertTrue(r['stillness_v29']['events'])

    def test_unknown_content_still_rejected(self):
        for key,value in [('xian_mo_strategies',[5001]),('board',[8020012,9999999,0])]:
            row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[8020012,0,0]
            row['players'][0]['candidate_start'][key]=value
            with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))

if __name__=='__main__':unittest.main()
