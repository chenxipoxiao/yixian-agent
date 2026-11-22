import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerTemporaryChase,installTemporaryChase} from '../tools/current_temporary_chase_v61.mjs';
import {installCurrentQiPayment} from '../tools/current_qi_payment_v61.mjs';
import {installCurrentSoundScheduler} from '../tools/current_sound_scheduler_v61.mjs';
import {installChasePayment} from '../tools/current_chase_payment_v61.mjs';
import {installChaseSoundScheduler} from '../tools/current_chase_sound_scheduler_v61.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const ordinary=swogi['601011'];registerTemporaryChase(root,swogi);assert.equal(swogi['601011'],ordinary);
assert.throws(()=>registerTemporaryChase(root,swogi),/alias_collision/);
let scenarios=0;
function fresh(cards,install=installCurrentQiPayment) {
 const g=new GameState(undefined,undefined,'temporary-chase-software');
 for(const p of g.players){p.character='sw1';p.hp=400;p.max_hp=400;p.max_physique=100;p.cards=[...cards];p.hand_count=0;}
 install(g,(_id,_idx,cost)=>cost);const observer=installTemporaryChase(root,g,[1,0]);
 g.start_of_game_setup();return {g,p:g.players[0],q:g.players[1],observer};
}
for(const install of [installCurrentQiPayment,installCurrentSoundScheduler,installChasePayment,installChaseSoundScheduler]) {
 for(let grade=1;grade<=3;grade++) {
  const id='76100'+grade;
  // One body finishes every hit before adding capacity. The pending owner
  // survives a seat reversal and cleanup preserves a permanent extra chase.
  {
   const {g,p,q,observer:o}=fresh([id,'601011','601011'],install);p.max_chases=2;
   g.play_card(id,0);assert.equal(q.hp,400-5*grade);assert.equal(p.max_chases,3);assert.equal(o.pendingFor(p),1);
   assert.equal(p.this_card_chases,1);assert.equal(o.metadata().events[0].player_index,1);
   g.players.reverse();g.current_temporary_chase_cleanup();assert.equal(p.max_chases,3);assert.equal(o.pendingFor(p),1);
   g.players.reverse();g.current_temporary_chase_cleanup();assert.equal(p.max_chases,2);assert.equal(o.pendingFor(p),0);
   const n=o.metadata().events.length;g.current_temporary_chase_cleanup();assert.equal(o.metadata().events.length,n);scenarios++;
  }
  // Consecutive bodies stack two capacity increments, allowing the second
  // requested chase and the third played card, then both increments expire.
  {
   const {g,p,q,observer:o}=fresh([id,id,'601011','601011'],install);g.sim_turn();
   assert.equal(q.hp,400-10*grade-3);assert.equal(p.next_card_index,3);assert.equal(p.chases,2);
   assert.equal(p.max_chases,1);assert.equal(o.pendingFor(p),0);
   assert.equal(o.metadata().events.at(-1).removed572,2);
   g.sim_turn();assert.equal(p.next_card_index,0);assert.equal(p.max_chases,1);scenarios++;
  }
  // Entangle stops the requested chase, not the body's capacity gain. Its
  // temporary increment still expires during that same owner turn.
  {
   const {g,p,q,observer:o}=fresh([id,'601011','601011'],install);p.entangle=1;g.sim_turn();
   assert.equal(q.hp,400-5*grade);assert.equal(p.next_card_index,1);assert.equal(p.max_chases,1);
   assert.equal(o.pendingFor(p),0);assert.equal(p.chases,0);scenarios++;
  }
 }
}
// Unaffected turns emit no metadata and do not create a permanent-state field.
{
 const {g,p,observer:o}=fresh(['601011','601011','601011']);g.sim_turn();
 assert.equal(o.metadata(),null);assert.equal(p.max_chases,1);scenarios++;
}
// Native death short-circuits before turn-end: do not invent a cleanup event.
{
 const {g,q,observer:o}=fresh(['761001','601011','601011']);q.hp=1;g.sim_turn();
 assert.equal(g.game_over,true);assert.equal(o.metadata().events.filter(e=>e.kind==='owner_turn_end').length,0);scenarios++;
}
// A temporary nested execution has the same body and capacity, without relying
// on a hidden replay grid identity or marking that physical grid as consumed.
{
 const {g,p,observer:o}=fresh(['601011','601011','601011']);p.trigger_depth=1;
 g.trigger_card('761002',0);assert.equal(p.max_chases,2);assert.equal(o.pendingFor(p),1);
 assert.equal(o.metadata().events[0].trigger_depth,2);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios}));
