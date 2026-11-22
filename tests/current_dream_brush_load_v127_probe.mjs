import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execute} from '../tools/full_battle_bridge_v127.mjs';
import {dreamBrushLoadFacts} from '../tools/current_dream_brush_load_v127.mjs';
import {createDreamQueue} from '../tools/current_dream_queue_v127.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const facts=dreamBrushLoadFacts(root),debuff=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-debuff-parameters-v87r2.json')));
const cases=[],scenario=(name,fn)=>{fn();cases.push(name);};
function fresh(cards=['D24015','111011','111011'],stream=null){
 const player=()=>({character:'he1',hp:1000,max_hp:2000,cultivation:50,round_number:10,destiny:100,qi:0,def:0,physique:0,max_physique:1000,hand_count:0,cards:[...cards]});
 return execute({players:[player(),player()],seed:'dream-software',first_player:0,max_turns:64,include_trace:false,current_rules_context:{realms:[5,5]}},({game:g,swogi})=>{
  g.start_of_game_setup();const q=stream===null?null:createDreamQueue(swogi,g,stream,[0,1],debuff,facts);
  return {g,p:g.players[0],enemy:g.players[1],q,swogi};
 });
}
for(const c of facts.cards.filter(c=>c.kind==='dream_load')){
 scenario('all-eight-positive-debuffs-'+c.raw_id,()=>{
  const {g,p}=fresh([c.runtime_id,'111011','111011']);for(const k of facts.debuff_fields)p[k]=2;
  p.internal_injury=-4;p.weaken=0;g.trigger_card(c.runtime_id,0);
  assert.equal(p.def,16+12*c.config.otherParams[0]);
 });
 scenario('passive-without-ever-playing-'+c.raw_id,()=>{
  const {g,p}=fresh(['111011',c.runtime_id,c.runtime_id]);p.def=7;const hp=p.hp;
  g.do_def_decay();assert.equal(p.def,3);assert.equal(p.hp,hp+4);
 });
}
scenario('moon-water-consumes-one-and-prevents-conversion',()=>{
 const {g,p}=fresh(['D14155']);p.def=7;p.moon_water_sword_formation_stacks=1;const hp=p.hp;
 g.do_def_decay();assert.equal(p.hp,hp);assert.equal(p.def,7);assert.equal(p.moon_water_sword_formation_stacks,0);
});
scenario('turtle-reduces-decay-before-regen',()=>{
 const {g,p}=fresh(['D14154']);p.def=7;p.black_earth_turtle_stacks=2;const hp=p.hp;
 g.do_def_decay();assert.equal(p.hp,hp+2);assert.equal(p.def,7);
});
scenario('heal-request-uses-saved-loss-not-callback-net-difference',()=>{
 const {g,p}=fresh(['D14155']);p.def=7;const hp=p.hp,reduce=g.reduce_idx_def.bind(g);
 g.reduce_idx_def=function(i,n){reduce(i,n);this.increase_idx_def(i,50);};
 g.do_def_decay();assert.equal(p.def,53);assert.equal(p.hp,hp+4);
});
scenario('no-defense-and-removed-card-do-not-heal',()=>{
 const {g,p}=fresh(['D14155']);const hp=p.hp;g.do_def_decay();assert.equal(p.hp,hp);
 p.def=7;p.cards[0]='111011';g.do_def_decay();assert.equal(p.hp,hp);assert.equal(p.def,3);
});
for(const c of facts.cards.filter(c=>c.kind==='dream_brush')){
 scenario('explicit-no-result-still-grants-defense-'+c.raw_id,()=>{
  const {g,p,q}=fresh([c.runtime_id],[-1]);g.trigger_card(c.runtime_id,0);q.verifyTerminal();
  assert.equal(p.def,c.config.def);assert.equal(p.cards[0],c.runtime_id);assert.equal(p.played_card_count,1);
 });
 scenario('temporary-execution-keeps-physical-slot-and-skips-costs-'+c.raw_id,()=>{
  const {g,p,q}=fresh([c.runtime_id],[10000065,10000035,10000002,10000001,10000015,10000036]);
  const hp=p.hp;p.strike_twice_stacks=1;const calls=[],pre=g.do_cloud_sword_softheart_and_friends.bind(g);
  g.do_cloud_sword_softheart_and_friends=function(id){calls.push([id,p.cards[0],p.trigger_depth]);return pre(id);};
  g.trigger_card(c.runtime_id,0);q.verifyTerminal();
  assert.equal(p.hp,hp);assert.equal(p.qi,0);assert.equal(p.strike_twice_stacks,1);assert.equal(p.cards[0],c.runtime_id);assert.equal(p.can_play[0],true);
  assert.equal(p.trigger_depth,0);assert.equal(p.played_card_count,7);
  assert.deepEqual(calls.map(c=>c[2]),[1,2,3,3,3,3,3]);assert.ok(calls.every(([id,physical])=>id===physical));
  assert.deepEqual(q.metadata().events.map(e=>e.value),[10000065,10000035,10000002,10000001,10000015,10000036]);
 });
}
scenario('nested-buff-reader-interleaves-with-card-readers',()=>{
 const {g,p,q}=fresh(undefined,[10000065,10000035,103,10000002,10000001,10000015,10000036]);
 p.crash_fist_truncate_stacks=1;p.decrease_atk=1;
 g.trigger_card('D24015',0);q.verifyTerminal();
 assert.deepEqual(q.metadata().events.map(e=>[e.queue_index,e.value]),[[0,10000065],[1,10000035],[2,103],[3,10000002],[4,10000001],[5,10000015],[6,10000036]]);
 assert.equal(q.metadata().events[2].phase,'next_crash_before_card');
});
for(const [name,stream,error] of [
 ['unknown-target',[999999999],/selected_card_not_admitted/],
 ['wrong-type',[1000001],/selected_card_not_admitted/],
 ['wrong-crash-grade',[10000065,10010035],/wrong_crash_identity_or_grade/],
 ['missing-next-parameter',[10000065],/parameter_underflow/],
 ['unused-result',[-1,-1],/unused_parameters/],
 ['boolean-result',[true],/invalid_stream/],
 ['empty-stream',[],/invalid_stream/]]){
 scenario(name,()=>assert.throws(()=>{const {g,q}=fresh(undefined,stream);g.trigger_card('D24015',0);q.verifyTerminal();},error));
}
scenario('bound-reader-required-without-rng-fallback',()=>{
 const {g}=fresh();assert.throws(()=>g.trigger_card('D24015',0),/bound_card_result_required/);
});
scenario('nested-failure-restores-original-slot',()=>{
 const {g,p}=fresh(undefined,[10000065,999999]);assert.throws(()=>g.trigger_card('D24015',0),/wrong_crash_identity/);assert.equal(p.cards[0],'D24015');
});
console.log(JSON.stringify({scenarios:cases.length,cases,real_replays:false}));
