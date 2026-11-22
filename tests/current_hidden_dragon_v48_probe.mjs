import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerCurrentChainCards} from '../tools/current_chain_cards_v11.mjs';
import {registerHiddenDragonClassification} from '../tools/current_hidden_dragon_v48.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const {installCurrentDelayedEffects}=await import('../tools/current_delayed_effects_v17.mjs');
registerCurrentChainCards(root,swogi);
const ordinary=swogi['601011'],old=Object.fromEntries(['612921','612922','612923'].map(id=>[id,swogi[id]]));
registerHiddenDragonClassification(root,swogi);
assert.equal(swogi['601011'],ordinary);
assert.throws(()=>registerHiddenDragonClassification(root,swogi),/Unexpected Hidden Dragon/);
let scenarios=0;
function fresh(id){
 const g=new GameState(undefined,undefined,'hidden-dragon-classification-software');
 for(const p of g.players){p.character='sw3';p.hp=500;p.max_hp=500;p.max_physique=100;p.cards=[id,'601011','601011'];p.hand_count=0;}
 installCurrentDelayedEffects(root,g,swogi);g.start_of_game_setup();g.players[0].hp=200;return g;
}
for(const [id,attack,count] of [['612921',7,2],['612922',11,3],['612923',15,4]]){
 // Inherent classification is present before the body grants the next-card status.
 const g=fresh(id),p=g.players[0];
 assert.equal(p.m_light_sword_stacks,0);assert.ok(g.is_cloud_sword(id)&&g.is_unrestrained_sword(id)&&g.is_sword(id));
 assert.equal(swogi[id].card_actions,old[id].card_actions);scenarios++;
 for(const def of [0,2,100])for(const temporary of [0,1]){
  const h=fresh(id),me=h.players[0];me.unrestrained_sword_zero_stacks=50;me.m_light_sword_stacks=temporary;
  h.players[1].def=def;
  const heals=[],heal=h.heal.bind(h);h.heal=n=>{heals.push(n);return heal(n);};
  h.play_card(id,0);
  const damage=Math.max(0,attack-def),recovery=Math.floor(damage/2);
  assert.equal(h.players[1].hp,500-damage);assert.equal(me.hp,200+recovery);
  assert.deepEqual(heals,damage>0?[recovery]:[]);scenarios++;
 }
 // Native post-card hooks count the inherent identity once, then consume exactly
 // the advertised number of subsequent ordinary cards; no duplicate healing.
 for(const cloudBefore of [0,1]){
  const h=fresh(id),me=h.players[0];me.cloud_sword_chain_count=cloudBefore;me.unrestrained_sword_zero_stacks=50;
  h.play_card(id,0);assert.equal(me.unrestrained_sword_count,1);
  const granted=cloudBefore?count:1;assert.equal(me.m_light_sword_stacks,granted);
  for(let i=0;i<granted;i++)h.play_card('601011',1);
  assert.equal(me.m_light_sword_stacks,0);assert.equal(me.unrestrained_sword_count,1+granted);
  assert.equal(me.hp,200+Math.floor(attack/2)+granted);
  h.play_card('601011',1);assert.equal(me.unrestrained_sword_count,1+granted);
  assert.equal(me.hp,200+Math.floor(attack/2)+granted);scenarios++;
 }
}
// The base ordinary card never becomes intrinsically Unrestrained.
{
 const g=fresh('612921');g.players[0].unrestrained_sword_zero_stacks=50;
 assert.equal(g.is_unrestrained_sword('601011'),false);g.play_card('601011',1);
 assert.equal(g.players[0].hp,200);assert.equal(g.players[0].unrestrained_sword_count,0);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios}));
