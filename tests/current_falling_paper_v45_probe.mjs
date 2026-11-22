import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installFallingPaper} from '../tools/current_falling_paper_v45.mjs';
import {installDragonQi} from '../tools/current_dragon_qi_v40.mjs';
import {installCloudsRain} from '../tools/current_clouds_rain_v39.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
let scenarios=0;
const canonical=v=>Array.isArray(v)?'['+v.map(canonical).join(',')+']':v!==null&&typeof v==='object'?'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}':JSON.stringify(v);
function fresh(){const g=new GameState(undefined,undefined,'paper-software');for(const p of g.players){
 p.character='sw3';p.hp=43;p.max_hp=100;p.max_physique=100;p.cards=['601011','601011','601011'];p.hand_count=2;
}return g;}
function spec(g,owners,stream){const battle={software_only:true,players:g.players.map(p=>({hp:p.hp,max_hp:p.max_hp,cards:p.cards}))};
 const value={owners,stream,battle_sha256:crypto.createHash('sha256').update(canonical(battle)).digest('hex')};return {battle,value};}
for(const order of [[0,1],[1,0]])for(const branch of [0,1,2,3]){
 const g=fresh(),{battle,value}=spec(g,[true,true],[branch,branch]);const m=installFallingPaper(root,g,value,order,battle);
 g.start_of_game_setup();m.verifyTerminal();const events=m.metadata().events;
 assert.deepEqual(events.map(e=>e.player_index),order);assert.equal(events.length,2);
 for(const e of events){assert.equal(e.before.hp,43);assert.equal(e.after.hp,branch===0?47:43);
  assert.equal(e.after.max_hp,branch===0?104:100);assert.equal(e.after.def,branch===1?4:0);assert.equal(e.after.weaken,branch===3?1:0);}
 assert.equal(m.metadata().pending_match_rewards.length,branch===2?2:0);
 assert.equal(m.metadata().authoritative_exchange_credit_applied,false);
 g.do_plant_start_permanent_buffs();assert.equal(m.metadata().events.length,2);m.verifyTerminal();scenarios++;
}
// A shared queue follows actual first/second startup, not original snapshot order.
for(const order of [[0,1],[1,0]]){
 const g=fresh(),{battle,value}=spec(g,[true,true],[0,3]);const m=installFallingPaper(root,g,value,order,battle);
 g.start_of_game_setup();m.verifyTerminal();assert.deepEqual(m.metadata().events.map(e=>[e.player_index,e.branch]),[[order[0],0],[order[1],3]]);
 assert.equal(g.players[0].hp,47);assert.equal(g.players[1].weaken,1);scenarios++;
}
// One owner consumes one entry, including when the other player starts first.
for(const order of [[0,1],[1,0]]){
 const g=fresh(),{battle,value}=spec(g,[true,false],[2]);const m=installFallingPaper(root,g,value,order,battle);
 g.start_of_game_setup();m.verifyTerminal();assert.deepEqual(m.metadata().events.map(e=>e.player_index),[0]);
 assert.deepEqual(m.metadata().pending_match_rewards,[{player_index:0,kind:'exchange_chance',amount:1,authoritative_credit_applied:false}]);scenarios++;
}
// Compute the requested heal once, before a max-HP callback can change HP.
{
 const g=fresh(),{battle,value}=spec(g,[true,false],[0]);const max=g.increase_idx_max_hp.bind(g);const order=[];
 g.increase_idx_max_hp=(i,n)=>{order.push(['max',n]);max(i,n);g.players[i].hp+=7;};
 const hp=g.increase_idx_hp.bind(g);g.increase_idx_hp=(i,n)=>{order.push(['hp',n]);return hp(i,n);};
 const m=installFallingPaper(root,g,value,[0,1],battle);g.start_of_game_setup();m.verifyTerminal();
 assert.deepEqual(order,[['max',4],['hp',4]]);assert.equal(g.players[0].hp,54);scenarios++;
}
// Wrapper order is3011 arming,16024 then7069; a max-HP callback consumes the armed bonus.
{
 const g=fresh(),{battle,value}=spec(g,[true,false],[0]);const clouds=installCloudsRain(root,g,{players:[{hand:[15,15],board:[0,0,0]},null]});
 const paper=installFallingPaper(root,g,value,[0,1],battle),max=g.increase_idx_max_hp.bind(g);
 g.increase_idx_max_hp=(i,n)=>{max(i,n);g.increase_idx_qi(i,1);};
 const dragon=installDragonQi(root,g,{players:[{strategy_id:3011},null]});
 g.start_of_game_setup();paper.verifyTerminal();assert.equal(g.players[0].qi,4);
 assert.equal(dragon.metadata().events.find(e=>e.kind==='first_positive_qi').delegated_amount,3);
 assert.equal(clouds.metadata().events[0].qi_before,3);scenarios++;
}
for(const stream of [[],[0,1],[4],[-1],[true],[1.2]]){
 const g=fresh(),{battle,value}=spec(g,[true,false],stream);assert.throws(()=>installFallingPaper(root,g,value,[0,1],battle),/invalid_complete_stream/);scenarios++;
}
for(const kind of ['changed_battle','duplicate_order','missing_binding','both_unowned']){
 const g=fresh(),{battle,value}=spec(g,[true,false],[0]);let order=[0,1];
 if(kind==='changed_battle')battle.players[0].hp++;
 if(kind==='duplicate_order')order=[0,0];
 if(kind==='missing_binding')delete value.battle_sha256;
 if(kind==='both_unowned')value.owners=[false,false];
 assert.throws(()=>installFallingPaper(root,g,value,order,battle),/falling_paper_unresolved/);scenarios++;
}
for(const when of ['before','during','after','rng_call','missing_opening']){
 const g=fresh(),{battle,value}=spec(g,[true,false],[0]);const m=installFallingPaper(root,g,value,[0,1],battle);
 if(when==='before'){g.used_randomness=true;assert.throws(()=>g.start_of_game_setup(),/other_random_consumer/);}
 if(when==='during'){g.increase_idx_max_hp=()=>g.rng();assert.throws(()=>g.start_of_game_setup(),/other_random_consumer/);}
 if(when==='after'){g.start_of_game_setup();g.used_randomness=true;assert.throws(()=>m.verifyTerminal(),/other_random_consumer/);}
 if(when==='rng_call')assert.throws(()=>g.rng(),/other_random_consumer/);
 if(when==='missing_opening')assert.throws(()=>m.verifyTerminal(),/unused_parameters_or_missing_opening/);
 scenarios++;
}
for(const hp of [-1,214748365]){
 const g=fresh();g.players[0].hp=hp;const {battle,value}=spec(g,[true,false],[0]);installFallingPaper(root,g,value,[0,1],battle);
 assert.throws(()=>g.do_plant_start_permanent_buffs(),/unsupported_hp_or_int32_overflow/);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios}));
