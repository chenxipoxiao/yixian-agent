import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createProbabilityQueue} from '../tools/current_probability_parameters_v88.mjs';
import {registerHexagramThunder,installHexagramThunder} from '../tools/current_hexagram_thunder_v67.mjs';
import {installThunderTiming} from '../tools/current_thunder_timing_v68.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerHexagramThunder(root,swogi);
const facts=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-probability-parameters-v88.json')));
let scenarios=0;
function fresh(id='601011'){
 const g=new GameState(undefined,undefined,'probability-software');
 for(const p of g.players){p.character='he1';p.hp=500;p.max_hp=600;p.cards=[id,'601011','601011'];}
 g.start_of_game_setup();installHexagramThunder(root,g,swogi);installThunderTiming(root,g,swogi);return g;
}
function body(g,id){g.players[0].currently_triggering_card_id=id;g.players[0].currently_triggering_card_idx=0;g.just_do_the_card_and_nothing_else(swogi[id]);}
// Every grade: strict success/failure boundary, inclusive magnitudes, and one
// consumed entry for each guaranteed branch (including five pre-hit requests).
for(const c of facts.cards)for(const forced of [false,true]){
 const g=fresh(c.runtime_id),p=g.players[0];
 const stream=c.reads.map(r=>r.type==='range'?(forced?r.hi:r.lo):(forced?r.threshold-1:r.threshold));
 p.hexagram=forced?c.reads.length:0;
 const q=createProbabilityQueue(swogi,g,stream,[1,0],facts);body(g,c.runtime_id);q.verifyTerminal();
 const m=q.metadata();assert.equal(m.consumed,c.reads.length);assert(m.events.every(e=>e.player_index===1));
 assert.equal(p.hexagram,0);assert.equal(p.triggered_hexagram_count,forced?c.reads.length:0);
 assert(m.events.filter(e=>e.type==='probability').every(e=>e.result===forced));scenarios++;
}
// The producer domain is unknown: an exact nonnegative int32 is compared as
// recorded, not rescaled to [0,1], modulo100, clipped or sampled.
for(const value of [0,10,11,99,100,2147483647]){
 const g=fresh('122081'),q=createProbabilityQueue(swogi,g,[value],[0,1],facts);
 body(g,'122081');q.verifyTerminal();assert.equal(g.players[1].weaken,value<11?1:0);scenarios++;
}
// Mixed types, simultaneous-sealed starts, actor swaps: one shared FIFO.
{
 const g=fresh('121101'),q=createProbabilityQueue(swogi,g,[9,4,10],[1,0],facts);
 body(g,'121101');body(g,'122071');g.players.reverse();body(g,'122081');q.verifyTerminal();
 assert.deepEqual(q.metadata().events.map(e=>[e.type,e.value,e.player_index]),[['probability',9,1],['range',4,1],['probability',10,0]]);scenarios++;
}
// Effects before/after consumption follow the client, not a generic roll-first
// approximation: Golden attacks then roll, White Snake rolls then attack.
{
 const g=fresh('122081'),q=createProbabilityQueue(swogi,g,[0,0],[0,1],facts),seen=[],atk=g.atk.bind(g);
 g.atk=n=>{seen.push([n,q.metadata().consumed]);return atk(n);};
 body(g,'122081');body(g,'123041');q.verifyTerminal();assert.deepEqual(seen,[[11,0],[6,2]]);scenarios++;
}
// Five Thunders settles all five outcomes before any hit callback, which may
// itself grant hexagram. Newly gained hexagram must not alter later rolls.
{
 const g=fresh('125041'),q=createProbabilityQueue(swogi,g,[0,30,29,50,99],[0,1],facts),seen=[],atk=g.atk.bind(g);
 g.atk=n=>{seen.push(q.metadata().consumed);g.increase_idx_hexagram(0,1);return atk(n);};
 body(g,'125041');q.verifyTerminal();assert.deepEqual(seen,[5,5]);assert.equal(g.players[0].hexagram,2);scenarios++;
}
// Lotus magnitudes and probability are separate; a hit callback can grant the
// hexagram consumed by its later probability read. Defense gain is separate.
{
 const g=fresh('767021'),q=createProbabilityQueue(swogi,g,[4,0],[0,1],facts),atk=g.atk.bind(g);
 let first=true;g.atk=n=>{const out=atk(n);if(first){first=false;g.increase_idx_hexagram(0,1);}return out;};
 body(g,'767021');q.verifyTerminal();assert.deepEqual(q.metadata().events.map(e=>e.forced_by_hexagram),[false,true]);assert.equal(g.players[0].hexproof,2);scenarios++;
}
// Both range and probability discrepancies reject forced outcomes. Unrelated
// guaranteed/random helpers cannot bypass rejection by avoiding rng().
for(const mode of ['missing','extra','negative','forced_probability','forced_range','wrong_type','wrong_arguments','outside','other','resonance','twice']){
 const g=fresh('121101');let stream=[0];
 if(mode==='extra')stream=[0,0];if(mode==='negative')stream=[-1];
 if(mode==='forced_probability'){stream=[10];g.players[0].hexagram=1;}
 if(mode==='forced_range'){stream=[6];g.players[0].hexagram=1;}
 if(mode==='resonance')g.players[0].resonance_test=1;
 assert.throws(()=>{
  const altered=structuredClone(facts);
  if(mode==='wrong_type')altered.cards.find(c=>c.runtime_id==='121101').reads=[{type:'range',lo:1,hi:10}];
  if(mode==='wrong_arguments')altered.cards.find(c=>c.runtime_id==='121101').reads=[{type:'probability',threshold:11}];
  const q=createProbabilityQueue(swogi,g,stream,[0,1],altered);
  if(mode==='wrong_type'||mode==='wrong_arguments'){body(g,'121101');
  }else if(mode==='outside')g.if_c_pct(10);
  else if(mode==='other'){g.players[0].hexagram=2;g.trigger_hexagram(0);}
  else if(mode==='twice')createProbabilityQueue(swogi,g,stream,[0,1],facts);
  else if(mode==='forced_range')body(g,'122061');
  else{body(g,'121101');if(mode==='missing')body(g,'121101');q.verifyTerminal();}
 },/probability_parameters_unresolved/);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios,real_replays:false}));
