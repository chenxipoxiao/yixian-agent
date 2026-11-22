from copy import deepcopy
import json, subprocess, shutil, unittest
from unittest.mock import patch
from yixian import full_battle_v129r2 as engine, terminal_damage_v129 as settlement
from yixian.settlement import ordinary_destiny_damage

STAGE=engine.ROOT/'runs/stages/20261116T100200Z-s2-mirror-reader'
FIXTURES=json.loads((STAGE/'opening-fixtures-v129r2.json').read_text('utf8'))
PLAIN=next(v for v in FIXTURES.values() if not v['context']['battle_params'])
RANDOM=next(v for v in FIXTURES.values() if v['context']['battle_params'])

def inputs(fixture):
    row,ctx=deepcopy(fixture['row']),deepcopy(fixture['context'])
    return row,{'combat_context':ctx,'game_mode':3,'season_mec':10,
               'seed':'diagnostic-'+row['id'],'first_player':fixture['first_player_argument']}

def terminal():
    c=deepcopy(PLAIN['compiled'])
    for p in c['effect_players']:
        p.update(fates=[],season_choices=[],talent_counters={},life=3)
    r={'terminated':True,'truncated':False,'winner':0,
       'players':[{'hp':30,'direct_destiny_lost':0,'kindness_tune_stacks':0},
                  {'hp':-10,'direct_destiny_lost':0,'kindness_tune_stacks':0}]}
    return c,r

class MirrorContextTests(unittest.TestCase):
    def test_original_snapshot_preserved_old_entry_stays_strict(self):
        row,kw=inputs(PLAIN);before=deepcopy((row,kw))
        got=engine.compile_start(row,**kw)
        self.assertEqual((row,kw),before)
        self.assertEqual([p['is_mirror'] for p in got['effect_players']],[False,True])
        self.assertEqual(got['battle']['civet'],{'is_mirror':[False,True]})
        self.assertEqual(got['battle']['players'],PLAIN['compiled']['battle']['players'])
        with self.assertRaisesRegex(engine.UnresolvedBattle,'Mirror/unknown'):
            engine.previous.compile_start(row,**kw)
        row['outcome']={'recorded_hp_delta':9999,'recorded_destiny_damage':9999}
        kw['combat_context']['players'][1]['after_talent_counters']={'27':999}
        self.assertEqual(got,engine.compile_start(row,**kw))

    def test_unknown_markers_provenance_and_other_effects_rejected(self):
        row,kw=inputs(PLAIN)
        for value in [None,0,1,'true']:
            kw['combat_context']['players'][1]['is_mirror']=value
            with self.assertRaisesRegex(engine.UnresolvedBattle,'explicit_boolean'):
                engine.compile_start(row,**kw)
        row,kw=inputs(PLAIN);kw['combat_context']['players'][1]['source_fields']['is_mirror']='future_state'
        with self.assertRaisesRegex(engine.UnresolvedBattle,'marker_provenance'):
            engine.compile_start(row,**kw)
        row,kw=inputs(PLAIN);row['players'][1]['candidate_start']['permanentBuffTempDatas']['999999']=1
        with self.assertRaisesRegex(engine.UnresolvedBattle,'permanent_hooks_pending'):
            engine.compile_start(row,**kw)

    def test_original_random_inputs_bound_and_nonmirror_path_unchanged(self):
        row,kw=inputs(RANDOM)
        with patch.object(engine,'compile_mirror_start',side_effect=lambda *a,**k:deepcopy(RANDOM['compiled'])):
            good=engine.compile_start(row,**kw)
            row['outcome']={'recorded_turn_count':999}
            self.assertEqual(good,engine.compile_start(row,**kw))
            kw['combat_context']['battle_params'][0]+=1
            with self.assertRaisesRegex(engine.UnresolvedBattle,'original_snapshot_and_stream'):
                engine.compile_start(row,**kw)
        row,kw=inputs(PLAIN);kw['combat_context']['players'][1]['is_mirror']=False
        sentinel={'unchanged':True}
        with patch.object(engine.previous,'compile_start',return_value=sentinel) as previous:
            self.assertIs(engine.compile_start(row,**kw),sentinel)
            self.assertEqual(previous.call_args.kwargs,kw)

    def test_mirror_loser_skips_live_mitigation_and_never_invents_balance(self):
        c,r=terminal();c['effect_players'][1].update(fates=[27,45,105,65],talent_counters={'105':1,'65':1})
        r['players'][1]['kindness_tune_stacks']=99
        answer=settlement.calculate_terminal_damage(c,r)
        expected=ordinary_destiny_damage(c['battle']['players'][0]['round_number'],40)
        self.assertEqual(answer['life_damage'],expected)
        self.assertEqual(answer['pending_match_effects'],[])
        self.assertNotIn('loser_destiny_after',answer)
        self.assertIsNone(answer['authoritative_post_battle_destiny'])
        self.assertEqual(answer['events'],[])
        c['effect_players'][0]['season_choices']=[2011]
        second=settlement.calculate_terminal_damage(c,r)
        self.assertEqual([e['effect'] for e in second['events']],['season2011'])
        self.assertLess(second['life_damage'],expected)

    def test_live_loser_keeps_v47_settlement_with_mirror_winner(self):
        c,r=terminal();r['winner']=1;r['players'][0]['hp']=-10;r['players'][1]['hp']=30
        c['effect_players'][0].update(fates=[65],talent_counters={'65':1})
        c['effect_players'][1]['season_choices']=[2011]
        got=settlement.calculate_terminal_damage(c,r)
        live=deepcopy(c);live['effect_players'][1]['is_mirror']=False
        expected=settlement.legacy.calculate_terminal_damage(live,r)
        got.pop('mirror_context_v129')
        self.assertEqual(got,expected)
        self.assertEqual(got['loser_destiny_after'],1)

    def test_civet_runtime_preserves_mirror_after_initiative_reordering(self):
        script=r"""
import {installCivet} from './tools/current_civet_v38.mjs';
import {validateMirrorContext} from './tools/current_mirror_context_v129r2.mjs';
const root=process.cwd(),a={hp:1,direct_destiny_lost:0},b={hp:1,direct_destiny_lost:0};
const game={players:[a,b],increase_idx_hp(i,n){this.players[i].hp+=n;}};
const input={mirror_context:{is_mirror:[false,true]},civet:{is_mirror:[false,true]}};
const meta=validateMirrorContext(root,input),civet=installCivet(root,game,input.civet,[1,0]);
game.current_civet_execute(10433);game.players.reverse();game.current_civet_execute(10433);
civet.verifyTerminal();let rejected=false;
try{validateMirrorContext(root,{...input,civet:{is_mirror:[false,false]}});}catch(e){rejected=true;}
process.stdout.write(JSON.stringify({meta,civet:civet.metadata(),hp:[a.hp,b.hp],rejected}));
"""
        run=subprocess.run([shutil.which('node'),'--experimental-default-type=module','--input-type=module','-e',script],cwd=engine.ROOT,capture_output=True,text=True,encoding='utf8',check=True)
        got=json.loads(run.stdout)
        self.assertEqual(got['civet']['requested_destiny_gains'],[6,0])
        self.assertEqual([e['player_index'] for e in got['civet']['events']],[1,0])
        self.assertEqual(got['hp'][0],got['hp'][1]);self.assertGreater(got['hp'][0],1)
        self.assertTrue(got['rejected'])

if __name__=='__main__':unittest.main()
