from copy import deepcopy
import json
import shutil
import subprocess
import unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v14 as current


class CurrentAnimalCardTests(unittest.TestCase):
    def battle(self,raw,turns=1):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[raw,0,0]
        return current.compile_start(row,combat_context=ctx,game_mode=3,season_mec=10,
            seed='software-only',first_player=0,max_turns=turns)['battle']

    def test_badger_damage_is_not_attack_and_respects_defense(self):
        battle=self.battle(430);battle['players'][0]['increase_atk']=100
        battle['players'][1]['def']=4
        result=current.simulate_batch([battle])['results'][0]
        self.assertEqual(result['players'][1]['hp'],36)
        self.assertEqual(result['players'][1]['def'],0)
        self.assertEqual(result['pending_animal_match_effects'][0][0]['kind'],'badger')

    def test_turtle_adds_maximum_without_healing(self):
        result=current.simulate_batch([self.battle(431)])['results'][0]
        self.assertEqual((result['players'][0]['hp'],result['players'][0]['max_hp'],result['players'][0]['def']),(40,41,11))

    def test_rat_gains_qi_and_defense_not_immediate_resource_cards(self):
        result=current.simulate_batch([self.battle(432)])['results'][0]
        self.assertEqual((result['players'][0]['qi'],result['players'][0]['def']),(1,8))
        self.assertEqual(len(result['players'][0]['cards']),3)
        self.assertEqual(result['initial'][0]['cultivation'],result['players'][0]['cultivation'])

    def test_parrot_heals_to_cap_and_copying_is_pending_without_combat_rng(self):
        battle=self.battle(434);battle['players'][0]['max_hp']=45
        before=deepcopy(battle);result=current.simulate_batch([battle])['results'][0]
        self.assertEqual(result['players'][0]['hp'],45);self.assertFalse(result['used_randomness'])
        self.assertEqual(battle,before)
        self.assertFalse(result['pending_animal_match_effects'][0][0]['future_match_state_mutated'])

    def test_consumed_animal_is_not_played_on_second_deck_cycle(self):
        result=current.simulate_batch([self.battle(431,turns=12)])['results'][0]
        self.assertEqual(len(result['pending_animal_match_effects'][0]),1)
        self.assertEqual(result['players'][0]['max_hp'],41)

    def test_three_grades_and_source_contract_remain_explicit(self):
        facts=current.extension_contract();cards,mapping,_,_=current.catalogue()
        self.assertEqual(sum(len(f['cards']) for f in facts['families']),12)
        for f in facts['families']:
            results=current.simulate_batch([self.battle(c['id']) for c in f['cards']])['results']
            for c,result in zip(f['cards'],results):
                self.assertEqual(result['initial'][0]['cards'][0],mapping[c['id']])
                self.assertEqual(result['pending_animal_match_effects'][0][0]['params'],c['otherParams'])

    def test_yeying_classification_is_not_conditional_on_fate193(self):
        battle=self.battle(213)
        result=current.simulate_batch([battle])['results'][0]
        self.assertEqual(result['players'][1]['hp'],34)
        self.assertEqual(result['players'][0]['def'],9)
        script="""import {GameState,ready} from './gamestate_full.js';import {swogi} from './card_info.js';
        import {registerCurrentAnimalCards} from '../../tools/current_animal_cards_v14.mjs';
        await ready;registerCurrentAnimalCards(process.argv[1],swogi);const g=new GameState();
        console.log(JSON.stringify(['is_cloud_sword','is_unrestrained_sword','is_spirit_sword','is_sword_formation'].map(k=>g[k]('615031'))));"""
        run=subprocess.run([shutil.which('node'),'--experimental-default-type=module','--input-type=module','-e',script,str(current.ROOT)],cwd=current.ROOT/'external/yisim',capture_output=True,text=True,encoding='utf8',check=True)
        self.assertEqual(json.loads(run.stdout),[True]*4)
