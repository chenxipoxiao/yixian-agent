from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v12 as old, full_battle_v13 as current


class CurrentFateContextTests(unittest.TestCase):
    def fixture(self):
        row,ctx=start_fixture()
        for p in ctx['players']:
            p['start_extensions']={'origin':'publicData.lastRoundData','talentDatas':{},'privateTalentDatas':{}}
        return row,ctx

    def compile(self,row,ctx,**kw):
        return current.compile_start(row,combat_context=ctx,game_mode=3,season_mec=10,
            seed='software-only',first_player=0,**kw)

    def test_soulstat_requires_eighth_slot_and_ordinary_attack(self):
        for n in [3,7,8]:
            row,ctx=self.fixture();s=row['players'][0]['candidate_start']
            s['board']=[0]*n;s['unlocked_slots']=n;s['talents']=[52]
            battle=self.compile(row,ctx,max_turns=1)['battle']
            result=current.simulate_batch([battle])['results'][0]
            expected=['601011']*n
            if n==8:expected[-1]='624011'
            self.assertEqual(result['players'][0]['cards'],expected)
        s['board'][-1]=1000001
        c=self.compile(row,ctx,max_turns=1)
        result=current.simulate_batch([c['battle']])['results'][0]
        self.assertNotEqual(result['players'][0]['cards'][-1],'624011')

    def test_nested_metadata_required_known_absence_is_distinct(self):
        for fate,kind,key in [(192,'talentDatas','189'),(199,'privateTalentDatas','199')]:
            row,ctx=self.fixture();row['players'][0]['candidate_start']['talents']=[fate]
            self.compile(row,ctx)
            ctx['players'][0]['start_extensions'][kind][key]={}
            with self.assertRaisesRegex(ValueError,'commonParams'):self.compile(row,ctx)
            del ctx['players'][0]['start_extensions']
            with self.assertRaisesRegex(ValueError,'start talent metadata'):self.compile(row,ctx)

    def test_learned_families_are_runtime_classifications_not_rewards(self):
        row,ctx=self.fixture();s=row['players'][0]['candidate_start'];s['talents']=[189,192]
        ctx['players'][0]['start_extensions']['talentDatas']['189']={'commonParams':[1000001]}
        before=deepcopy(row);c=self.compile(row,ctx,max_turns=1);p=c['battle']['players'][0]
        self.assertEqual(p['cards'],['601011']*3);self.assertEqual(row,before)
        family=current.catalogue()[1][1000001][:-1]
        script="""import {GameState,ready} from './gamestate_full.js';await ready;
        const g=new GameState();Object.assign(g.players[0],JSON.parse(process.argv[1]));
        const id=process.argv[2];console.log(JSON.stringify([g.is_cloud_sword(id),g.is_unrestrained_sword(id),g.is_spirit_sword(id),g.is_sword_formation(id)]));"""
        run=subprocess.run([shutil.which('node'),'--experimental-default-type=module','--input-type=module','-e',script,json.dumps(p),family+'2'],cwd=current.ROOT/'external/yisim',capture_output=True,text=True,encoding='utf8',check=True)
        self.assertEqual(json.loads(run.stdout),[True]*4)
        current.simulate_batch([c['battle']])

    def test_vase_retains_empty_first_slot_and_activates_only_first(self):
        cases=[([0,0,0],0),([0,7000003,0],0),([7000003,0,0],1)]
        for slots,expected in cases:
            row,ctx=self.fixture();row['players'][0]['candidate_start']['talents']=[199]
            ctx['players'][0]['start_extensions']['privateTalentDatas']['199']={'commonParams':slots}
            c=self.compile(row,ctx);p=c['battle']['players'][0]
            script="""import {GameState,ready} from './gamestate_full.js';await ready;
            const g=new GameState();Object.assign(g.players[0],JSON.parse(process.argv[1]));
            g.do_five_elements_pure_vase(0);console.log(g.players[0].activate_wood_spirit_stacks);"""
            run=subprocess.run([shutil.which('node'),'--experimental-default-type=module','--input-type=module','-e',script,json.dumps(p)],cwd=current.ROOT/'external/yisim',capture_output=True,text=True,encoding='utf8',check=True)
            self.assertEqual(int(run.stdout),expected)

    def test_mutual_growth_uses_current_two_upgrade_config(self):
        row,ctx=self.fixture();row['players'][0]['candidate_start']['talents']=[10127]
        p=self.compile(row,ctx)['battle']['players'][0]
        script="""import {GameState,ready} from './gamestate_full.js';await ready;
        const g=new GameState();Object.assign(g.players[0],JSON.parse(process.argv[1]));
        g.apply_p3_fates_setup(0);console.log(g.players[0].mutual_growth_stacks);"""
        run=subprocess.run([shutil.which('node'),'--experimental-default-type=module','--input-type=module','-e',script,json.dumps(p)],cwd=current.ROOT/'external/yisim',capture_output=True,text=True,encoding='utf8',check=True)
        self.assertEqual(int(run.stdout),2)

    def test_only_reviewed_noncombat_counters_are_omitted(self):
        row,ctx=self.fixture();before=self.compile(row,ctx)['battle']
        row['players'][0]['candidate_start']['permanentBuffTempDatas'].update({'10059':1,'20083':2,'20084':3,'20085':4,'20086':5})
        self.assertEqual(self.compile(row,ctx)['battle'],before)
        row['players'][0]['candidate_start']['permanentBuffTempDatas']['999999']=1
        with self.assertRaisesRegex(ValueError,'permanent_hooks_pending'):self.compile(row,ctx)

    def test_outcomes_and_after_state_cannot_supply_nested_params(self):
        row,ctx=self.fixture();row['players'][0]['candidate_start']['talents']=[192,199]
        original=self.compile(row,ctx)
        row['outcome']={'recorded_hp_delta':999}
        ctx['players'][0]['after_talent_counters']={'189':{'commonParams':[1000001]},'199':{'commonParams':[7000003,0,0]}}
        self.assertEqual(self.compile(row,ctx),original)

    def test_unmapped_state_duplicate_fates_and_season_interactions_still_block(self):
        row,ctx=self.fixture();row['players'][0]['candidate_start']['talents']=[199]
        ctx['players'][0]['start_extensions']['privateTalentDatas']['199']={'commonParams':[9999999,0,0]}
        with self.assertRaisesRegex(ValueError,'Unmapped vase'):self.compile(row,ctx)
        ctx['players'][0]['start_extensions']['privateTalentDatas']['199']={'commonParams':[0,0,0]}
        row['players'][0]['candidate_start']['xian_mo_strategies']=[23058]
        with self.assertRaises(ValueError):self.compile(row,ctx)
        row['players'][0]['candidate_start']['talents']=[199,199]
        with self.assertRaisesRegex(ValueError,'Unique explicit talents'):self.compile(row,ctx)
