import copy
import unittest
from tests.test_full_battle import start_fixture,compile_fixture
from yixian import full_battle_v8 as old,full_battle_v9 as current

def compile_card(fates,counter=None):
    row,ctx=start_fixture();s=row['players'][0]['candidate_start']
    s['board']=[19,0,0];s['talents']=fates
    if counter is not None:s['talentTempDatas']['92']=counter
    return current.compile_start(row,first_player=0,seed='software-only',game_mode=3,season_mec=10,combat_context=ctx)

class ClearHeartTests(unittest.TestCase):
    def test_explicit_counter_and_forge_effects_in_full_turn(self):
        for fates,counter,damage,qi,defense in [
            ([92],5,12,0,0),([92,10094],5,18,0,0),
            ([92,10094,30096],5,20,0,0),
            ([92,20093,20095],5,10,0,9),
            ([92,10095,30095],5,20,1,0),
            ([92,10095,30095,30096],5,28,1,0),
            ([92,30094],5,10,0,0),([92,20093,20096],0,1,0,9)]:
            c=compile_card(fates,counter);c['battle']['max_turns']=1
            c['battle']['players'][1].update(hp=100,max_hp=100)
            r=current.simulate_batch([c['battle']])['results'][0]
            with self.subTest(fates=fates):
                self.assertEqual(r['players'][1]['hp'],100-damage)
                self.assertEqual(r['players'][0]['qi'],qi)
                self.assertEqual(r['players'][0]['def'],defense)

    def test_explicit_empty_counter_is_source_defined_no_bonus(self):
        c=compile_card([92]);self.assertEqual(c['battle']['players'][0]['swordsmith_stacks'],0)
        self.assertFalse(c['current_clear_heart']['players'][0]['counter_key_present'])

    def test_invalid_counter_not_coerced_or_inferred(self):
        for value in [-1,19,True,'7',{'swordsmith_attack_bonus':7}]:
            with self.subTest(value=value),self.assertRaises(current.UnresolvedBattle):compile_card([92],value)

    def test_original_input_and_effect_counters_preserved(self):
        row,ctx=start_fixture();s=row['players'][0]['candidate_start'];s['board']=[19,0,0]
        s['talents']=[92,10094];s['talentTempDatas']={'92':7};before=copy.deepcopy(row)
        c=current.compile_start(row,first_player=0,seed=1,game_mode=3,season_mec=10,combat_context=ctx)
        self.assertEqual(row,before);self.assertEqual(c['effect_players'][0]['talent_counters'],{'92':7})
        self.assertEqual(c['effect_players'][0]['fates'],[92,10094])

    def test_unaffected_battle_trace_unchanged(self):
        b=compile_fixture()['battle'];a=old.simulate_batch([b])['results'][0]
        r=current.simulate_batch([b])['results'][0];r.pop('current_clear_heart')
        self.assertEqual(a,r)
