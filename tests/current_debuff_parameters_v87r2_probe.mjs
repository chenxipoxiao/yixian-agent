import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createDebuffQueue} from '../tools/current_debuff_parameters_v87r2.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const facts=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-debuff-parameters-v87r2.json')));
let scenarios=0;
function fresh(){const g=new GameState(undefined,undefined,'debuff-software');for(const p of g.players){p.character='he1';p.hp=80;p.max_hp=120;p.max_physique=100;p.physique=0;p.cards=['601011','601011','601011'];}g.start_of_game_setup();return g;}
function body(g,id){g.players[0].currently_triggering_card_id=id;g.players[0].currently_triggering_card_idx=0;g.just_do_the_card_and_nothing_else(swogi[id]);}
// Every grade consumes the exact prescribed number even with no removable buff.
for(const c of facts.cards.filter(c=>c.kind!=="demon_breaking_palm"))for(const order of [[0,1],[1,0]]){
 const g=fresh(),p=g.players[0];p.hexagram=2;
 const n=c.kind==='mad_obsession'?c.otherParams[1]:c.kind==='exorcism_elixir'?c.otherParams[0]:1;
 // The deterministic third Mad grade may appear inside another bound stream.
 const stream=n?Array(n).fill(c.kind==='mad_obsession'?101:-1):[-1];
 const q=createDebuffQueue(swogi,g,stream,order,facts);body(g,c.runtime_id);
 assert.equal(p.hexagram,2);assert.equal(p.triggered_hexagram_count,0);
 if(c.kind==='mad_obsession'){
  assert.equal(p.weaken,n);assert.equal(p.styx,c.otherParams[0]);assert.equal(p.physique,1+c.otherParams[0]+n);
 }
 if(n){q.verifyTerminal();assert.equal(q.metadata().consumed,n);assert(q.metadata().events.every(e=>e.player_index===order[0]));}
 else{assert.equal(q.metadata().consumed,0);assert.throws(()=>q.verifyTerminal(),/unused_parameters/);}
 scenarios++;
}
// Existing gain callback: hexproof blocks styx, random debuffs remain ordered.
{
 const g=fresh();g.players[0].hexproof=2;const q=createDebuffQueue(swogi,g,[101,104],[0,1],facts);
 body(g,'643011');q.verifyTerminal();assert.equal(g.players[0].styx,0);assert.equal(g.players[0].weaken,1);
 assert.equal(g.players[0].entangle,1);assert.equal(g.players[0].physique,3);scenarios++;
}
// Source GetDebuffCount counts positive category1 layers, including indigestion.
{
 const g=fresh();g.players[0].indigestion=3;g.players[0].wound=-2;
 const q=createDebuffQueue(swogi,g,[100,101],[1,0],facts);body(g,'643011');q.verifyTerminal();
 assert.equal(g.players[0].physique,8);scenarios++;
}
// Mixed add/remove consumers retain actual styx loss and explicit no-op entries.
{
 const g=fresh(),q=createDebuffQueue(swogi,g,[100,102,367,100,-1],[0,1],facts);
 body(g,'643011');const hp=g.players[0].hp;body(g,'312021');assert.equal(g.players[0].hp,hp-6);
 body(g,'141091');q.verifyTerminal();assert.deepEqual(q.metadata().events.map(e=>e.kind),['mad_obsession','mad_obsession','exorcism_elixir','exorcism_elixir','thousand_catty']);
 assert.equal(g.players[0].internal_injury,0);assert.equal(g.players[0].flaw,1);scenarios++;
}
// Attack precedes the thousand-catty read; transfer loss precedes target gain.
{
 const g=fresh(),calls=[];g.players[0].styx=1;g.players[1].hexproof=1;
 const q=createDebuffQueue(swogi,g,[367,-1],[0,1],facts),remove=g.reduce_idx_x_by_c.bind(g),gain=g.increase_idx_debuff.bind(g),atk=g.atk.bind(g);
 g.reduce_idx_x_by_c=(i,k,n)=>{if(k==='styx')calls.push(['remove',q.metadata().consumed]);return remove(i,k,n);};
 g.increase_idx_debuff=(i,k,n)=>{calls.push(['gain',i,q.metadata().consumed]);return gain(i,k,n);};
 g.atk=n=>{calls.push(['attack',q.metadata().consumed]);return atk(n);};
 body(g,'143021');body(g,'141091');q.verifyTerminal();
 assert.deepEqual(calls,[['remove',1],['gain',1,1],['attack',1],['attack',1]]);
 assert.equal(g.players[0].hp,77);assert.equal(g.players[1].styx,0);assert.equal(g.players[1].hexproof,0);scenarios++;
}
// Next-crash stack count is a loop, not a single random transfer. Seat can swap.
{
 const g=fresh(),q=createDebuffQueue(swogi,g,[100,100,-1],[1,0],facts);
 g.players[0].internal_injury=2;g.players[0].crash_fist_truncate_stacks=2;
 g.players[0].currently_triggering_card_id='143021';g.do_pre_crash_fist('143021');
 assert.equal(g.players[1].internal_injury,2);assert.equal(g.players[0].crash_fist_truncate_stacks,0);
 g.players.reverse();body(g,'141091');q.verifyTerminal();
 assert.deepEqual(q.metadata().events.map(e=>e.player_index),[1,1,0]);
 assert.deepEqual(q.metadata().events.slice(0,2).map(e=>e.phase),['next_crash_before_card','next_crash_before_card']);scenarios++;
}
// Conversion differs from repeated cleansing: -1 breaks its loop, then all
// successfully removed layers become attack before the card's hits.
for(const id of ['645021','645022','645023']){
 const g=fresh();g.players[0].physique=58;g.players[0].styx=1;
 const q=createDebuffQueue(swogi,g,[367,-1,-1],[0,1],facts),calls=[],gain=g.increase_idx_x_by_c.bind(g),atk=g.atk.bind(g);
 g.increase_idx_x_by_c=(i,k,n)=>{if(k==='increase_atk')calls.push(['gain',n,q.metadata().consumed]);return gain(i,k,n);};
 g.atk=n=>{calls.push(['hit',q.metadata().consumed,g.players[0].increase_atk]);return atk(n);};
 body(g,id);assert.equal(q.metadata().consumed,2);assert.equal(g.players[0].increase_atk,1);
 assert.deepEqual(calls[0],['gain',1,2]);assert(calls.slice(1).every(x=>x[0]==='hit'&&x[1]===2&&x[2]===1));
 body(g,'141091');q.verifyTerminal();assert.equal(q.metadata().events[1].breaks_conversion_loop,true);scenarios++;
}
{
 const g=fresh(),q=createDebuffQueue(swogi,g,[-1],[0,1],facts);body(g,'645021');assert.equal(q.metadata().consumed,0);
 body(g,'141091');q.verifyTerminal();scenarios++;
}
for(const which of ['unknown','absent','underflow','leftover','random_before','random_after','repeat','add_styx']){
 const g=fresh(),stream=which==='unknown'?[999]:which==='add_styx'?[367,100]:which==='absent'?[101]:[-1];
 const q=createDebuffQueue(swogi,g,stream,[0,1],facts);
 if(which==='unknown')assert.throws(()=>body(g,'141091'),/unknown_buff_id/);
 else if(which==='absent')assert.throws(()=>body(g,'141091'),/selected_debuff_not_present/);
 else if(which==='add_styx')assert.throws(()=>body(g,'643011'),/unsupported_random_add_buff_id/);
 else if(which==='repeat')assert.throws(()=>createDebuffQueue(swogi,g,stream,[0,1],facts),/already_installed/);
 else if(which==='leftover')assert.throws(()=>q.verifyTerminal(),/unused_parameters/);
 else if(which==='random_before'){g.used_randomness=true;assert.throws(()=>body(g,'141091'),/other_random_consumer/);}
 else {body(g,'141091');if(which==='underflow')assert.throws(()=>body(g,'141091'),/parameter_underflow/);
  else{g.used_randomness=true;assert.throws(()=>q.verifyTerminal(),/other_random_consumer/);}}
 scenarios++;
}
for(const method of [...facts.blocked_random_entrypoints,'rng']){
 const g=fresh();g.players[0].hexagram=10;createDebuffQueue(swogi,g,[-1],[0,1],facts);
 assert.throws(()=>g[method](0,1,1),/debuff_parameters_unresolved/);scenarios++;
}
for(const stream of [[],[true],[NaN],[-2],[2147483648]]){assert.throws(()=>createDebuffQueue(swogi,fresh(),stream,[0,1],facts),/invalid_stream/);scenarios++;}
console.log(JSON.stringify({passed:true,scenarios}));
