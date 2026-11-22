import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createSeasonOpeningBatch} from '../tools/current_season_opening_v51.mjs';
import {installHeavenSpirit} from '../tools/current_heaven_spirit_v34.mjs';
import {installKillingSound} from '../tools/current_killing_sound_v36.mjs';
import {installDragonQi} from '../tools/current_dragon_qi_v40.mjs';
import {installCurrentSeasonContext} from '../tools/current_season_context_v27.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
let scenarios=0;
const e=id=>id===1002?{strategy_id:id,enabled:true}:{strategy_id:id};
const all=[e(1002),e(3002),e(7105)];
function fresh(){const g=new GameState(undefined,undefined,'opening-probe');for(const p of g.players){
 p.character='dx3';p.hp=40;p.max_hp=100;p.max_physique=100;p.cards=['601011','601011','601011'];p.hand_count=2;
}return g;}
function attach(g,value,order=[0,1],extra=false){
 const c=createSeasonOpeningBatch(root,g,value,order);c.installBoundary(7105);
 if(extra)installDragonQi(root,g,{players:[{strategy_id:3011},{strategy_id:3011}]},order);
 c.installBoundary(3002);
 if(extra)installCurrentSeasonContext(root,g,swogi,{players:[[3001],[3001]]},order);
 if(extra)installKillingSound(root,g,{players:[{strategy_id:1006,enabled:true},{strategy_id:1006,enabled:true}]},order);
 c.installBoundary(1002);
 if(extra)installHeavenSpirit(root,g,{players:[{strategy_id:1001,enabled:true},{strategy_id:1001,enabled:true}]},order);
 return c;
}
for(const order of [[0,1],[1,0]])for(const both of [false,true]) {
 const g=fresh(),value={players:both?[all,all]:[all,[]]},c=attach(g,value,order);
 const owners=g.players.filter((p,i)=>both||order[i]===0);
 g.start_of_game_setup();assert.deepEqual(g.players.map(p=>p.increase_atk),both?[2,2]:[1,1]);
 for(const p of owners){assert.equal(p.guard_up,1);assert.equal(p.styx,2);assert.equal(p.hp,46);assert.equal(p.max_hp,100);}
 assert.equal(c.metadata().events.length,both?6:3);
 assert.deepEqual(c.metadata().events.map(x=>x.strategy_id),both?[1002,3002,7105,1002,3002,7105]:[1002,3002,7105]);
 const count=c.metadata().events.length;g.do_plant_start_permanent_buffs();g.swap_players();g.do_plant_start_permanent_buffs();assert.equal(c.metadata().events.length,count);
 assert.throws(()=>createSeasonOpeningBatch(root,g,value,order),/already_installed/);scenarios++;
}
// Both switches are disabled independently; guard and Styx still execute.
for(const order of [[0,1],[1,0]]) {
 const g=fresh(),value={players:[[...all.slice(1),{strategy_id:1002,enabled:false}],[]]};
 attach(g,value,order);g.start_of_game_setup();assert.deepEqual(g.players.map(p=>p.increase_atk),[0,0]);scenarios++;
}
// Guard stacks add to existing guards; one non-cost hit spends one, costs do not.
for(const amount of [1,7]) {
 const g=fresh();g.players[0].guard_up=2;attach(g,{players:[[e(3002)],[]]});g.start_of_game_setup();
 assert.equal(g.players[0].guard_up,3);g.reduce_idx_hp(0,amount,true);assert.equal(g.players[0].guard_up,3);
 const hp=g.players[0].hp;g.reduce_idx_hp(0,amount,false);assert.equal(g.players[0].hp,hp);assert.equal(g.players[0].guard_up,2);scenarios++;
}
// Full native debuff path: ward prevention; extra-debuff charge is not consumed for Styx.
for(const ward of [0,1,2]) {
 const g=fresh();g.players[0].hexproof=ward;g.players[0].gain_extra_debuff=5;
 attach(g,{players:[[e(7105)],[]]});g.start_of_game_setup();assert.equal(g.players[0].styx,2-ward);
 assert.equal(g.players[0].hp,40+3*(2-ward));assert.equal(g.players[0].gain_extra_debuff,5);scenarios++;
}
// Non-XiaoBu can receive the effect as an explicit software case; HP callback remains damage.
{
 const g=fresh();g.players[0].character='sw3';attach(g,{players:[[e(3002),e(7105)],[]]});g.start_of_game_setup();
 assert.equal(g.players[0].styx,2);assert.equal(g.players[0].hp,40);assert.equal(g.players[0].guard_up,0);scenarios++;
}
// Conversion applies to the attack buff acquisition rather than a raw increment.
{
 const g=fresh();g.players[0].convert_increase_atk_to_wood_thorn=1;
 attach(g,{players:[[e(1002)],[]]});g.start_of_game_setup();assert.equal(g.players[0].increase_atk,0);assert.equal(g.players[0].wood_thorn,1);assert.equal(g.players[1].increase_atk,1);scenarios++;
}
// Integration order: first owner's guard exists during second owner's1006; second guard does not yet exist.
for(const order of [[0,1],[1,0]]) {
 const g=fresh(),c=attach(g,{players:[all,all]},order,true);g.start_of_game_setup();
 const guards=c.metadata().events.filter(x=>x.strategy_id===3002);
 assert.equal(guards[0].after[0].guard_up,1);assert.equal(guards[1].before[1].guard_up,0);
 assert.deepEqual(c.metadata().events.filter(x=>x.strategy_id===1002).map(x=>x.player_index),order);scenarios++;
}
for(const value of [null,{}, {players:[[]]}, {players:[[],[]]}, {players:[[e(1002),e(1002)],[]]},
 {players:[[{strategy_id:1002}],[]]}, {players:[[{strategy_id:3002,enabled:true}],[]]}, {players:[[e(999)],[]]}]) {
 assert.throws(()=>createSeasonOpeningBatch(root,fresh(),value),/required/);scenarios++;
}
{
 const g=fresh(),c=createSeasonOpeningBatch(root,g,{players:[[e(3002)],[]]});c.installBoundary(3002);
 assert.throws(()=>g.start_of_game_setup(),/incomplete/);assert.throws(()=>c.installBoundary(3002),/duplicate/);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios}));
