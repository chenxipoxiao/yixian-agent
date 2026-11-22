import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createProbabilityQueue} from '../tools/current_probability_parameters_v88.mjs';
import {registerHexagramThunder} from '../tools/current_hexagram_thunder_v67.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerHexagramThunder(root,swogi);
const facts=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-thunder-parameters-v120.json')));
let scenarios=0;
function fresh(id='124071'){
 const g=new GameState(undefined,undefined,'typed-thunder-software');
 for(const p of g.players){p.character='he1';p.hp=500;p.max_hp=600;p.cards=[id,'601011','601011'];}
 g.start_of_game_setup();return g;
}
function body(g,id){g.players[0].currently_triggering_card_id=id;g.players[0].currently_triggering_card_idx=0;g.just_do_the_card_and_nothing_else(swogi[id]);}
for(const c of facts.cards.filter(c=>c.kind==='thunder_and_lightning'))for(const hex of [0,1,2]){
 const g=fresh(c.runtime_id),p=g.players[0];p.hexagram=hex;
 const stream=[hex?c.randomAttack:1,hex===2?c.randomAttack:1];
 const q=createProbabilityQueue(swogi,g,stream,[1,0],facts),hits=[],atk=g.atk.bind(g);
 g.atk=n=>{hits.push([n,q.metadata().consumed,p.qi,p.hexagram]);return atk(n);};
 body(g,c.runtime_id);q.verifyTerminal();
 assert.deepEqual(hits,[[stream[0],1,0,Math.max(0,hex-1)],[stream[1],2,hex?1:0,0]]);
 assert.equal(p.qi,hex);assert.equal(p.triggered_hexagram_count,hex);
 assert.equal(g.players[1].hp,500-stream[0]-stream[1]);
 assert(q.metadata().events.every(e=>e.player_index===1));scenarios++;
}
// A first-hit callback changes the second read, but cannot retroactively earn qi for the first.
{
 const g=fresh(),p=g.players[0],q=createProbabilityQueue(swogi,g,[4,10],[0,1],facts),atk=g.atk.bind(g);let first=true;
 g.atk=n=>{const out=atk(n);if(first){first=false;g.increase_idx_hexagram(0,1);}return out;};
 body(g,'124071');q.verifyTerminal();assert.deepEqual(q.metadata().events.map(e=>e.forced_by_hexagram),[false,true]);assert.equal(p.qi,1);scenarios++;
}
// Losing the remaining hexagram during a hit does not cancel the saved first-hit qi grant.
{
 const g=fresh(),p=g.players[0];p.hexagram=2;
 const q=createProbabilityQueue(swogi,g,[10,4],[0,1],facts),atk=g.atk.bind(g);let first=true;
 g.atk=n=>{const out=atk(n);if(first){first=false;g.reduce_idx_x_by_c(0,'hexagram',1);}return out;};
 body(g,'124071');q.verifyTerminal();assert.equal(p.qi,1);assert.deepEqual(q.metadata().events.map(e=>e.forced_by_hexagram),[true,false]);scenarios++;
}
{
 const g=fresh(),q=createProbabilityQueue(swogi,g,[10,4,1,13],[1,0],facts);
 body(g,'124071');g.players.reverse();body(g,'124072');q.verifyTerminal();
 assert.deepEqual(q.metadata().events.map(e=>[e.value,e.player_index]),[[10,1],[4,1],[1,0],[13,0]]);scenarios++;
}
for(const mode of ['zero','too_high','sentinel','underflow','unused','forced_wrong','outside','wrong_grade']){
 const g=fresh();let stream=[10,4];
 if(mode==='zero')stream=[0,4];if(mode==='too_high')stream=[11,4];if(mode==='sentinel')stream=[-1,4];
 if(mode==='underflow')stream=[10];if(mode==='unused')stream=[10,4,1];
 if(mode==='forced_wrong'){stream=[1,4];g.players[0].hexagram=1;}
 assert.throws(()=>{
  const q=createProbabilityQueue(swogi,g,stream,[0,1],facts);
  if(mode==='outside')g.rand_range(1,10);
  else if(mode==='wrong_grade'){g.players[0].currently_triggering_card_id='124072';g.just_do_the_card_and_nothing_else(swogi['124071']);}
  else{body(g,'124071');q.verifyTerminal();}
 },/probability_parameters_unresolved/);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios,real_replays:false}));
