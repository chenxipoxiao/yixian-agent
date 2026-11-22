import copy
import unittest
from tests.test_full_battle import start_fixture,compile_fixture
from yixian import full_battle_v6 as old,full_battle_v7 as current

def compile_row(row,ctx):
    return current.compile_start(row,first_player=0,seed=7,game_mode=3,season_mec=10,combat_context=ctx)

class CurrentStartStatesTests(unittest.TestCase):
    def test_plants_preserved_outside_initial_hp_and_execute_at_opening(self):
        row,ctx=start_fixture();s=row['players'][0]['candidate_start']
        s['permanentBuffTempDatas'].update({'10010':2,'10011':3,'10013':2,'10014':5,'10019':1})
        original=copy.deepcopy(row);c=compile_row(row,ctx)
        self.assertEqual(original,row);self.assertEqual(c['battle']['players'][0]['hp'],40)
        c['battle']['max_turns']=1;r=current.simulate_batch([c['battle']])['results'][0]
        # Three extra attack and two enemy internal injury; own regen is full.
        self.assertEqual(r['trace'][0]['before'][0]['def'],5)
        self.assertEqual(r['players'][1]['hp'],34);self.assertEqual(r['players'][0]['def'],2)
        self.assertFalse(r['training_label_allowed'])

    def test_nonbattle_fates_do_not_reapply_acquisition_or_speed(self):
        row,ctx=start_fixture();s=row['players'][0]['candidate_start']
        s['talents']=[175,10175,115,178,191,270]
        s['permanentBuffTempDatas'].update({'10015':2,'10041':5,'10042':6,'10043':1,'10052':2,'20054':1,'20068':1,'369':8})
        before=copy.deepcopy(row);c=compile_row(row,ctx)
        self.assertEqual(before,row);self.assertEqual(c['battle']['players'][0]['hp'],40)
        self.assertEqual(c['effect_players'][0]['fates'],s['talents'])
        self.assertEqual(len(c['current_start_projection']['players'][0]['preparation_counters']),7)

    def test_innate_element_requires_public_selected_talent(self):
        for selected,element in [(10109,'metal'),(20109,'water'),(30109,'wood'),(40109,'fire'),(50109,'earth')]:
            row,ctx=start_fixture();row['players'][0]['candidate_start']['talents']=[selected,110]
            c=compile_row(row,ctx)
            self.assertEqual(c['battle']['players'][0]['innate_'+element+'_stacks'],1)
            self.assertEqual(c['current_start_projection']['players'][0]['innate_element_from_start_talent'],element)
        for fates in [[110],[10109,20109,110]]:
            row,ctx=start_fixture();row['players'][0]['candidate_start']['talents']=fates
            with self.assertRaisesRegex(current.UnresolvedBattle,'one_explicit'):compile_row(row,ctx)

    def test_wind_forging_current_cap_through_full_scheduler(self):
        row,ctx=start_fixture();s=row['players'][0]['candidate_start'];s['talents']=[267]
        s['board']=[1000104,1000104,1000104]
        c=compile_row(row,ctx);c['battle']['max_turns']=3
        r=current.simulate_batch([c['battle']])['results'][0]
        self.assertEqual(r['players'][0]['max_hp'],43)
        self.assertEqual(r['players'][0]['qi'],6)
        self.assertEqual(r['players'][1]['hp'],38)

    def test_old_result_including_trace_and_log_unchanged(self):
        b=compile_fixture()['battle'];a=old.simulate_batch([b])['results'][0]
        r=current.simulate_batch([b])['results'][0];r.pop('current_start_states')
        self.assertEqual(a,r)

    def test_unknown_and_nonpositive_plant_values_stay_unresolved(self):
        for key,value in [('9999',1),('10010',0),('10013',-1),('20054',True)]:
            row,ctx=start_fixture();row['players'][0]['candidate_start']['permanentBuffTempDatas'][key]=value
            with self.assertRaises(current.UnresolvedBattle):compile_row(row,ctx)

    def test_recorded_result_and_after_fields_never_change_input(self):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['talents']=[267]
        before=compile_row(row,ctx)
        row['outcome']={'recorded_hp_delta':999,'winner_snapshot_slot':'p2'}
        ctx['players'][0]['after_talent_counters']={'267':999}
        self.assertEqual(before,compile_row(row,ctx))
