from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v32 as old,full_battle_v33 as current

class DragonTailTests(unittest.TestCase):
    def args(self,ctx):
        return dict(first_player=0,seed='dragon-tail-software',game_mode=3,season_mec=10,combat_context=ctx)
    def test_native_boundaries(self):
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_dragon_tail_v33_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout),{'passed':True,'scenarios':27})
    def test_parameters_and_aliases(self):
        facts=current.extension_contract();self.assertEqual([c['heal'] for c in facts['cards']],[7,11,15])
        self.assertEqual([c['divisor'] for c in facts['cards']],[2,2,2]);self.assertFalse(facts['training_label_allowed'])
        _,a,*_=old.catalogue();_,b,*_=current.catalogue()
        self.assertEqual({k:v for k,v in b.items() if k not in (4000103,4010103,4020103)},a)
    def test_prior_complete_battle_unchanged(self):
        row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx))
        self.assertEqual(a,b);self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
    def test_recorded_outcome_not_input(self):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[4000103,0,0]
        saved=deepcopy(row);a=current.compile_start(row,**self.args(ctx));self.assertEqual(row,saved)
        row['outcome']={'recorded_hp_delta':999999,'winner_snapshot_slot':'p2'};ctx['battle_params']=[4,8,99]
        self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
        out=current.simulate_batch([a['battle']])['results'][0]
        self.assertTrue(out['terminated']);self.assertFalse(out['training_label_allowed']);self.assertIn('dragon_tail_v33',out)
    def test_all_three_grades_execute(self):
        for raw in (4000103,4010103,4020103):
            with self.subTest(raw=raw):
                row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[raw,0,0]
                b=current.compile_start(row,**self.args(ctx))['battle'];r=current.simulate_batch([b])['results'][0]
                self.assertTrue(r['terminated']);self.assertEqual(r['dragon_tail_v33']['events'][0]['raw_id'],raw)
    def test_truncated_not_terminal(self):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[4000103,0,0]
        b=current.compile_start(row,**self.args(ctx))['battle'];b['max_turns']=1
        r=current.simulate_batch([b])['results'][0]
        self.assertTrue(r['truncated']);self.assertIsNone(r['winner']);self.assertIsNone(r['hp_delta'])

if __name__=='__main__':unittest.main()
