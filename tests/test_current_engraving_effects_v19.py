from copy import deepcopy
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v18 as old,full_battle_v19 as current
from tools.prepare_engraving_context_v19 import prepare


class FollowupEngravingTests(unittest.TestCase):
    def fixture(self,ids=(13008,),slot=0):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=list(ids)
        ctx['players'][0]['season_engraving_input']={'origin':current.ORIGIN,
            'selected_strategy_ids':sorted(ids),'slots':{str(i):slot for i in ids}}
        return row,ctx

    def compile(self,row,ctx,**kw):
        return current.compile_start(row,first_player=kw.pop('first_player',0),seed='software-v19',
            game_mode=3,season_mec=10,combat_context=ctx,**kw)

    def test_current_lifecycle_boundaries_on_native_engine(self):
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',
            str(current.ROOT/'tests/current_engraving_effects_v19_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(p.returncode,0,p.stderr);self.assertTrue(json.loads(p.stdout)['passed'])

    def test_prior_outputs_preserved_including_old_engraving_combination(self):
        battles=[]
        for ids in [(),(13009,),(13016,),(13009,13016)]:
            row,ctx=self.fixture(ids);battles.append(self.compile(row,ctx)['battle'])
        self.assertEqual(old.simulate_batch(battles)['results'],current.simulate_batch(battles)['results'])
        self.assertEqual(old.catalogue()[1],current.catalogue()[1])

    def test_all_new_effects_compile_without_replaying_acquisition(self):
        row,ctx=self.fixture((13001,13004,13008,13013,13019));c=self.compile(row,ctx)
        self.assertEqual(c['battle']['season_engraving']['players'][0],
            [{'strategy_id':i,'slot':0} for i in (13001,13004,13008,13013,13019)])
        self.assertEqual(c['battle']['players'][0]['hp'],40)
        self.assertEqual(c['effect_players'][0]['season_choices'],[13001,13004,13008,13013,13019])

    def test_full_turn_guard_expiry_and_ownership(self):
        row,ctx=self.fixture();b=self.compile(row,ctx,max_turns=4)['battle']
        r=current.simulate_batch([b])['results'][0]
        self.assertEqual([p['hp'] for p in r['trace'][1]['after']],[40,37])
        self.assertEqual([p['hp'] for p in r['trace'][3]['after']],[37,34])
        b['first_player']=1;r=current.simulate_batch([b])['results'][0]
        self.assertEqual(r['trace'][0]['after'][0]['hp'],37)
        self.assertEqual(r['trace'][2]['after'][0]['hp'],37)

    def test_complete_poison_battle_has_no_training_permission(self):
        row,ctx=self.fixture((13001,));r=current.simulate_batch([self.compile(row,ctx)['battle']])['results'][0]
        self.assertTrue(r['terminated']);self.assertEqual(r['winner'],0)
        self.assertEqual(sum('current engraving 13001 first use' in x for x in r['log']),1)
        self.assertFalse(r['training_label_allowed'])

    def test_missing_new_slot_never_defaults_to_zero(self):
        for i in [13001,13004,13008,13013,13019]:
            row,ctx=self.fixture((i,));ctx['players'][0]['season_engraving_input']['slots'].clear()
            with self.assertRaisesRegex(current.UnresolvedBattle,'engraving_preparation_slot_missing'):self.compile(row,ctx)

    def test_unimplemented_upgrade_downgrade_and_after_card_attack_stay_blocked(self):
        for i in [13003,13006,13007]:
            row,ctx=self.fixture((13008,));row['players'][0]['candidate_start']['xian_mo_strategies'].append(i)
            with self.assertRaisesRegex(current.UnresolvedBattle,'unsupported_season_combat'):self.compile(row,ctx)

    def test_private_projection_keeps_only_grid_fields(self):
        row,ctx=self.fixture((13001,13004,13008,13013,13019));raw={'x':{'source_raw_sha256':'software-fixture','players':[]}}
        for p in row['players']:
            ids=p['candidate_start']['xian_mo_strategies']
            raw['x']['players'].append({'slot':p['snapshot_slot'],'start_fields':{'xianMoStrategies':ids},
                'private_fields_for_schema_only':{'xianMoData':{'strategies':[{'selected':i} for i in ids],
                'tempDatas':{**{str(i):0 for i in ids},'13007':7},'counters':{'13001':999}},'handCards':[998877]}})
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp);a=d/'base';b=d/'raw';out=d/'result'
            a.write_text(json.dumps({'x':ctx}),encoding='utf8');b.write_text(json.dumps(raw),encoding='utf8')
            result=prepare(a,b,out);text=out.read_text('utf8')
            self.assertEqual(result['explicit_grid_values'],5)
            for private in ['998877','999','13007']:self.assertNotIn(private,text)

    def test_targets_and_usage_counts_do_not_modify_compilation(self):
        row,ctx=self.fixture((13004,13019));before=deepcopy((row,ctx));c=self.compile(row,ctx)
        self.assertEqual((row,ctx),before)
        row['outcome']={'recorded_hp_delta':-999}
        ctx['players'][0]['after_talent_counters']={'13004':100}
        self.assertEqual(self.compile(row,ctx),c)

if __name__=='__main__':unittest.main()
