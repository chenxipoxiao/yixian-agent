import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerCurrentDelayedCards,installCurrentDelayedEffects} from '../tools/current_delayed_effects_v17.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const original={...swogi};registerCurrentDelayedCards(root,swogi);
for(const id of Object.keys(original))assert.strictEqual(swogi[id],original[id]);
let checked=0;
function fresh(id='601011',fields={},enemy={}) {
 const g=new GameState(undefined,undefined,'software-boundary-v17');
 Object.assign(g.players[0],{cards:[id,'601011','121031'],hp:50,max_hp:100,qi:0,def:0,
  currently_playing_card_idx:0,currently_triggering_card_idx:0,currently_triggering_card_id:id},fields);
 Object.assign(g.players[1],{cards:['601011'],hp:1000,max_hp:1000,qi:0,def:0},enemy);
 const ledger=installCurrentDelayedEffects(root,g,swogi);
 return [g,ledger];
}
function before(g,id='601011',idx=0) {
 Object.assign(g.players[0],{currently_triggering_card_idx:idx,currently_triggering_card_id:id,currently_playing_card_idx:idx});
 g.do_water_spirit_formation(id);
}
for(let grade=0;grade<3;grade++) {
 const wood=String(135981+grade),earth=String(135991+grade),star=String(124951+grade);
 for(const active of [0,1]) {
  const [g,l]=fresh(wood,{activate_wood_spirit_stacks:active});swogi[wood].card_actions(g);
  assert.equal(g.players[0].qi,3+grade);assert.equal(g.players[1].hp,1000);
  assert.equal(l.forPlayer(g.players[0])[777],active?(3+grade):0);
  for(let i=0;i<5+grade;i++) {
   g.players[0].increase_atk=i;
   const hp=g.players[1].hp;before(g);
   assert.equal(hp-g.players[1].hp,active&&i<3+grade?1+i:0);
  }
  assert.equal(l.forPlayer(g.players[0])[777],0);checked++;
  const [e,el]=fresh(earth,{activate_earth_spirit_stacks:active});swogi[earth].card_actions(e);
  assert.equal(e.players[0].def,5*grade);assert.equal(e.players[0].agility,active?10:0);
  assert.equal(el.forPlayer(e.players[0])[779],1);checked++;
 }
 // An already active effect is paid before this new copy supplies new charges.
 {
  const [g,l]=fresh(wood,{activate_wood_spirit_stacks:1});swogi[wood].card_actions(g);
  g.trigger_card(wood,0);
  assert.equal(g.players[1].hp,999);assert.equal(l.forPlayer(g.players[0])[777],2*(3+grade)-1);checked++;
 }
 {
  const [g,l]=fresh(star);swogi[star].card_actions(g);
  assert.equal(g.players[1].hp,999);assert.equal(g.players[0].qi,2+grade);
  assert.equal(l.forPlayer(g.players[0])[778],2+grade);
  before(g,'601011');assert.equal(l.forPlayer(g.players[0])[778],2+grade);
  // Before attack, the actual triggering slot is converted and healed once.
  before(g,'121031',1);assert.equal(g.players[0].is_star_point[1],true);
  assert.equal(g.players[0].hp,55);assert.equal(g.players[0].star_power,0);
  before(g,'121031',1);assert.equal(g.players[0].star_power,1);assert.equal(g.players[0].hp,55);
  assert.equal(l.forPlayer(g.players[0])[778],grade);checked++;
 }
}
// The heal request is independent of how much HP the enemy actually lost.
for(const enemy of [{guard_up:1},{covert_shift_stacks:1},{hp:1}]) {
 const [g,l]=fresh('135981',{activate_wood_spirit_stacks:1,increase_atk:3},enemy);
 swogi['135981'].card_actions(g);before(g);assert.equal(g.players[0].hp,54);
 assert.equal(l.forPlayer(g.players[0])[777],2);checked++;
}
{
 const [g,l]=fresh('135981',{activate_wood_spirit_stacks:1,prevent_gain_hp_stacks:1,increase_atk:2});
 swogi['135981'].card_actions(g);before(g);assert.equal(g.players[0].hp,50);
 assert.equal(g.players[1].hp,997);assert.equal(l.forPlayer(g.players[0])[777],2);checked++;
}
// Real native attacks include defense, wound, penetration and HP protection.
for(const attack of [1,2,3,8,9,12])for(const defense of [0,2,20])for(const guard of [0,1]) {
 const [g,l]=fresh('135991',{}, {def:defense,guard_up:guard});swogi['135991'].card_actions(g);
 const hp=g.players[1].hp;g.atk(attack);
 assert.equal(g.players[0].def,Math.trunc((hp-g.players[1].hp)/3));
 assert.equal(l.forPlayer(g.players[0])[779],0);
 const gained=g.players[0].def;g.atk(12);assert.equal(g.players[0].def,gained);checked++;
}
{
 const [g,l]=fresh('135991',{penetrate:3},{def:2,wound:2});swogi['135991'].card_actions(g);
 g.atk(9);assert.equal(g.players[1].hp,988);assert.equal(g.players[0].def,4);
 assert.equal(l.forPlayer(g.players[0])[779],0);checked++;
}
{
 const [g,l]=fresh('135991',{}, {hp:2});swogi['135991'].card_actions(g);g.atk(9);
 assert.equal(g.players[1].hp,-7);assert.equal(g.players[0].def,3);checked++;
}
{
 const [g,l]=fresh('135991');swogi['135991'].card_actions(g);swogi['135991'].card_actions(g);
 g.deal_damage(9);assert.equal(l.forPlayer(g.players[0])[779],2);assert.equal(g.players[0].def,0);
 g.atk(8);g.atk(9);g.atk(12);assert.equal(g.players[0].def,5);
 assert.equal(l.forPlayer(g.players[0])[779],0);checked++;
}
{
 const [g,l]=fresh('135991',{}, {repel_citta_dharma_stacks:3});swogi['135991'].card_actions(g);g.atk(12);
 // Defense must exist when the counterattack starts, not after atk returns.
 assert.equal(g.players[0].hp,50);assert.equal(g.players[0].def,1);checked++;
}
{
 const [g,l]=fresh('135991');swogi['135991'].card_actions(g);g.atk(9,true);
 assert.equal(g.players[0].def,3);assert.equal(l.forPlayer(g.players[0])[779],0);checked++;
}
{
 const [g,l]=fresh('135981',{activate_wood_spirit_stacks:1});swogi['135981'].card_actions(g);
 const owner=g.players[0];g.players.reverse();before(g);assert.equal(l.forPlayer(owner)[777],3);
 g.players.reverse();before(g);assert.equal(l.forPlayer(owner)[777],2);checked++;
}
{
 const [g,l]=fresh('124951');swogi['124951'].card_actions(g);g.current_gain_delayed(777,1);
 g.players[0].is_star_point[1]=true;g.players[0].increase_atk=2;
 const order=[],addStar=g.increase_idx_star_power.bind(g),lose=g.reduce_idx_hp.bind(g);
 g.increase_idx_star_power=(...args)=>{order.push('star');return addStar(...args);};
 g.reduce_idx_hp=(...args)=>{order.push('steal');return lose(...args);};
 before(g,'121031',1);assert.deepEqual(order,['star','steal']);checked++;
}
assert.throws(()=>registerCurrentDelayedCards(root,swogi),/alias collision/);
console.log(JSON.stringify({passed:true,checked,old_entries_unchanged:Object.keys(original).length}));
