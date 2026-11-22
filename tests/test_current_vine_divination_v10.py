import copy
import unittest
from tests.test_full_battle import compile_fixture
from yixian import full_battle_v9 as old,full_battle_v10 as current

class VineDivinationTests(unittest.TestCase):
    def test_current_qi_and_growth_for_all_grades(self):
        inputs=[];expected=[]
        for grade in range(3):
            for prefix in ['37503','37504','37502']:
                b=compile_fixture()['battle'];b['max_turns']=1;b['players'][0]['cards'][0]=prefix+str(grade+1)
                inputs.append(b);expected.append((prefix,grade))
        original=copy.deepcopy(inputs)
        for (prefix,g),r in zip(expected,current.simulate_batch(inputs)['results']):
            with self.subTest(prefix=prefix,grade=g):
                p=r['players'][0]
                if prefix=='37502':self.assertEqual((p['hp'],p['max_hp']),(50+g*5,50+g*5))
                else:self.assertEqual(p['qi'],3+g*2)
                self.assertFalse(r['training_label_allowed'])
        self.assertEqual(inputs,original)

    def test_vine_applies_current_layers_then_actual_opponent_chases(self):
        # Chase-capable Cloud Sword - Dragon Roam against an unshielded target.
        inputs=[]
        for grade in range(3):
            b=compile_fixture()['battle'];b['max_turns']=2
            b['players'][0]['cards'][0]='36503'+str(grade+1);b['players'][0]['qi']=1
            b['players'][1]['cards']=['115011','601011','601011'];inputs.append(b)
        results=current.simulate_batch(inputs)['results']
        self.assertEqual([r['players'][1]['next_card_index'] for r in results],[2,1,1])
        self.assertEqual(results[0]['players'][0]['hp'],33)
        self.assertEqual(results[1]['players'][0]['hp'],36)
        self.assertEqual(results[2]['players'][0]['hp'],36)

    def test_unaffected_battle_unchanged(self):
        b=compile_fixture()['battle'];a=old.simulate_batch([b])['results'][0]
        r=current.simulate_batch([b])['results'][0];r.pop('current_vine_divination')
        self.assertEqual(a,r)
