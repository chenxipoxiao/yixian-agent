from copy import deepcopy
import json, shutil, subprocess, unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v76 as old, full_battle_v77 as current
from yixian.preparation_context_v77 import FIELD, ORIGIN, PROJECTION_SHA, required_ids, validate_additions
from yixian.terminal_damage_v47 import calculate_terminal_damage


def prepared(ids=(13015,), present=None):
    row,ctx=start_fixture();row['split']='train'
    row['players'][0]['candidate_start']['xian_mo_strategies']=list(ids)
    ctx['engraving_source_projection_sha256']=PROJECTION_SHA
    legacy=[x for x in ids if x in (13007,13016)]
    if legacy:ctx['players'][0]['season_engraving_input']={'origin':'privateData.xianMoData.tempDatas:preparation_grid_selection','selected_strategy_ids':sorted(legacy),'slots':{}}
    previous=deepcopy(ctx); expected=required_ids(row['players'][0],ctx['players'][0]);present={} if present is None else present
    ctx['players'][0][FIELD]={'origin':ORIGIN,'selected_strategy_ids':expected,'present_values':present,
        'absent_keys':sorted(str(x) for x in expected if str(x) not in present),'complete_temp_map_present':True,
        'source_projection_sha256':PROJECTION_SHA,'source_raw_sha256':row['source']['raw_sha256'],
        'environment_only':True,'record_id':row['id'],'round':row['round'],'snapshot_slot':'p1'}
    return row,ctx,previous


class PreparationTests(unittest.TestCase):
    def args(self,ctx,first=0):return dict(first_player=first,seed='preparation-software',game_mode=3,season_mec=10,combat_context=ctx)
    def test_native_consumption_and_engraving_boundaries(self):
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_preparation_v77_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(p.returncode,0,p.stderr);data=json.loads(p.stdout);self.assertTrue(data['passed']);self.assertGreaterEqual(data['scenarios'],15);print('V77_NATIVE_PROBE='+p.stdout.strip(),flush=True)
    def test_missing_key_in_complete_map_resolves_default_slot(self):
        for id in [13007,13015,13016]:
            row,ctx,_=prepared([id]);before=deepcopy((row,ctx));c=current.compile_start(row,**self.args(ctx))
            self.assertEqual(c['battle']['season_engraving']['players'][0],[{'strategy_id':id,'slot':0}]);self.assertEqual(before,(row,ctx))
    def test_explicit_ash_grid_preserved(self):
        row,ctx,_=prepared(present={'13015':2});c=current.compile_start(row,**self.args(ctx));self.assertEqual(c['battle']['season_engraving']['players'][0][0]['slot'],2)
    def test_disabled_switch_only_and_ownership_restored(self):
        for value in [1,-1,2147483647]:
            row,ctx,_=prepared([1010],{'1010':value});c=current.compile_start(row,**self.args(ctx));self.assertEqual(c['effect_players'][0]['season_choices'],[1010]);self.assertEqual(c['preparation_v77_context']['disabled1010_players'],[0])
        for value in [{},{'1010':0}]:
            row,ctx,_=prepared([1010],value)
            with self.assertRaisesRegex(current.UnresolvedBattle,'active1010'):current.compile_start(row,**self.args(ctx))
    def test_missing_map_is_not_default_zero(self):
        for key,value in [('complete_temp_map_present',False),('present_values',None),('absent_keys',[]),('origin','unknown')]:
            row,ctx,_=prepared();ctx['players'][0][FIELD][key]=value
            with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
        row,ctx,_=prepared();del ctx['players'][0][FIELD]
        with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
    def test_binding_and_private_field_injection_refused(self):
        for key,value in [('record_id','future'),('round',2),('snapshot_slot','p2'),('source_raw_sha256','other'),('source_projection_sha256','other'),('environment_only',False),('selected_strategy_ids',[13016]),('hand',[999])]:
            row,ctx,_=prepared();ctx['players'][0][FIELD][key]=value
            with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
    def test_invalid_grid_boolean_and_noninteger_refused(self):
        for value in [-1,8,True,1.5,'0']:
            row,ctx,_=prepared(present={'13015':value})
            with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
    def test_additive_validator_preserves_every_old_field(self):
        row,ctx,prev=prepared();a={row['id']:prev};b={row['id']:ctx}
        self.assertEqual(validate_additions([row],a,b,[row['id']]),[{'record_id':row['id'],'player_index':0}])
        changed=deepcopy(b);changed[row['id']]['players'][1]['hand_count']=4
        with self.assertRaises(ValueError):validate_additions([row],a,changed,[row['id']])
        with self.assertRaises(ValueError):validate_additions([row],a,b,[])
    def test_no_terminal_input_or_old_interface_migration(self):
        row,ctx,_=prepared();c=current.compile_start(row,**self.args(ctx));row['outcome']={'recorded_hp_delta':999,'winner_snapshot_slot':'p2'}
        self.assertEqual(c,current.compile_start(row,**self.args(ctx)))
        with self.assertRaises(old.UnresolvedBattle):old.compile_start(row,**self.args(ctx))
    def test_nonowner_complete_output_unchanged(self):
        row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
        self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
    def test_complete_ash_battles_both_seats_and_slots(self):
        starts=[]
        for first in [0,1]:
            for slot in [0,2]:
                row,ctx,_=prepared(present={'13015':slot});starts.append(current.compile_start(row,**self.args(ctx,first)))
        for c,b in zip(starts,current.simulate_batch([x['battle'] for x in starts])['results']):
            self.assertTrue(b.get('terminated'),b);self.assertFalse(b['used_randomness']);self.assertTrue(calculate_terminal_damage(c,b)['resolved']);self.assertFalse(b['training_label_allowed']);self.assertIn('preparation_v77',b)
    def test_truncation_has_no_settlement(self):
        row,ctx,_=prepared();c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1
        b=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(b['truncated']);self.assertFalse(calculate_terminal_damage(c,b)['resolved'])

if __name__=='__main__':unittest.main()
