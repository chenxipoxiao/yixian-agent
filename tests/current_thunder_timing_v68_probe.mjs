import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installThunderTiming} from '../tools/current_thunder_timing_v68.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
let scenarios=0;
function fresh(grade=1,order=[0,1]){
 const g=new GameState(undefined,undefined,'five-thunders-timing');
 for(const p of g.players){p.character='he1';p.hp=1000;p.max_hp=1000;p.cards=['601011','601011','601011'];p.max_physique=100;}
 const id='12504'+grade;g.players[0].cards[0]=id;const ext=installThunderTiming(root,g,swogi,order);g.start_of_game_setup();
 const p=g.players[0],q=g.players[1];p.currently_playing_card_idx=0;p.currently_triggering_card_idx=0;p.currently_triggering_card_id=id;p.trigger_depth=1;
 return {g,p,q,ext,id,body:()=>g.just_do_the_card_and_nothing_else(swogi[id])};
}
// Exhaustive five-result patterns verify no hit interleaves a pending draw.
for(let grade=1;grade<=3;grade++)for(let mask=0;mask<32;mask++){
 const {g,ext,body}=fresh(grade);const calls=[];let n=0,hits=0;
 g.if_c_pct=chance=>{assert.equal(chance,30);calls.push('draw');return Boolean(mask&(1<<n++));};
 g.atk=amount=>{assert.equal(n,5);assert.equal(amount,[8,10,12][grade-1]);calls.push('hit');hits++;};body();
 assert.deepEqual(calls.slice(0,5),Array(5).fill('draw'));assert.equal(hits,mask.toString(2).replaceAll('0','').length);
 assert.equal(ext.metadata().events[0].hits,hits);scenarios++;
}
// Each request consumes one hexagram, independently; equality at30% fails.
for(let hex=0;hex<=5;hex++){
 const {g,p,q,body,ext}=fresh();p.hexagram=hex;let random=0;g.rng=()=>{random++;return 0.3;};body();
 assert.equal(random,5-hex);assert.equal(p.hexagram,0);assert.equal(q.hp,1000-8*hex);assert.equal(p.triggered_hexagram_count,hex);
 assert.equal(ext.metadata().events[0].hexagram_before_hits,0);scenarios++;
}
// A hit callback that grants hexagram cannot retroactively guarantee earlier draws.
{
 const {g,p,q,body,ext}=fresh();p.hexagram=1;let random=0;g.rng=()=>{random++;return 0.99;};
 const hit=g.atk.bind(g);g.atk=(...args)=>{hit(...args);g.increase_idx_hexagram(0,1);};body();
 assert.equal(random,4);assert.equal(q.hp,992);assert.equal(p.hexagram,1);assert.equal(ext.metadata().events[0].hits,1);scenarios++;
}
// Multi-hit remains sequential: shield then two guards then two wound hits.
{
 const {g,p,q,body}=fresh();p.hexagram=5;q.def=13;q.guard_up=2;q.wound=3;g.rng=()=>{throw new Error('unexpected rng');};body();
 assert.equal(q.hp,978);assert.equal(q.def,0);assert.equal(q.guard_up,0);assert.equal(p.attack_count,5);scenarios++;
}
// Fatal hit does not truncate the already requested hit sequence or judge victory.
{
 const {g,p,q,body,ext}=fresh(3,[1,0]);p.hexagram=5;q.hp=1;body();
 assert.equal(q.hp,-59);assert.equal(ext.metadata().events[0].player_index,1);assert.equal(p.attack_count,5);assert.equal(g.game_over,false);scenarios++;
}
// Unsupported typed consumers remain blocked rather than using native randomness.
{
 const {g,q,body}=fresh();g.if_c_pct=()=>{throw new Error('typed_parameters_unresolved:unsupported_consumer:if_c_pct');};
 assert.throws(body,/unsupported_consumer/);assert.equal(q.hp,1000);scenarios++;
}
// Repeated bodies have fresh independent success counts; no retained accumulator.
{
 const {g,p,q,body,ext}=fresh();p.hexagram=5;g.rng=()=>0.9;body();body();assert.equal(q.hp,960);
 assert.deepEqual(ext.metadata().events.map(e=>e.hits),[5,0]);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios}));
