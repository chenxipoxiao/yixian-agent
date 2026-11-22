from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v31 as old,full_battle_v32 as current

class DreamEchoTests(unittest.TestCase):
    def fixture(self,hand=None):
        row,ctx=start_fixture()
        row['players'][0]['candidate_start']['board']=[10349,0,0]
        hand=[10434] if hand is None else hand
        ctx['players'][0]['hand_count']=len(hand)
        ctx['players'][0]['dream_echo_hand']={'origin':'publicData.lastRoundData.handCards','raw_cards':hand,
          'source_raw_sha256':row['source']['raw_sha256'],'environment_only':True}
        return row,ctx
    def args(self,ctx):
        return dict(first_player=0,seed='dream-echo-software',game_mode=3,season_mec=10,combat_context=ctx)
    def test_native_boundaries(self):
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_dream_echo_v32_probe.mjs')],
            capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout),{'passed':True,'scenarios':18})
    def test_values_and_aliases(self):
        f=current.extension_contract();self.assertEqual([c['hp_and_max_hp'] for c in f['cards']],[4,10])
        self.assertFalse(f['recorded_parameters_as_input']);self.assertFalse(f['random_selection_supported'])
        _,a,*_=old.catalogue();_,b,*_=current.catalogue()
        self.assertEqual({k:v for k,v in b.items() if k not in (349,10349)},a)
    def test_old_complete_battle_unchanged(self):
        row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx))
        self.assertEqual(a,b);self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
    def test_parameters_and_outcomes_not_inputs(self):
        row,ctx=self.fixture();before=deepcopy(row);c=current.compile_start(row,**self.args(ctx));self.assertEqual(row,before)
        row['outcome']={'recorded_hp_delta':999999,'winner_snapshot_slot':'p2'};ctx['battle_params']=[7020023,0,-1]
        self.assertEqual(c,current.compile_start(row,**self.args(ctx)))
        r=current.simulate_batch([c['battle']])['results'][0]
        self.assertTrue(r['terminated']);self.assertFalse(r['used_randomness']);self.assertFalse(r['training_label_allowed'])
        self.assertTrue(all(e['selected_raw']==10434 for e in r['dream_echo_v32']['events']))
    def test_missing_source_count_and_unmapped_rejected(self):
        for mutation in ['missing','source','count','unknown','unmapped']:
            row,ctx=self.fixture();p=ctx['players'][0]
            if mutation=='missing':del p['dream_echo_hand']
            if mutation=='source':p['dream_echo_hand']['source_raw_sha256']='wrong'
            if mutation=='count':p['hand_count']=8
            if mutation=='unknown':p['dream_echo_hand']['raw_cards']=[9999999]
            if mutation=='unmapped':p['dream_echo_hand']['raw_cards']=[433]
            with self.subTest(mutation=mutation),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
    def test_multiple_distinct_targets_rejected(self):
        row,ctx=self.fixture([10434,7020023])
        with self.assertRaisesRegex(current.UnresolvedBattle,'multiple_targets'):current.compile_start(row,**self.args(ctx))
    def test_empty_hand_cannot_copy_board(self):
        row,ctx=self.fixture([]);row['players'][0]['candidate_start']['board']=[7020023,10349,0]
        c=current.compile_start(row,**self.args(ctx));r=current.simulate_batch([c['battle']])['results'][0]
        self.assertTrue(r['terminated']);self.assertTrue(all(e['selected_raw'] is None for e in r['dream_echo_v32']['events']))
    def test_bridge_missing_hand_rejected(self):
        row,ctx=self.fixture();b=current.compile_start(row,**self.args(ctx))['battle'];del b['dream_echo']
        r=current.simulate_batch([b])['results'][0];self.assertEqual(r['unresolved_reason'],'dream_echo_unresolved:hand_context_required')

if __name__=='__main__':unittest.main()
