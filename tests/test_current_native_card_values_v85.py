from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v84 as old,full_battle_v85 as new
from yixian.combat_validation_batch_v9 import review_case
from yixian.terminal_damage_v47 import calculate_terminal_damage

class CurrentCardValuesTests(unittest.TestCase):
    def compile(self,engine,row,ctx,first=0):
        return engine.compile_start(row,first_player=first,seed='values-v85-software',
            game_mode=3,season_mec=10,combat_context=ctx)
    def test_real_scheduler_and_body_boundaries(self):
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',
            str(new.ROOT/'tests/current_native_card_values_v85_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        d=json.loads(p.stdout);self.assertTrue(d['passed']);self.assertEqual(d['scenarios'],11)
    def test_start_inputs_and_previous_compiler_are_unchanged(self):
        for raw in [174,3000012,3010012,3020012,50,10050,20050]:
            row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=raw;saved=deepcopy(row)
            a=self.compile(old,row,ctx);b=self.compile(new,row,ctx)
            self.assertEqual(a,b);self.assertEqual(saved,row)
    def test_terminal_and_future_do_not_change_input(self):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=50
        a=self.compile(new,row,ctx);row['outcome']={'recorded_hp_delta':9999,'winner_snapshot_slot':'p2'}
        ctx['players'][0]['after_talent_counters']={'204':999}
        self.assertEqual(a,self.compile(new,row,ctx))
    def test_non_target_full_battle_unchanged(self):
        row,ctx=start_fixture();c=self.compile(new,row,ctx)
        self.assertEqual(old.simulate_batch([c['battle']])['results'],new.simulate_batch([c['battle']])['results'])
    def test_axe_full_battles_both_initiatives_and_settlement(self):
        compiled=[]
        for first in [0,1]:
            row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=174
            compiled.append(self.compile(new,row,ctx,first))
        for c,r in zip(compiled,new.simulate_batch([c['battle'] for c in compiled])['results']):
            self.assertTrue(r['terminated']);self.assertFalse(r['truncated']);self.assertFalse(r['training_label_allowed'])
            self.assertTrue(calculate_terminal_damage(c,r)['resolved'])
    def test_unknown_inputs_remain_blocked(self):
        for key,value in [('talents',None),('board',[50,999999999,0]),('xian_mo_strategies',[999999999])]:
            row,ctx=start_fixture();row['players'][0]['candidate_start'][key]=value
            with self.assertRaises((new.UnresolvedBattle,ValueError)):self.compile(new,row,ctx)
    def test_review_rejects_undeclared_or_start_changes(self):
        a={'compiled':{},'simulation':{'initial':[]},'all_four_match':False}
        b=deepcopy(a);b['compiled']['unrelated']=1
        self.assertEqual(review_case(a,b,selected=False)['kind'],'unselected_changed')
        self.assertEqual(review_case(a,b,selected=True)['kind'],'starting_input_changed')

if __name__=='__main__':unittest.main()
