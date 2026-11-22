from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v25 as old,full_battle_v26 as current

class YanChenCardTests(unittest.TestCase):
    def test_native_card_and_scheduler_boundaries(self):
        run=subprocess.run([shutil.which('node'),'--experimental-default-type=module',
            str(current.ROOT/'tests/current_yan_chen_cards_v26_probe.mjs')],
            text=True,capture_output=True,encoding='utf8',timeout=60)
        self.assertEqual(run.returncode,0,run.stderr)
        data=json.loads(run.stdout);self.assertTrue(data['passed'])
        self.assertIn('qi-pays-chased-five-thunders',data['scenarios'])
        self.assertIn('entangle-retains-qi',data['scenarios'])
        self.assertIn('global-and-other-game-isolation',data['scenarios'])

    def test_initial_state_and_terminal_field_isolation(self):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[28,29,4010046]
        args=dict(first_player=0,seed='software-yan-chen',game_mode=3,season_mec=10,combat_context=ctx)
        expected=old.compile_start(row,**args)
        self.assertEqual(current.compile_start(row,**args),expected)
        polluted=deepcopy(row);polluted['outcome']={'recorded_hp_delta':10000,'winner_snapshot_slot':'p2'}
        self.assertEqual(current.compile_start(polluted,**args),expected)

    def test_unaffected_complete_battle_unchanged(self):
        row,ctx=start_fixture()
        battle=current.compile_start(row,first_player=0,seed='software-yan-chen',game_mode=3,
            season_mec=10,combat_context=ctx)['battle']
        self.assertEqual(current.simulate_batch([battle])['results'],old.simulate_batch([battle])['results'])

    def test_fixed_current_version_contract(self):
        facts=current.extension_contract()
        self.assertEqual(facts['version'],'001.0008.0005')
        self.assertEqual([c['anima'] for c in facts['fury_thunder']['cards']],[1,1,2])
        self.assertEqual([c['otherParams'][0] for c in facts['ultimate_hexagram']['cards']],[1,3,5])
        self.assertFalse(facts['terminal_adjustment']);self.assertFalse(facts['training_label_allowed'])

if __name__=='__main__':unittest.main()
