import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createTypedCardQueue} from '../tools/current_card_parameters_v86.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const facts=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-card-parameters-v86.json')));
let scenarios=0;
function fresh(){const g=new GameState(undefined,undefined,'typed-cards-software');for(const p of g.players){p.character='he1';p.hp=50;p.max_hp=100;p.cards=['601011','601011','601011'];}g.start_of_game_setup();g.players[1].hp=80;return g;}
function body(g,id){g.players[0].currently_triggering_card_id=id;g.players[0].currently_triggering_card_idx=0;g.just_do_the_card_and_nothing_else(swogi[id]);}
for(const card of facts.cards)for(const order of [[0,1],[1,0]])for(const forced of [false,true]){
 const g=fresh(),[lo,hi]=card.otherParams,amount=forced?hi:lo+1;g.players[0].hexagram=forced?2:0;
 const m=createTypedCardQueue(swogi,g,[amount],order,facts);body(g,card.runtime_id);m.verifyTerminal();
 assert.equal(g.players[0].hexagram,forced?1:0);assert.equal(g.players[0].triggered_hexagram_count,forced?1:0);
 if(card.kind==='qi_therapy'){assert.equal(g.players[0].hp,50+amount);assert.equal(g.players[0].max_hp,100+lo);}
 else{assert.equal(g.players[1].hp,80-card.attackCount*card.attack);assert.equal(g.players[1].max_hp,100-amount);}
 const event=m.metadata().events[0];assert.equal(event.player_index,order[0]);assert.equal(event.value,amount);assert.equal(event.forced_by_hexagram,forced);scenarios++;
}
{
 const g=fresh(),m=createTypedCardQueue(swogi,g,[13,9,21],[0,1],facts);
 g.players[0].hexagram=1;
 const attack=g.atk.bind(g),max=g.reduce_enemy_max_hp.bind(g),calls=[];
 g.atk=n=>{calls.push(['attack',n,m.metadata().consumed,g.players[0].hexagram]);return attack(n);};
 g.reduce_enemy_max_hp=n=>{calls.push(['cap',n,m.metadata().consumed,g.players[0].hexagram]);return max(n);};
 body(g,'122071');assert.deepEqual(calls,[['attack',5,0,1],['attack',5,0,1],['cap',13,1,0]]);
 g.players.reverse();body(g,'123081');g.players.reverse();body(g,'122073');m.verifyTerminal();
 assert.deepEqual(m.metadata().events.map(e=>e.player_index),[0,1,0]);assert.deepEqual(m.metadata().events.map(e=>e.queue_index),[0,1,2]);scenarios++;
}
{
 const g=fresh();g.players[0].hexagram=1;const m=createTypedCardQueue(swogi,g,[18],[1,0],facts),calls=[];
 const max=g.increase_idx_max_hp.bind(g),hp=g.increase_idx_hp.bind(g);
 g.increase_idx_max_hp=(i,n)=>{calls.push(['cap',n,m.metadata().consumed,g.players[i].hexagram]);return max(i,n);};
 g.increase_idx_hp=(i,n)=>{calls.push(['hp',n,m.metadata().consumed,g.players[i].hexagram]);return hp(i,n);};
 body(g,'123081');m.verifyTerminal();assert.deepEqual(calls,[['cap',8,1,0],['hp',18,1,0]]);scenarios++;
}
for(const which of ['out_of_range','forced_mismatch','underflow','leftover','other_before','other_after','repeat']){
 const g=fresh(),stream=which==='out_of_range'?[7]:which==='leftover'?[9,9]:[9];
 if(which==='forced_mismatch')g.players[0].hexagram=1;
 const m=createTypedCardQueue(swogi,g,stream,[0,1],facts);
 if(which==='other_before'){g.used_randomness=true;assert.throws(()=>body(g,'123081'),/other_random_consumer/);}
 else if(which==='repeat')assert.throws(()=>createTypedCardQueue(swogi,g,stream,[0,1],facts),/already_installed/);
 else if(which==='out_of_range')assert.throws(()=>body(g,'123081'),/parameter_out_of_range/);
 else if(which==='forced_mismatch')assert.throws(()=>body(g,'123081'),/forced_hexagram_result_mismatch/);
 else{body(g,'123081');if(which==='underflow')assert.throws(()=>body(g,'123081'),/parameter_underflow/);
  else if(which==='leftover')assert.throws(()=>m.verifyTerminal(),/unused_parameters/);
  else{g.used_randomness=true;assert.throws(()=>m.verifyTerminal(),/other_random_consumer/);}}
 scenarios++;
}
for(const method of [...facts.blocked_random_entrypoints,'rng']){
 const g=fresh();g.players[0].hexagram=10;createTypedCardQueue(swogi,g,[18],[0,1],facts);
 assert.throws(()=>g[method](0,1,1),/card_parameters_unresolved/);scenarios++;
}
for(const stream of [[],[true],[NaN],[-1],[2147483648]]){assert.throws(()=>createTypedCardQueue(swogi,fresh(),stream,[0,1],facts),/invalid_stream/);scenarios++;}
console.log(JSON.stringify({passed:true,scenarios}));
