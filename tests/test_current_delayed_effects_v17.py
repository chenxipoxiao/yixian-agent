"""Client delayed-effect timing, fail-closed inputs and full-scheduler regressions."""
from copy import deepcopy
import json
import shutil
import subprocess
import unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v16 as old, full_battle_v17 as current
from yixian.simulator import SimulatorError


class DelayedEffectsTests(unittest.TestCase):
    def compile(self,raw=0,turns=1):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=raw
        return current.compile_start(row,first_player=0,seed='software-v17',game_mode=3,
            season_mec=10,combat_context=ctx,max_turns=turns)

    def test_native_primitive_boundaries(self):
        r=subprocess.run([shutil.which('node'),'--experimental-default-type=module',
            str(current.ROOT/'tests/current_delayed_effects_v17_probe.mjs')],
            capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertTrue(json.loads(r.stdout)['passed'])

    def test_nine_grades_preserve_the_previous_mapping(self):
        a=old.catalogue()[1];b=current.catalogue()[1]
        self.assertEqual(len(b)-len(a),9);self.assertTrue(all(b[k]==v for k,v in a.items()))

    def test_damage_copy_is_exactly_native_plus_one_ordered_hook(self):
        native=(current.ROOT/'external/yisim/gamestate_full.js').read_text(encoding='utf8')
        a=native.index('    deal_damage_inner(');b=native.index('    deal_damage(dmg)',a)
        expected=native[a:b].strip()
        new=(current.ROOT/'tools/current_delayed_damage_v17.mjs').read_text(encoding='utf8')
        a=new.index('    game.deal_damage_inner=function(');body=new[a:new.rfind('}\n')].strip()
        body=body.replace('game.deal_damage_inner=function(', 'deal_damage_inner(',1).removesuffix(';')
        hook='            this.current_delayed_after_attack(my_idx, damage_actually_dealt_to_hp);\n'
        self.assertEqual(body.count(hook),1);self.assertEqual(body.replace(hook,''),expected)

    def test_old_completed_battle_is_identical(self):
        battle=self.compile(0,64)['battle']
        self.assertEqual(old.simulate_batch([battle])['results'],current.simulate_batch([battle])['results'])

    def test_scheduler_defers_new_wood_effect_to_later_card(self):
        battle=self.compile(7000112,1)['battle'];battle['players'][0]['activate_wood_spirit_stacks']=1
        first=current.simulate_batch([battle])['results'][0]
        self.assertEqual(first['players'][1]['hp'],40)
        battle['max_turns']=3
        later=current.simulate_batch([battle])['results'][0]
        self.assertTrue(any('current delayed 777 steal request 1' in x for x in later['log']))
        self.assertEqual(sum('current delayed 777' in x for x in later['log']),1)

    def test_earth_chase_reaches_next_card_with_effect_armed(self):
        battle=self.compile(7000114,1)['battle'];battle['players'][0]['activate_earth_spirit_stacks']=1
        result=current.simulate_batch([battle])['results'][0]
        self.assertTrue(any('current delayed 779 from HP loss 3 grants defense 1' in x for x in result['log']))
        self.assertEqual(result['players'][0]['def'],1)

    def test_new_battle_reaches_terminal_but_never_emits_training_label(self):
        battle=self.compile(7000112,64)['battle'];battle['players'][0]['activate_wood_spirit_stacks']=1
        result=current.simulate_batch([battle])['results'][0]
        self.assertTrue(result['terminated']);self.assertFalse(result['truncated'])
        self.assertFalse(result['training_label_allowed']);self.assertFalse(result['legacy_destiny_settlement_applied'])

    def test_no_replay_outcome_inputs_or_guessed_permanent_counters(self):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=7000112
        args=dict(first_player=0,seed='software',game_mode=3,season_mec=10,combat_context=ctx)
        snapshot=deepcopy(row);result=current.compile_start(row,**args);self.assertEqual(row,snapshot)
        row['outcome']={'recorded_hp_delta':98765};self.assertEqual(current.compile_start(row,**args),result)
        row['players'][0]['candidate_start']['permanentBuffTempDatas']['777']=3
        with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**args)

    def test_old_version_rejects_new_card(self):
        with self.assertRaisesRegex(SimulatorError,'Unimplemented card'):
            old.simulate_batch([self.compile(7000112)['battle']])

if __name__=='__main__':unittest.main()
