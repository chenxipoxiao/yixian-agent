import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerDragonTail,installDragonTail} from '../tools/current_dragon_tail_v33.mjs';
import {installCurrentQiPayment} from '../tools/current_qi_payment_v15.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerDragonTail(root,swogi);
let scenarios=0;
function fresh(grade=1) {
 const g=new GameState(undefined,undefined,'dragon-tail-boundaries'),id='12396'+grade;
 for(const p of g.players){p.hp=50;p.max_hp=100;p.max_physique=100;p.cards=['601011',id,'601011'];p.post_deck_setup();}
 g.players[0].next_card_index=1;g.players[1].hp=300;g.players[1].max_hp=300;
 installCurrentQiPayment(g);const trace=installDragonTail(root,g);
 return {g,p:g.players[0],id,trace};
}
for(let grade=1;grade<=3;grade++) {
 const heal=[7,11,15][grade-1];
 {
  const {g,p,id,trace}=fresh(grade);g.play_card(id,1);
  assert.equal(p.hp,50+heal);assert.equal(p.def,0);assert.equal(p.next_card_index,0);
  assert.equal(p.can_play[1],true);assert.equal(trace.metadata().events[0].post_action,false);scenarios++;
 }
 {
  const {g,p,id}=fresh(grade);p.can_post_action[1]=true;g.play_card(id,1);
  assert.equal(p.def,Math.trunc(heal/2));assert.equal(p.next_card_index,1);scenarios++;
 }
 {
  const {g,p,id,trace}=fresh(grade);p.hp=100;p.can_post_action[1]=true;g.play_card(id,1);
  assert.equal(p.hp,100);assert.equal(p.def,Math.trunc(heal/2));assert.equal(trace.metadata().events[0].healing_count,heal);scenarios++;
 }
 {
  const {g,p,id}=fresh(grade);p.hp_gained_this_turn=5;p.preemptive_strike_stacks=1;g.play_card(id,1);
  assert.equal(p.def,Math.trunc((5+heal)/2));assert.equal(p.next_card_index,0);scenarios++;
 }
 {
  const {g,p,id}=fresh(grade);p.prevent_gain_hp_stacks=1;p.can_post_action[1]=true;p.hp_gained_this_turn=5;g.play_card(id,1);
  assert.equal(p.hp,50);assert.equal(p.hp_gained_this_turn,5);assert.equal(p.def,2);scenarios++;
 }
 {
  const {g,p,id,trace}=fresh(grade);p.p2_post_strike_stacks=1;p.preemptive_strike_stacks=1;g.play_card(id,1);
  assert.equal(p.hp,52+heal);assert.equal(p.max_hp,102);assert.equal(p.def,2+Math.trunc((heal+2)/2));
  assert.equal(trace.metadata().events[0].healing_count,heal+2);scenarios++;
 }
 {
  const {g,p,id,trace}=fresh(grade);p.strike_twice_stacks=1;g.play_card(id,1);
  assert.equal(p.hp,50+2*heal);assert.equal(p.def,heal);assert.equal(p.next_card_index,0);
  assert.deepEqual(trace.metadata().events.filter(e=>e.kind==='card_body').map(e=>e.first_use),[true,false]);scenarios++;
 }
}
{
 const {g,p}=fresh();p.can_play[0]=false;g.sim_turn();
 assert.equal(p.next_card_index,2);assert.equal(p.hp_gained_this_turn,7);scenarios++;
}
{
 const {g,p}=fresh();p.can_post_action[1]=true;p.hp_gained_this_turn=100;g.sim_turn();
 assert.equal(p.def,3);assert.equal(p.hp_gained_this_turn,7);assert.equal(p.next_card_index,2);scenarios++;
}
{
 const {g,p,id}=fresh();p.card_play_direction=-1;g.play_card(id,1);assert.equal(p.next_card_index,2);scenarios++;
}
{
 const {g,id,trace}=fresh();g.players.reverse();g.players[0].next_card_index=1;g.play_card(id,1);
 assert.equal(trace.metadata().events[0].player_index,1);scenarios++;
}
{
 const {g,p,id,trace}=fresh();const before=[p.hp,p.def,p.next_card_index];
 swogi['dragon-tail-test-copy']={...swogi['601011'],card_actions:x=>x.trigger_card(id,0)};
 p.cards[0]='dragon-tail-test-copy';
 assert.throws(()=>g.play_card('dragon-tail-test-copy',0),/temporary_card_identity/);
 assert.deepEqual([p.hp,p.def,p.next_card_index],before);assert.equal(trace.metadata(),null);scenarios++;
}
{
 const {g}=fresh();assert.throws(()=>installDragonTail(root,g),/already_installed/);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios}));
