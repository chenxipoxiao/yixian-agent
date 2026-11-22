import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createSoundControl} from '../tools/current_sound_control_v52.mjs';
import {installCurrentSoundScheduler} from '../tools/current_sound_scheduler_v52.mjs';
import {installCurrentEngravings} from '../tools/current_engraving_effects_v52.mjs';
import {installKillingSound} from '../tools/current_killing_sound_v36.mjs';
import {createSeasonOpeningBatch} from '../tools/current_season_opening_v51.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const facts=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-sound-control-v52.json')));
let scenarios=0;
const entry=(id,enabled=true)=>({strategy_id:id,enabled});
function fresh(raw=[[0,0,0],[0,0,0]]) {
 const g=new GameState(undefined,undefined,'sound-boundary-probe');
 g.players.forEach((p,i)=>{p.character='sw3';p.hp=40;p.max_hp=100;p.max_physique=100;p.cards=raw[i].map(id=>facts.metadata[id].runtime_id);p.hand_count=2;});
 return g;
}
function attach(g,players,raw=[[0,0,0],[0,0,0]],order=[0,1],extra=false) {
 installCurrentSoundScheduler(g);
 const s=createSoundControl(root,g,swogi,{players,raw_boards:raw},order);
 let old;
 if(extra){old=createSeasonOpeningBatch(root,g,{players:[[{strategy_id:1002,enabled:true},{strategy_id:3002}],[]]},order);old.installBoundary(7105);old.installBoundary(3002);}
 s.installBoundary(1007);
 if(extra)installKillingSound(root,g,{players:[{strategy_id:1006,enabled:true},null]},order);
 s.installBoundary(1005);s.installBoundary(1003);
 if(extra)old.installBoundary(1002);
 return s;
}
for(const order of [[0,1],[1,0]])for(const both of [false,true]) {
 const g=fresh();g.players[0].hp=47;g.players[1].hp=53;
 const owners=both?[[entry(1003)],[entry(1003)]]:[[entry(1003)],[]];
 const s=attach(g,owners,undefined,order);g.start_of_game_setup();
 assert.deepEqual(g.players.map(p=>p.hp),both?[62,69]:[54,60]);
 assert.deepEqual(g.players.map(p=>p.max_hp),both?[115,116]:[107,107]);
 const count=s.metadata().events.length;g.do_plant_start_permanent_buffs();g.swap_players();g.do_plant_start_permanent_buffs();assert.equal(s.metadata().events.length,count);scenarios++;
}
// Target callbacks are retained and amounts are based on current HP, not maximum.
{
 const g=fresh();g.players[0].p2_rejuvenation_stacks=1;g.players[1].prevent_gain_hp_stacks=1;
 attach(g,[[entry(1003)],[]]);g.do_plant_start_permanent_buffs();
 assert.deepEqual(g.players.map(p=>[p.hp,p.max_hp]),[[46,109],[40,106]]);scenarios++;
}
// Both amounts are sampled before the first target's max-HP/healing callbacks.
{
 const g=fresh(),increase=g.increase_idx_max_hp.bind(g);
 g.increase_idx_max_hp=function(i,n){const r=increase(i,n);if(i===0)this.players[1].hp+=10;return r;};
 const s=attach(g,[[entry(1003)],[]]);g.do_plant_start_permanent_buffs();
 assert.deepEqual(s.metadata().events[0].amounts,[6,6]);assert.equal(g.players[1].hp,56);scenarios++;
}
for(const id of [1003,1005,1007]) {
 const g=fresh();attach(g,[[entry(id,false)],[]]);g.start_of_game_setup();
 assert.deepEqual(g.players.map(p=>[p.hp,p.max_hp,p.predicament_for_immortals_stacks,p.finishing_touch_stacks]),[[40,100,0,0],[40,100,0,0]]);scenarios++;
}
// Hidden ordinary attacks ARE eligible for281. Full-level cards retain the charge.
{
 const raw=[[20002,0,2],[0,0,0]],g=fresh(raw),s=attach(g,[[entry(1007)],[]],raw);
 g.start_of_game_setup();g.do_finishing_touch(0);assert.equal(g.players[0].finishing_touch_stacks,1);
 g.players[0].can_post_action[1]=true;g.do_finishing_touch(1);
 assert.equal(g.players[0].cards[1],'601012');assert.equal(g.players[0].finishing_touch_stacks,0);
 g.do_finishing_touch(2);assert.equal(g.players[0].cards[2],facts.metadata[2].runtime_id);
 assert.equal(s.metadata().events.filter(e=>e.phase==='before_card_body_281').length,1);scenarios++;
}
// Two sound owners stack two uses; repeated use of the SAME eligible card works.
{
 const g=fresh();attach(g,[[entry(1007)],[entry(1007)]]);g.start_of_game_setup();
 g.do_finishing_touch(0);g.players[0].can_post_action[0]=true;g.do_finishing_touch(0);
 assert.equal(g.players[0].cards[0],'601013');assert.equal(g.players[0].finishing_touch_stacks,0);scenarios++;
}
// First-use engraving upgrades before281, and it still has its own first-use restriction.
{
 const raw=[[2,0,0],[0,0,0]],g=fresh(raw);attach(g,[[entry(1007)],[]],raw);
 installCurrentEngravings(root,g,{players:[[{strategy_id:13003,slot:0}],[]]},[0,1],{players:raw},swogi);
 g.start_of_game_setup();g.do_finishing_touch(0);assert.equal(g.players[0].cards[0],facts.metadata[20002].runtime_id);
 assert.equal(g.players[0].finishing_touch_stacks,0);scenarios++;
}
// Unknown transformed identity stops instead of assigning an upgrade by ID digits.
{
 const g=fresh();attach(g,[[entry(1007)],[]]);g.start_of_game_setup();g.players[0].cards[0]='unknown';
 assert.throws(()=>g.do_finishing_touch(0),/unknown_runtime/);assert.equal(g.players[0].finishing_touch_stacks,1);scenarios++;
}
// Full/native chase checks: no agility cost while blocked; exemption is not erased.
for(const owners of [1,2])for(const exemption of [0,1]) {
 const g=fresh(),players=owners===1?[[entry(1005)],[]]:[[entry(1005)],[entry(1005)]];
 attach(g,players);g.start_of_game_setup();for(const p of g.players){p.hp=1000;p.max_hp=1000;}
 const p=g.players[0];p.agility=20;p.prevent_anti_chase=exemption;
 g.sim_turn();assert.equal(p.predicament_for_immortals_stacks,owners-1);
 assert.equal(p.chases,exemption?1:0);assert.equal(p.agility,exemption?10:20);
 assert.equal(g.players[1].predicament_for_immortals_stacks,owners);
 if(!exemption){g.sim_turn();assert.equal(p.chases,owners===1?1:0);assert.equal(p.predicament_for_immortals_stacks,0);}
 scenarios++;
}
// Rejuvenation occurs before1006 damage;1007 after it and before3002 guard.
{
 const g=fresh(),s=attach(g,[[entry(1003),entry(1005),entry(1007)],[]],undefined,[0,1],true);
 g.start_of_game_setup();const events=s.metadata().events;
 assert.deepEqual(events.map(e=>e.strategy_id),[1003,1005,1007]);
 assert.equal(events[0].before[0].hp,40);assert.equal(events[0].after[0].hp,46);
 assert.ok(events[2].before[0].hp<46);assert.equal(g.players[0].guard_up,1);scenarios++;
}
for(const value of [null,{}, {players:[[],[]],raw_boards:[[0],[0]]},
 {players:[[{strategy_id:1007}],[]],raw_boards:[[0],[0]]},
 {players:[[entry(1007),entry(1007)],[]],raw_boards:[[0],[0]]}]) {
 assert.throws(()=>createSoundControl(root,fresh(),swogi,value),/required/);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios}));
