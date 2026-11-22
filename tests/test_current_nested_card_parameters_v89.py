from copy import deepcopy
import json,shutil,subprocess,unittest
from yixian import full_battle_v89 as current,full_battle_v88r2 as old
from yixian.combat_report_comparison_v1 import cases_equal

class NestedCardParametersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=current.ROOT;cls.facts=current.extension_contract()
        cls.rows={r['id']:r for r in map(json.loads,(root/'runs/calibration/20261111T1616-longyao-train-pilot/evidence-rounds.jsonl').read_text('utf8').splitlines())}
        cls.ctx=json.loads((root/'runs/stages/20261114T155500Z-s2-cloud-parameter-batch/combat-context-v81-bound.json').read_text('utf8'))
        cls.rid=next(iter(cls.facts['admitted_records']));cls.tables=current.catalogue()
    def args(self,rid,ctx):return dict(first_player=None,seed='diagnostic-'+rid,game_mode=3,season_mec=10,combat_context=ctx,tables=self.tables)
    def test_boundaries(self):
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_nested_card_parameters_v89_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertGreaterEqual(r['scenarios'],20)
    def test_original_start_unchanged_and_additive_binding(self):
        row=deepcopy(self.rows[self.rid]);ctx=deepcopy(self.ctx[self.rid]);saved=deepcopy((row,ctx))
        a=old.compile_start(row,**self.args(self.rid,ctx));b=current.compile_start(row,**self.args(self.rid,ctx))
        b['battle'].pop('nested_card_parameters');b.pop('nested_card_parameter_context_v89')
        self.assertTrue(cases_equal({'compiled':a},{'compiled':b}));self.assertEqual(saved,(row,ctx))
    def test_terminal_comparison_fields_cannot_change_input(self):
        row=deepcopy(self.rows[self.rid]);ctx=deepcopy(self.ctx[self.rid]);a=current.compile_start(row,**self.args(self.rid,ctx))
        row['outcome']={'recorded_hp_delta':999999,'winner_snapshot_slot':'p2'}
        ctx['players'][0]['after_talent_counters']={'dummy':999}
        self.assertEqual(a,current.compile_start(row,**self.args(self.rid,ctx)))
    def test_stream_and_start_mutations_rejected(self):
        for kind in ['stream','bool','board','evidence','seed']:
            row=deepcopy(self.rows[self.rid]);ctx=deepcopy(self.ctx[self.rid]);args=self.args(self.rid,ctx)
            if kind=='stream':ctx['battle_params'][0]+=1
            elif kind=='bool':ctx['battle_params'][0]=True
            elif kind=='board':row['players'][0]['candidate_start']['board'].reverse()
            elif kind=='evidence':row['battle_params_evidence']['entries']+=1
            else:args['seed']='different'
            with self.subTest(kind=kind),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**args)
    def test_runtime_binding_cannot_be_recomputed_for_changed_start(self):
        row=self.rows[self.rid];ctx=self.ctx[self.rid];b=current.compile_start(row,**self.args(self.rid,ctx))['battle'];items=[]
        for kind in ['seed','stream','record','first']:
            x=deepcopy(b)
            if kind=='stream':x['nested_card_parameters']['stream'][0]+=1
            elif kind=='record':x['nested_card_parameters']['record_binding']['record_id']='invented'
            elif kind=='first':x['first_player']=1-x['first_player']
            else:x['seed']='changed'
            x['nested_card_parameters']['battle_sha256']=current.digest_json({k:v for k,v in x.items() if k!='nested_card_parameters'})
            items.append(x)
        for result in current.simulate_batch(items)['results']:
            self.assertIn('nested_card_parameters_unresolved:',result['unresolved_reason']);self.assertNotIn('winner',result)
            self.assertFalse(result['training_label_allowed'])

if __name__=='__main__':unittest.main()
