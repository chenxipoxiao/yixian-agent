from copy import deepcopy
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v17 as old,full_battle_v18 as current
from yixian.simulator import SimulatorError
from tools.prepare_engraving_context_v18 import prepare


class EngravingTests(unittest.TestCase):
    def fixture(self,identifier=13009,slot=0):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[identifier]
        ctx['players'][0]['season_engraving_input']={'origin':current.ORIGIN,
            'selected_strategy_ids':[identifier],'slots':{str(identifier):slot}}
        return row,ctx

    def compile(self,row,ctx,**kwargs):
        return current.compile_start(row,first_player=kwargs.pop('first_player',0),seed='software-v18',
            game_mode=3,season_mec=10,combat_context=ctx,**kwargs)

    def test_boundaries_on_native_engine(self):
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',
            str(current.ROOT/'tests/current_engraving_effects_v18_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(p.returncode,0,p.stderr);self.assertTrue(json.loads(p.stdout)['passed'])

    def test_preserve_old_battle_and_catalogue(self):
        row,ctx=start_fixture();b=self.compile(row,ctx)['battle']
        self.assertNotIn('season_engraving',b)
        self.assertEqual(old.catalogue()[1],current.catalogue()[1])
        self.assertEqual(old.simulate_batch([b])['results'],current.simulate_batch([b])['results'])

    def test_full_scheduler_sword_intent_damage(self):
        row,ctx=self.fixture(13016);c=self.compile(row,ctx,max_turns=1)
        r=current.simulate_batch([c['battle']])['results'][0]
        self.assertEqual(r['players'][1]['hp'],34) # ordinary 1 + attack (3+2)
        self.assertFalse(r['training_label_allowed']);self.assertTrue(r['truncated'])

    def test_water_moon_first_use(self):
        row,ctx=self.fixture();c=self.compile(row,ctx,max_turns=7)
        r=current.simulate_batch([c['battle']])['results'][0]
        self.assertEqual(sum('current engraving 13009' in x for x in r['log']),1)

    def test_recorded_tiebreak_order_preserves_owner(self):
        row,ctx=self.fixture();c=self.compile(row,ctx,max_turns=1,first_player=1)
        r=current.simulate_batch([c['battle']])['results'][0]
        self.assertFalse(any('current engraving' in x for x in r['log']))
        c['battle']['max_turns']=2;r=current.simulate_batch([c['battle']])['results'][0]
        self.assertEqual(sum('current engraving 13009' in x for x in r['log']),1)

    def test_missing_field_is_not_slot_zero(self):
        for mutate in [lambda d:d.clear(),lambda d:d['slots'].clear(),lambda d:d.update(origin='after_battle'),
                       lambda d:d.update(selected_strategy_ids=[]),lambda d:d['slots'].update({'13009':None}),
                       lambda d:d['slots'].update({'13009':True})]:
            row,ctx=self.fixture();mutate(ctx['players'][0]['season_engraving_input'])
            with self.assertRaises(current.UnresolvedBattle):self.compile(row,ctx)

    def test_explicit_zero_and_locked_slot_are_preserved(self):
        for slot in [0,7]:
            row,ctx=self.fixture(slot=slot);c=self.compile(row,ctx)
            self.assertEqual(c['battle']['season_engraving']['players'][0],[{'strategy_id':13009,'slot':slot}])

    def test_unknown_coowned_effect_still_blocks(self):
        row,ctx=self.fixture();row['players'][0]['candidate_start']['xian_mo_strategies'].append(13008)
        with self.assertRaisesRegex(current.UnresolvedBattle,'unsupported_season_combat'):self.compile(row,ctx)

    def test_input_is_immutable_and_target_outcomes_never_used(self):
        row,ctx=self.fixture();before=deepcopy((row,ctx));c=self.compile(row,ctx)
        self.assertEqual((row,ctx),before)
        row['outcome']={'recorded_hp_delta':99999};ctx['players'][0]['after_talent_counters']={'13009':999}
        self.assertEqual(self.compile(row,ctx),c)
        self.assertEqual(c['effect_players'][0]['season_choices'],[13009])

    def test_old_bridge_rejects_new_runtime(self):
        row,ctx=self.fixture()
        with self.assertRaisesRegex(SimulatorError,'Unknown battle field'):old.simulate_batch([self.compile(row,ctx)['battle']])

    def test_preparation_projection_omits_usage_and_opponent_private_hand(self):
        row,ctx=self.fixture();base={'fixture':ctx};raw={'fixture':{'source_raw_sha256':'software-fixture','players':[]}}
        for p in row['players']:
            raw['fixture']['players'].append({'slot':p['snapshot_slot'],
                'start_fields':{'xianMoStrategies':p['candidate_start']['xian_mo_strategies']},
                'private_fields_for_schema_only':{'xianMoData':{'strategies':[{'selected':13009}],
                    'tempDatas':{'13009':0,'16024':42},'counters':{'13009':999}},'handCards':[98765]}})
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp);a=d/'base.json';b=d/'raw.json';out=d/'out.json'
            a.write_text(json.dumps(base),encoding='utf8');b.write_text(json.dumps(raw),encoding='utf8')
            result=prepare(a,b,out);text=out.read_text(encoding='utf8')
            self.assertFalse(result['usage_counters_imported']);self.assertNotIn('98765',text)
            self.assertNotIn('16024',text);self.assertNotIn('999',text)
            self.assertEqual(json.loads(text)['fixture']['players'][0]['season_engraving_input']['slots'],{'13009':0})

if __name__=='__main__':unittest.main()
