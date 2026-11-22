import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerSpiritOutburst,installSpiritOutburst} from '../tools/current_spirit_outburst_v30.mjs';
import {registerCurrentStillness} from '../tools/current_stillness_v29.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerCurrentStillness(root,swogi);registerSpiritOutburst(root,swogi);
let scenarios=0;
function fresh(id='125971',install=true) {
  const g=new GameState(undefined,undefined,'spirit-outburst-boundaries');
  for(const p of g.players){p.hp=95;p.max_hp=100;p.max_physique=100;p.cards=[id,'601011','601011'];p.post_deck_setup();}
  g.players[1].hp=100;
  return [g,install?installSpiritOutburst(root,g,[0,1]):null];
}
function armed() {
  const [g,o]=fresh();g.play_card('125971',0);
  for(const p of g.players){p.hp=100;p.max_hp=100;}
  return [g,o];
}
for(let grade=1;grade<=3;grade++) {
  const id='12597'+grade;
  {
    const [g,o]=fresh(id),p=g.players[0];p.qi=2;g.play_card(id,0);
    assert.equal(p.qi,grade+3);assert.equal(p.hp,100);
    assert.equal(g.players[1].hp,100-(grade+2));
    assert.equal(o.forPlayer(p).remaining,grade+2);
    assert.deepEqual(p.can_play,[true,true,true]);assert.equal(p.this_card_chases,0);scenarios++;
  }
  {
    const [g,o]=fresh(id),p=g.players[0];p.qi=2;p.stillness_citta_dharma_stacks=3;
    g.play_card(id,0);
    const packets=o.metadata().events.filter(e=>e.kind==='overflow_damage').map(e=>e.requested);
    assert.deepEqual(packets,[3*grade-2,grade+7]);
    assert.equal(g.players[1].hp,100-(4*grade+5));scenarios++;
  }
  {
    const [g,o]=fresh(id),p=g.players[0];g.play_card(id,0);g.play_card(id,0);
    assert.equal(o.forPlayer(p).remaining,2*(grade+2));scenarios++;
  }
  {
    const [g,o]=fresh(id),p=g.players[0];p.strike_twice_stacks=1;g.play_card(id,0);
    assert.equal(o.forPlayer(p).remaining,2*(grade+2));
    assert.equal(o.metadata().events.filter(e=>e.kind==='card_body').length,2);scenarios++;
  }
  {
    const [g,o]=fresh(id),p=g.players[0];p.prevent_gain_hp_stacks=1;g.play_card(id,0);
    assert.equal(p.hp,95);assert.equal(g.players[1].hp,100);
    assert.equal(o.metadata().events.filter(e=>e.kind==='overflow_damage').length,0);scenarios++;
  }
  {
    const [g,o]=fresh(id),p=g.players[0];p.vitality_blossom_stacks=1;g.play_card(id,0);
    assert.equal(p.hp,100+grade);assert.equal(p.max_hp,100+grade);assert.equal(g.players[1].hp,100);scenarios++;
  }
  {
    const [g,o]=fresh(id),p=g.players[0];p.colorful_spirit_crane_stacks=1;g.play_card(id,0);
    assert.equal(p.qi,2*(grade+1));assert.equal(g.players[1].hp,100-(2*grade+1));scenarios++;
  }
  {
    const [g,o]=fresh(id),p=g.players[0];g.play_card(id,0);
    const n=o.forPlayer(p).remaining;
    g.reduce_idx_x_by_c(0,'god_opportunity_reversal_stacks',1);
    g.chase();g.process_this_card_chases();
    assert.equal(o.forPlayer(p).remaining,n);scenarios++;
  }
}
// Damage obeys defense and guard; attack bonuses do not modify this packet.
{
  const [g,o]=armed(),p=g.players[0],e=g.players[1];p.increase_atk=100;p.sword_intent=100;e.def=5;
  g.increase_idx_hp(0,8);assert.equal(e.hp,97);assert.equal(e.def,0);assert.equal(p.sword_intent,100);
  e.guard_up=1;g.increase_idx_hp(0,8);assert.equal(e.hp,97);assert.equal(e.guard_up,0);scenarios++;
}
// Modified healing and rejuvenation are applied before the overflow cap.
{
  const [g]=armed(),p=g.players[0];p.hp=99;p.indigestion=2;p.appetite=1;
  g.increase_idx_hp(0,6);assert.equal(g.players[1].hp,96);
  p.hp=95;p.indigestion=0;p.appetite=0;p.p2_rejuvenation_stacks=1;
  g.increase_idx_hp(0,8);assert.equal(p.max_hp,103);assert.equal(p.hp,103);assert.equal(g.players[1].hp,96);scenarios++;
}
// Type3 damage order is reversal373 -> overflow787 -> dream716.
{
  const [g]=armed(),p=g.players[0];p.hp=95;p.god_opportunity_reversal_stacks=2;p.dream_standing_firm_def_hp_damage_pct=50;
  const packets=[],old=g.deal_damage_inner.bind(g);
  g.deal_damage_inner=(amount,attack,idx)=>{packets.push([amount,attack,idx]);return old(amount,attack,idx);};
  g.increase_idx_hp(0,8);assert.deepEqual(packets,[[4,false,0],[3,false,0],[4,false,0]]);scenarios++;
}
// Converted healing and ordinary healing at nonpositive HP produce no overflow.
{
  const [g]=armed(),p=g.players[0];p.m_metal_spirit_seal_stacks=1;g.increase_idx_hp(0,8);
  assert.equal(p.penetrate,8);assert.equal(g.players[1].hp,100);
  p.m_metal_spirit_seal_stacks=0;p.hp=0;g.increase_idx_hp(0,8);
  assert.equal(p.hp,0);assert.equal(g.players[1].hp,100);scenarios++;
}
// Owner starts tick once, before regen. Opponent starts and chases never tick it.
{
  const [g,o]=armed(),p=g.players[0];p.cards=['601011','601011','601011'];p.post_deck_setup();p.regen=4;
  g.players[1].hp=10000;g.players[1].max_hp=10000;
  for(let expected=2;expected>=0;expected--) {
    p.hp=100;const before=o.metadata().events.filter(e=>e.kind==='overflow_damage').length;
    g.sim_turn();assert.equal(o.forPlayer(p).remaining,expected);
    assert.equal(o.metadata().events.filter(e=>e.kind==='overflow_damage').length-before,expected>0?1:0);
    g.players.reverse();g.sim_turn();assert.equal(o.forPlayer(p).remaining,expected);g.players.reverse();
  }
  scenarios++;
}
// Healing the other seat while the opponent acts damages the correct target.
{
  const [g,o]=armed(),p=g.players[0];g.players.reverse();g.increase_idx_hp(1,7);
  assert.equal(g.players[0].hp,93);assert.equal(p.hp,100);
  assert.equal(o.metadata().events.at(-1).player_index,0);assert.equal(o.metadata().events.at(-1).target_index,1);scenarios++;
}
// Inactive extension is observationally identical to the pinned shared engine.
{
  const [a]=fresh('601011',false),[b,o]=fresh('601011',true);
  for(const g of [a,b]){g.increase_idx_hp(0,8);g.sim_turn();}
  assert.deepEqual(a.players,b.players);assert.deepEqual(a.output,b.output);assert.equal(o.metadata(),null);scenarios++;
}
assert.throws(()=>registerSpiritOutburst(root,swogi),/alias collision/);scenarios++;
process.stdout.write(JSON.stringify({passed:true,scenarios}));
