import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createNestedCardQueue} from '../tools/current_nested_card_parameters_v89.mjs';
import {registerCurrentSectCards} from '../tools/current_sect_cards_v6.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerCurrentSectCards(root,swogi);
const facts=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-nested-card-parameters-v89.json')));
let scenarios=0;
function fresh(id){
 const g=new GameState(undefined,undefined,'nested-software');
 for(const p of g.players){p.character='he1';p.hp=1000;p.max_hp=1100;p.cards=[id,'601011','601011'];}
 g.start_of_game_setup();return g;
}
// Actual current values, all card grades / branches; no hexagram use.
for(const c of facts.cards.filter(c=>c.kind==='falling_paper'))for(const branch of [0,1,2]){
 const g=fresh(c.runtime_id),p=g.players[0];p.hexagram=3;
 const q=createNestedCardQueue(swogi,g,[branch],[1,0],facts),before={hp:p.hp,def:p.def,guard:p.guard_up};
 g.trigger_card(c.runtime_id,0);q.verifyTerminal();
 assert.equal(p.hp-before.hp,branch===1?c.config.otherParams[1]:0);
 assert.equal(p.def-before.def,branch===0?c.config.otherParams[0]:0);
 assert.equal(p.guard_up-before.guard,branch===2?c.config.otherParams[2]:0);
 assert.equal(p.hexagram,3);assert.equal(q.metadata().events[0].player_index,1);scenarios++;
}
// Nested effects run once; count both cards, keep costs / ordinary Execute
// repeat tokens untouched, restore slot, and skip outer-only extra triggers.
for(const c of facts.cards.filter(c=>c.kind==='divine'))for(const selected of facts.selected_targets){
 const g=fresh(c.runtime_id),p=g.players[0],enemy=g.players[1];p.unrestrained_sword_count=3;
 p.strike_twice_stacks=1;p.unrestrained_sword_twin_dragons_stacks=2;p.hexagram=4;
 const q=createNestedCardQueue(swogi,g,[selected.raw_id],[0,1],facts),beforeHp=p.hp,enemyHp=enemy.hp;
 const calls=[],pre=g.do_cloud_sword_softheart_and_friends.bind(g),extra=g.do_endless_sword_formation.bind(g);let outerExtras=0;
 g.do_cloud_sword_softheart_and_friends=function(id){calls.push([id,p.cards[0],p.trigger_depth]);return pre(id);};
 g.do_endless_sword_formation=function(){outerExtras++;return extra();};
 g.trigger_card(c.runtime_id,0);q.verifyTerminal();
 assert.deepEqual(calls,[[c.runtime_id,c.runtime_id,1],[selected.runtime_id,selected.runtime_id,2]]);
 assert.equal(outerExtras,1);assert.equal(p.cards[0],c.runtime_id);assert.equal(p.trigger_depth,0);
 assert.equal(p.unrestrained_sword_count,5);assert.equal(p.played_card_count,2);
 assert.equal(p.strike_twice_stacks,1);assert.equal(p.unrestrained_sword_twin_dragons_stacks,selected.raw_id===1000061?3:2);
 assert.equal(p.hp-beforeHp,c.config.otherParams[1]);assert.equal(p.def,c.config.def);assert.equal(p.hexagram,4);
 assert.equal(enemyHp-enemy.hp,selected.raw_id===1000061?2:selected.raw_id===1000102?7:11);
 assert.equal(q.metadata().events[0].before.def,c.config.def);
 assert.equal(q.metadata().events[0].restored_runtime_id,c.runtime_id);scenarios++;
}
// One FIFO across actors and types. The card identity is the exact stored ID.
{
 const g=fresh('344022');g.players[1].cards[0]='915081';
 const q=createNestedCardQueue(swogi,g,[1,1000061],[1,0],facts);
 g.trigger_card('344022',0);g.players.reverse();g.trigger_card('915081',0);q.verifyTerminal();
 assert.deepEqual(q.metadata().events.map(e=>[e.type,e.value,e.player_index]),[['effect_branch',1,1],['card_identity',1000061,0]]);scenarios++;
}
// Strict boundaries and empty/unknown streams, including all old RNG helpers.
for(const mode of ['empty','negative','boolean','branch','identity','extra','underflow','other_rng','preused','physical','active','twice']){
 const id=['identity','physical'].includes(mode)?'915081':'344021',g=fresh(id);
 let stream=id==='915081'?[1000061]:[0];
 if(mode==='empty')stream=[];if(mode==='negative')stream=[-1];if(mode==='boolean')stream=[true];
 if(mode==='branch')stream=[3];if(mode==='identity')stream=[1010061];if(mode==='extra')stream=[0,0];
 assert.throws(()=>{
  const q=createNestedCardQueue(swogi,g,stream,[0,1],facts);
  if(mode==='other_rng')g.random_int(3);
  else if(mode==='twice')createNestedCardQueue(swogi,g,stream,[0,1],facts);
  else if(mode==='active'){g.players[0].currently_triggering_card_id='601011';g.just_do_the_card_and_nothing_else(swogi[id]);}
  else{
   if(mode==='preused')g.used_randomness=true;
   if(mode==='physical')g.players[0].cards[0]='601011';
   g.trigger_card(id,0);if(mode==='underflow')g.trigger_card(id,0);q.verifyTerminal();
  }
 },/nested_card_parameters_unresolved/);scenarios++;
}
// A nested error cannot leave the physical slot transformed; the entire
// failed battle remains unresolved and is never a reward/settlement result.
{
 const g=fresh('915081'),p=g.players[0],base=g.trigger_card.bind(g);
 createNestedCardQueue(swogi,g,[1000061],[0,1],facts);
 g.trigger_card=function(id,slot){if(id==='215031')throw new Error('injected_nested_failure');return base(id,slot);};
 assert.throws(()=>g.trigger_card('915081',0),/injected_nested_failure/);assert.equal(p.cards[0],'915081');scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios,real_replays:false}));
