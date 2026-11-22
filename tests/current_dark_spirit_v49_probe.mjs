import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerDarkSpirit,installDarkSpiritObserver} from '../tools/current_dark_spirit_v49.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const ordinary=swogi['601011'];registerDarkSpirit(root,swogi);
assert.equal(swogi['601011'],ordinary);
assert.throws(()=>registerDarkSpirit(root,swogi),/alias collision/);
let scenarios=0;
function fresh(id) {
 const g=new GameState(undefined,undefined,'dark-spirit-software');
 for(const p of g.players){p.character='dx1';p.hp=200;p.max_hp=500;p.max_physique=100;p.cards=[id,'601011','601011'];p.hand_count=0;}
 g.start_of_game_setup();return g;
}
for(const [id,qi,n] of [['744061',2,3],['744062',3,4],['744063',4,5]]) {
 // No hidden attack, cost, chase or consumption in the card body.
 {
  const g=fresh(id),p=g.players[0],hp=g.players[1].hp;
  const order=[],q=g.increase_idx_qi.bind(g),b=g.increase_idx_x_by_c.bind(g),d=g.increase_idx_debuff.bind(g);
  g.increase_idx_qi=(idx,c)=>{order.push('qi');return q(idx,c);};
  g.increase_idx_x_by_c=(idx,x,c)=>{order.push(x);return b(idx,x,c);};
  g.increase_idx_debuff=(idx,x,c)=>{order.push(x);return d(idx,x,c);};
  swogi[id].card_actions(g);
  assert.deepEqual(order,['qi','increase_atk','decrease_atk','agility']);
  assert.equal(p.qi,qi);assert.equal(p.increase_atk,n);assert.equal(p.decrease_atk,n);assert.equal(p.agility,n);
  assert.equal(g.players[1].hp,hp);assert.equal(p.this_card_chases,0);scenarios++;
 }
 // Final body count sees actual post-callback layers, including partial/full purity.
 for(const protection of [0,1,n,n+2]) {
  const g=fresh(id),p=g.players[0];p.hexproof=protection;p.internal_injury=2;
  swogi[id].card_actions(g);
  assert.equal(p.hexproof,Math.max(0,protection-n));assert.equal(p.decrease_atk,Math.max(0,n-protection));
  assert.equal(p.agility,2+Math.max(0,n-protection));scenarios++;
 }
 // All eight categories count layers; unrelated buffs do not. Food status was
 // omitted by the reference helper. The new card must include it.
 {
  const g=fresh(id),p=g.players[0];
  Object.assign(p,{internal_injury:1,weaken:2,flaw:3,decrease_atk:4,entangle:5,wound:6,styx:7,indigestion:8,force:3,def:20,agility:2});
  swogi[id].card_actions(g);assert.equal(p.agility,2+36+n);assert.equal(p.def,20);scenarios++;
 }
 // A nonpositive stored entry is not in GetDebuffList; do not subtract it.
 {
  const g=fresh(id),p=g.players[0];p.internal_injury=-4;p.indigestion=3;
  swogi[id].card_actions(g);assert.equal(p.agility,n+3);scenarios++;
 }
 // Two real uses accumulate old debuffs and recount after each new gain.
 {
  const g=fresh(id),p=g.players[0];const observer=installDarkSpiritObserver(root,g,swogi,[1,0]);
  g.play_card(id,0);g.play_card(id,0);
  assert.equal(p.qi,qi*2);assert.equal(p.increase_atk,n*2);assert.equal(p.decrease_atk,n*2);assert.equal(p.agility,n*3);
  const e=observer.metadata().events;assert.equal(e.length,2);assert.deepEqual(e.map(x=>x.positive_debuff_layers_after),[n,n*2]);
  assert.ok(e.every(x=>x.player_index===1&&x.slot===0));assert.equal(observer.metadata().recorded_action_log,false);scenarios++;
 }
 // Native debuff gain can heal and add internal injury; the count is taken
 // after both callbacks, not from a precomputed amount or number of categories.
 {
  const g=fresh(id),p=g.players[0];p.unwavering_soul_stacks=1;p.m_ruthless_water_stacks=1;
  const hp=p.hp;swogi[id].card_actions(g);
  assert.equal(p.decrease_atk,n);assert.equal(p.internal_injury,n);assert.equal(p.hp,hp+2*n);assert.equal(p.agility,2*n);scenarios++;
 }
 // The card itself grants no chase. The existing turn scheduler spends ten
 // agility on a subsequent card when the resulting total reaches the threshold.
 {
  const g=fresh(id),p=g.players[0];p.agility=10-n;
  const observer=installDarkSpiritObserver(root,g,swogi);g.sim_turn();
  assert.equal(observer.metadata().events[0].after.agility,10);
  assert.equal(p.agility,0);assert.equal(p.next_card_index,2);scenarios++;
 }
}
console.log(JSON.stringify({passed:true,scenarios}));
