import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v15 as current


class CurrentQiStanceTests(unittest.TestCase):
    def compile(self,fates,character=4000001,first=0):
        row,ctx=start_fixture();row['players'][0]['character_id']=character
        row['players'][0]['candidate_start']['talents']=fates
        row['players'][0]['candidate_start']['board']=[1000025,0,0]
        return current.compile_start(row,combat_context=ctx,game_mode=3,season_mec=10,
            seed='software-only',first_player=first,max_turns=1)['battle']

    def test_missing_qi_spends_only_hp_even_with_no_physique(self):
        b=self.compile([153]);b['players'][0]['max_hp']=45
        r=current.simulate_batch([b])['results'][0]
        self.assertEqual((r['players'][0]['hp'],r['players'][0]['max_hp'],r['players'][0]['def']),(37,45,8))

    def test_hp_must_be_strictly_greater_than_payment(self):
        bs=[]
        for hp in [2,3,4]:
            b=self.compile([153]);b['players'][0]['hp']=hp;bs.append(b)
        results=current.simulate_batch(bs)['results']
        self.assertEqual([(r['players'][0]['hp'],r['players'][0]['qi'],r['players'][0]['def']) for r in results],[(2,1,0),(3,1,0),(1,0,8)])

    def test_available_qi_requires_no_hp_payment(self):
        b=self.compile([153]);b['players'][0]['qi']=1
        r=current.simulate_batch([b])['results'][0]
        self.assertEqual((r['players'][0]['hp'],r['players'][0]['qi'],r['players'][0]['def']),(40,0,8))

    def test_base_character_stance_is_fist_and_indomitable_reduces_attack(self):
        b=self.compile([206],character=4000005,first=1)
        self.assertEqual(b['players'][0]['stance'],1)
        r=current.simulate_batch([b])['results'][0]
        self.assertEqual(r['players'][0]['hp'],38)

    def test_fist_force_gain_only_grants_agility_once_per_turn(self):
        script="""import {GameState,ready} from './gamestate_full.js';await ready;const g=new GameState();
        const p=g.players[0];p.stance=1;p.surge_of_qi_stacks=1;
        g.increase_idx_force(0,1);g.increase_idx_force(0,1);console.log(p.agility);"""
        self.assertEqual(self.node(script),2)

    def test_stick_chase_grants_one_qi(self):
        script="""import {GameState,ready} from './gamestate_full.js';
        import {installCurrentQiPayment} from '../../tools/current_qi_payment_v15.mjs';await ready;
        const g=new GameState();installCurrentQiPayment(g);g.players.forEach(p=>{p.hp=40;p.max_hp=40;p.cards=['601011','601011','601011'];});
        g.start_of_game_setup();const p=g.players[0];p.stance=-1;p.surge_of_qi_stacks=1;p.agility=10;
        g.sim_turn();console.log(p.qi);"""
        self.assertEqual(self.node(script),1)

    def node(self,script):
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module','--input-type=module','-e',script],cwd=current.ROOT/'external/yisim',capture_output=True,text=True,encoding='utf8',check=True)
        return json.loads(p.stdout)

    def test_unverified_stance_ownership_still_blocks(self):
        with self.assertRaisesRegex(ValueError,'Non-native stance'):self.compile([209],character=1000003)

    def test_copied_scheduler_matches_registered_single_branch_edit(self):
        s=(current.ROOT/'external/yisim/gamestate_full.js').read_text(encoding='utf8');a=s.index('    sim_turn() {')
        m=re.search(r'\n    [a-zA-Z_][a-zA-Z_0-9]*\([^\n]*\) \{',s[a+1:]);old=s[a:a+1+m.start()]
        patched=(current.ROOT/'tools/current_qi_payment_v15.mjs').read_text(encoding='utf8')
        patched=patched[patched.index('    game.sim_turn=function() {'):].rsplit(';\n}',1)[0].replace('    game.sim_turn=function() {','    sim_turn() {',1)
        facts=current.extension_contract()
        self.assertEqual(hashlib.sha256(old.encode()).hexdigest(),facts['base_sim_turn_sha256'])
        self.assertEqual(hashlib.sha256(patched.encode()).hexdigest(),facts['patched_method_sha256'])
