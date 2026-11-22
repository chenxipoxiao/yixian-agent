import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerChaseCards,installChaseCardsObserver} from '../tools/current_chase_cards_v50r2.mjs';
import {installCurrentQiPayment} from '../tools/current_qi_payment_v15.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const old={metal:swogi['132071'],finishing:swogi['345021'],overcome:swogi['634021']};
registerChaseCards(root,swogi);
assert.equal(old.metal,swogi['132071']);assert.equal(old.finishing,swogi['345021']);assert.equal(old.overcome,swogi['634021']);
assert.throws(()=>registerChaseCards(root,swogi),/alias_collision/);
let scenarios=0;
function fresh(cards) {
 const g=new GameState(undefined,undefined,'chase-cards-software');
 for(const p of g.players){p.character='sw1';p.hp=400;p.max_hp=500;p.max_physique=100;p.cards=[...cards];p.hand_count=0;}
 installCurrentQiPayment(g);g.start_of_game_setup();return g;
}
for(let grade=1;grade<=3;grade++) {
 const finish='75051'+grade,metal='75052'+grade,overcome='75050'+grade;
 // Installing the metal formation has no retroactive sharpness. A subsequent
 // metal card gets the existing formation before it installs additional stacks.
 {
  const g=fresh([metal,metal,'131011']),p=g.players[0];
  const o=installChaseCardsObserver(root,g,swogi,[1,0]);g.play_card(metal,0);
  assert.equal(p.penetrate,0);assert.equal(p.metal_spirit_formation_stacks,grade);
  assert.equal(p.activate_metal_spirit_stacks,1);assert.equal(p.can_play[0],false);assert.equal(p.this_card_chases,1);
  g.play_card(metal,1);assert.equal(p.penetrate,grade);assert.equal(p.metal_spirit_formation_stacks,2*grade);
  assert.equal(o.metadata().events[1].before.penetrate,grade);assert.equal(o.metadata().events[1].after.penetrate,grade);
  assert.ok(o.metadata().events.every(e=>e.player_index===1));scenarios++;
 }
 // Continuous marking and consumption marking are distinct. Nonmetal cards
 // cannot trigger metal formation; existing stacks add, not replace.
 {
  const g=fresh([metal,'131011','601011']),p=g.players[0];p.metal_spirit_formation_stacks=4;
  g.play_card(metal,0);assert.equal(p.penetrate,4);assert.equal(p.metal_spirit_formation_stacks,4+grade);
  g.play_card('131011',1);assert.equal(p.penetrate,4);assert.equal(swogi[metal].is_continuous,true);
  assert.equal(swogi[metal].is_consumption,false);assert.equal(swogi[metal].is_metal_spirit,true);scenarios++;
 }
 // Extreme Finishing adds charges before its chase. It does not upgrade itself.
 {
  const g=fresh([finish,'131011','601011']),p=g.players[0];g.sim_turn();
  assert.equal(p.cards[0],finish);assert.equal(p.cards[1],'131012');assert.equal(p.can_play[0],false);
  assert.equal(p.finishing_touch_stacks,grade-1);assert.equal(p.next_card_index,2);
  assert.equal(swogi[finish].is_consumption,true);assert.equal(swogi[finish].is_continuous,false);scenarios++;
 }
 // A max-grade next card keeps every charge. Ordinary281 then upgrades the next
 // eligible card; this is not the first-use, fixed-slot engraving13003 rule.
 {
  const g=fresh([finish,'131013','131011','601011']),p=g.players[0];g.sim_turn();
  assert.equal(p.cards[1],'131013');assert.equal(p.finishing_touch_stacks,grade);
  g.sim_turn();assert.equal(p.cards[2],'131012');assert.equal(p.finishing_touch_stacks,grade-1);scenarios++;
 }
 // Actual agility, rather than an unconditional native-overcome chase, is paid.
 {
  const g=fresh([overcome,'601011','601011']),p=g.players[0];g.sim_turn();
  assert.equal(p.qi,2*grade-1);assert.equal(p.agility,0);assert.equal(p.next_card_index,2);assert.equal(p.def,4);scenarios++;
 }
 // Correct immediate neighbours, including wrap, reversal and consumed slots.
 for(const reverse of [false,true]) {
  const g=fresh(reverse?[overcome,'131071','131011']:[overcome,'131011','131071']),p=g.players[0];
  if(reverse)p.card_play_direction=-1;
  p.can_play[reverse?1:2]=false;g.play_card(overcome,0);
  assert.equal(p.qi,2*grade-1);assert.equal(p.def,4);assert.equal(p.agility,10);
  assert.equal(p.activate_wood_spirit_stacks,1);assert.equal(p.this_card_chases,0);scenarios++;
 }
 // Fire-generation can broaden generation, but not the client's IsKeZhi.
 {
  const g=fresh([overcome,'131031','131011']),p=g.players[0];p.fire_spirit_generation_stacks=1;
  g.play_card(overcome,0);assert.equal(p.activate_fire_spirit_stacks,0);assert.equal(p.this_card_chases,0);scenarios++;
 }
 // Unknown temporary slot identity is not silently treated as a normal grid.
 {
  const g=fresh([overcome,'131011','131071']);g.players[0].trigger_depth=1;
  assert.throws(()=>g.trigger_card(overcome,0),/overcome_temporary_slot/);scenarios++;
 }
}
// Five exact overcoming pairs; each generates only its named next activation.
const ids={metal:'131071',wood:'131011',earth:'131051',water:'131091',fire:'131031'};
for(const [a,b] of [['metal','wood'],['wood','earth'],['earth','water'],['water','fire'],['fire','metal']]) {
 const g=fresh(['750501',ids[b],ids[a]]),p=g.players[0];g.play_card('750501',0);
 assert.equal(p['activate_'+b+'_spirit_stacks'],1);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios}));
