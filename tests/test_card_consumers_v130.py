from copy import deepcopy
from pathlib import Path
import json, subprocess, shutil, unittest
from yixian import full_battle_v130 as engine
S=engine.ROOT/'runs/stages/20261116T103900Z-s2-mirror-card-consumers'
FIXTURES=json.loads((S/'opening-fixtures-v130.json').read_text('utf8'))
PLAIN=next(f for f in FIXTURES.values() if not f['context']['battle_params'])
RANDOM=next(f for f in FIXTURES.values() if f['context']['battle_params'])
def inputs(f):
 return deepcopy(f['row']),dict(combat_context=deepcopy(f['context']),game_mode=3,season_mec=10,first_player=f['first_player_argument'],seed='diagnostic-'+f['row']['id'])
def node(script):
 p=subprocess.run([shutil.which('node'),'--experimental-default-type=module','--input-type=module','-e',script],cwd=engine.ROOT,capture_output=True,text=True,encoding='utf8')
 if p.returncode:raise AssertionError(p.stderr)
 return json.loads(p.stdout)
class CardConsumersTests(unittest.TestCase):
 def test_three_grades_extend_catalogue_without_changing_old_ids(self):
  new=engine.catalogue();old=engine.previous.catalogue()
  self.assertEqual(new[0],old[0]);self.assertEqual(new[2:],old[2:])
  self.assertEqual({k:v for k,v in new[1].items() if k in old[1]},old[1])
  self.assertEqual(set(new[1])-set(old[1]),{7000105,7010105,7020105})
 def test_original_snapshot_unchanged_and_terminal_fields_cannot_change_start(self):
  row,kw=inputs(RANDOM);before=deepcopy((row,kw));got=engine.compile_start(row,**kw)
  self.assertEqual((row,kw),before)
  row['outcome']={'recorded_hp_delta':999,'recorded_turn_count':999}
  kw['combat_context']['players'][1]['after_talent_counters']={'27':999}
  self.assertEqual(got,engine.compile_start(row,**kw))
 def test_changed_stream_unknown_mirror_and_missing_hand_remain_blocked(self):
  for change in ['stream','mirror','hand']:
   row,kw=inputs(RANDOM);ctx=kw['combat_context']
   if change=='stream':ctx['battle_params'][0]+=1
   elif change=='mirror':ctx['players'][1]['is_mirror']=None
   else:ctx['players'][1]['hand']=None
   with self.assertRaises(engine.UnresolvedBattle):engine.compile_start(row,**kw)
 def test_high_grade_patrol_evaluates_healing_after_all_hits_and_wood_condition(self):
  got=node(r"""
import {registerWoodPatrol,installWoodPatrol} from './tools/current_wood_patrol_v130.mjs';
const swogi={'601011':{is_cloud_sword:true}},out=[];registerWoodPatrol(process.cwd(),swogi);
for(const [id,wood,heals] of [['771011',true,true],['771012',true,true],['771013',true,true],['771013',false,true],['771013',true,false]]){
 const p={hp:10,max_hp:100,qi:0,def:0,hp_gained:0,wood_thorn:0,this_card_chases:0,currently_triggering_card_id:id,currently_triggering_card_idx:0,trigger_depth:1},q={hp:100};let hits=0;
 const g={players:[p,q],increase_idx_x_by_c(i,k,n){this.players[i][k]+=n;},atk(n){hits++;q.hp-=n;if(heals){p.hp_gained++;p.hp++;}},if_wood_spirit(){return wood;},chase(){p.this_card_chases++;}};
 const hook=installWoodPatrol(process.cwd(),g,swogi);swogi[id].card_actions(g);out.push({hits,chases:p.this_card_chases,thorns:p.wood_thorn,counter:hook.metadata().events[0].counter313});
}process.stdout.write(JSON.stringify(out));
""")
  self.assertEqual([g['hits'] for g in got],[2,3,4,4,4]);self.assertEqual([g['chases'] for g in got],[1,1,1,0,0]);self.assertEqual([g['thorns'] for g in got],[1]*5)
 def test_nested_selected_card_restores_physical_identity_on_exception(self):
  got=node(r"""
import fs from 'node:fs';import {createNestedCardQueue} from './tools/current_nested_card_parameters_v89.mjs';
const f=JSON.parse(fs.readFileSync('data/inspection/current-mirror-card-consumers-v130.json')).nested_reader;
const c=f.cards.find(x=>x.kind==='divine'),target=f.selected_targets.find(x=>x.raw_id===1000066),swogi={};
for(const a of [...f.cards,...f.selected_targets])swogi[a.runtime_id]={card_actions(){}};
const p={cards:[c.runtime_id],currently_triggering_card_id:c.runtime_id,currently_triggering_card_idx:0,hp:10,def:0};let observed;
const g={players:[p,{}],just_do_the_card_and_nothing_else(){throw Error('wrong body');},increase_idx_def(i,n){p.def+=n;},increase_idx_hp(i,n){p.hp+=n;},trigger_card(id,slot){observed=[p.cards[slot],id];throw Error('nested boundary');}};
for(const m of f.blocked_random_entrypoints)g[m]=()=>{};
createNestedCardQueue(swogi,g,[1000066],[0,1],f);let error;
try{g.just_do_the_card_and_nothing_else(swogi[c.runtime_id]);}catch(e){error=e.message;}
process.stdout.write(JSON.stringify({observed,restored:p.cards[0]===c.runtime_id,target:target.runtime_id,error}));
""")
  self.assertTrue(got['restored']);self.assertEqual(got['observed'],[got['target']]*2);self.assertEqual(got['error'],'nested boundary')
 def test_flag_original_order_controls_selected_card_and_even_slot_is_rejected(self):
  got=node(r"""
import fs from 'node:fs';import {installFlagParameterReader} from './tools/current_flag_parameter_reader_v102.mjs';
const f=JSON.parse(fs.readFileSync('data/inspection/current-mirror-card-consumers-v130.json')).flag_reader,c=f.cards.find(x=>x.raw_id===7000111),selected=f.hand_metadata['7040090'];let events=[],triggers=0;
const p={cards:[c.runtime_id],currently_triggering_card_id:c.runtime_id,currently_triggering_card_idx:0,currently_playing_card_idx:0,trigger_depth:1,hand_count:1};
const g={players:[p,{}],trigger_card(){triggers++;},current_element_flag(){this.trigger_card(selected.runtime_id,0);}};
const reader=installFlagParameterReader(g,{[selected.runtime_id]:{card_actions(){}}},[[7040090],null],[0,1],f,e=>events.push(e));
g.current_element_flag(c.raw_id);reader.verifyIdle();p.cards.push(c.runtime_id);p.currently_triggering_card_idx=p.currently_playing_card_idx=1;let error;
try{g.current_element_flag(c.raw_id);}catch(e){error=e.message;}
process.stdout.write(JSON.stringify({events,triggers,error}));
""")
  self.assertEqual(got['events'][0]['expected_value'],7040090);self.assertEqual(got['triggers'],1);self.assertIn('even_slot',got['error'])
if __name__=='__main__':unittest.main()
