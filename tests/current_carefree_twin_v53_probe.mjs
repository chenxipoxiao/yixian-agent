import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installCarefreeTwin} from '../tools/current_carefree_twin_v53.mjs';
import {installCurrentNormalAttackV53} from '../tools/current_normal_attack_v53.mjs';
import {createSoundControl} from '../tools/current_sound_control_v52r2.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const facts=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-carefree-twin-v53.json')));
const rt=id=>facts.metadata[id].runtime_id;
let scenarios=0;
function fresh(raw=[[1000001,0,0],[0,0,0]]){
 const g=new GameState(undefined,undefined,'carefree-twin-boundaries');
 g.players.forEach((p,i)=>{p.hp=100;p.max_hp=100;p.cards=raw[i].map(rt);p.post_deck_setup();});return g;
}
function attach(g,ids=[5001,5009],raw=[[1000001,0,0],[0,0,0]],slot=0,order=[0,1]){
 const bySeat=order.map(i=>raw[i]);
 return installCarefreeTwin(root,g,swogi,{players:[ids.map(strategy_id=>({strategy_id,slot})),[]],raw_boards:bySeat},order);
}
for(const id of [5001,5009])for(const slot of [0,1,7]){
 const g=fresh(),e=attach(g,[id],undefined,slot);g.play_card(rt(1000001),0);
 assert.equal(g.players[1].hp,id===5009&&slot===0?88:94);
 assert.equal(g.players[0].this_card_chases,id===5001&&slot===0?1:0);
 assert.equal(e.metadata().events.length,slot===0?1:0);scenarios++;
}
// Both effects fire on each actual use. Repetition does not recurse or create two turns.
{
 const g=fresh(),e=attach(g);g.play_card(rt(1000001),0);
 assert.equal(g.players[1].hp,88);assert.equal(g.players[0].played_card_count,2);
 assert.equal(g.players[0].this_card_chases,2);g.process_this_card_chases();assert.equal(g.players[0].chases,1);
 g.play_card(rt(1000001),0);assert.equal(g.players[1].hp,76);assert.equal(g.players[0].played_card_count,4);
 assert.equal(e.metadata().events.filter(e=>e.strategy_id===5009).length,2);scenarios++;
}
// Full card grade is not the acquisition realm. A max-grade Qi-refining card qualifies.
for(const rawId of [1000012,1020012]){
 const raw=[[rawId,0,0],[0,0,0]],g=fresh(raw);attach(g,[5001,5009],raw);g.play_card(rt(rawId),0);
 assert.equal(g.players[0].def,rawId===1000012?8:12);
 assert.equal(g.players[0].sword_intent,rawId===1000012?4:8);
 assert.equal(g.players[0].this_card_chases,2);scenarios++;
}
// Hidden ordinary attacks and late-realm cards do not become eligible by their grid.
for(const rawId of [0,10000,20000,1000042]){
 const raw=[[rawId,0,0],[0,0,0]],g=fresh(raw),e=attach(g,[5001,5009],raw);g.play_card(rt(rawId),0);
 assert.equal(e.metadata().events.length,0);assert.equal(g.players[0].played_card_count,1);scenarios++;
}
// Realm2 is twin-eligible but not carefree-eligible; no second Qi payment.
{
 const raw=[[1010017,0,0],[0,0,0]],g=fresh(raw),e=attach(g,[5001,5009],raw);
 g.players[0].qi=0;g.play_card(rt(1010017),0);
 assert.equal(g.players[0].qi,2);assert.equal(g.players[0].sword_intent,8);
 assert.equal(g.players[0].this_card_chases,0);assert.deepEqual(e.metadata().events.map(x=>x.strategy_id),[5009]);scenarios++;
}
// Consumption marks the card for later traversal; the current twin effect still resolves.
{
 const raw=[[2000001,0,0],[0,0,0]],g=fresh(raw);g.players[0].hp=60;
 attach(g,[5009],raw);g.play_card(rt(2000001),0);
 assert.equal(g.players[0].hp,76);assert.deepEqual(g.players[0].can_play,[false,true,true]);scenarios++;
}
// Existing repeat charge adds to twin rather than multiplying its repetitions.
{
 const g=fresh();attach(g,[5009]);g.players[0].strike_twice_stacks=1;g.play_card(rt(1000001),0);
 assert.equal(g.players[1].hp,82);assert.equal(g.players[0].played_card_count,3);
 assert.equal(g.players[0].strike_twice_stacks,0);scenarios++;
}
// Temporary ExecuteEffect has no Execute-level twin, and carefree excludes temporary cards.
{
 const g=fresh(),e=attach(g);g.players[0].trigger_depth=1;g.trigger_card(rt(1000001),0);
 assert.equal(g.players[1].hp,94);assert.equal(g.players[0].this_card_chases,0);assert.equal(e.metadata().events.length,0);scenarios++;
}
// A transformed known identity resolves by current card, without repeating the transform.
{
 const raw=[[1000012,0,0],[0,0,0]],g=fresh(raw),e=attach(g,[5009],raw);
 g.players[0].cards[0]=rt(1020012);g.play_card(rt(1020012),0);
 assert.equal(g.players[0].def,12);assert.equal(e.metadata().events[0].raw_id,1020012);scenarios++;
}
{
 const raw=[[1000012,0,0],[0,0,0]],g=fresh(raw);
 const sound=createSoundControl(root,g,swogi,{players:[[{strategy_id:1007,enabled:true}],[]],raw_boards:raw},[0,1]);
 for(const id of [1007,1005,1003])sound.installBoundary(id);
 attach(g,[5009],raw);g.do_plant_start_permanent_buffs();g.do_finishing_touch(0);g.play_card(g.players[0].cards[0],0);
 assert.equal(g.players[0].cards[0],rt(1010012));assert.equal(g.players[0].finishing_touch_stacks,0);
 assert.equal(sound.metadata().events.filter(e=>e.phase==='before_card_body_281').length,1);scenarios++;
}
// Active later280 repeat is rejected, not silently reordered with5009.
{
 const g=fresh();attach(g,[5009]);g.players[0].ultimate_overcome_formation_stacks=1;
 assert.throws(()=>g.play_card(rt(1000001),0),/twin_ultimate_overcome_order_required/);
 assert.equal(g.players[1].hp,100);scenarios++;
}
// Player identity remains stable through initiative ordering and swaps.
{
 const raw=[[0,0,0],[1000001,0,0]],g=fresh(raw),e=attach(g,[5009],raw,0,[1,0]);
 g.play_card(rt(0),0);assert.equal(e.metadata().events.length,0);g.swap_players();g.play_card(rt(1000001),0);
 assert.equal(e.metadata().events[0].player_index,0);assert.equal(g.players[1].hp,88);scenarios++;
}
for(const id of [0,10000,20000]){
 const raw=[[id,id,id],[0,0,0]],g=fresh(raw),e=installCurrentNormalAttackV53(root,g,{players:[[5008],[]]},[0,1]);
 g.do_plant_start_permanent_buffs();g.play_card(rt(id),0);
 const base=id===0?3:id===10000?6:9;assert.equal(g.players[1].hp,100-base-3);
 assert.equal(g.players[0].increase_atk,3);assert.deepEqual(g.players[0].can_play,[false,true,true]);
 g.do_plant_start_permanent_buffs();g.play_card(rt(id),1);
 assert.equal(g.players[1].hp,100-2*(base+3));assert.equal(e.metadata().events.length,1);scenarios++;
}
{
 const raw=[[0,0,0],[0,0,0]],g=fresh(raw),e=installCurrentNormalAttackV53(root,g,{players:[[5004,5008,5011],[]]},[0,1]);
 g.do_plant_start_permanent_buffs();g.players[0].strike_twice_stacks=1;g.play_card(rt(0),0);
 assert.deepEqual(e.metadata().events.map(x=>x.effect_id),[5004,5008,5011,5004]);
 assert.equal(g.players[1].hp,88);assert.equal(g.players[0].agility,28);assert.equal(g.players[1].weaken,3);scenarios++;
}
{
 const raw=[[0,0,0],[0,0,0]],g=fresh(raw),e=installCurrentNormalAttackV53(root,g,{players:[[5008],[]]},[0,1]);
 g.do_plant_start_permanent_buffs();g.players[0].trigger_depth=1;
 assert.throws(()=>g.trigger_card(rt(0),0),/normal_attack_actual_card_identity_required/);
 assert.equal(g.players[0].increase_atk,0);assert.equal(e.metadata().remaining[0].power_pending,3);
 assert.deepEqual(g.players[0].can_play,[true,true,true]);scenarios++;
}
{
 const g=fresh(),e=installCurrentNormalAttackV53(root,g,{players:[[5008],[]]},[0,1]);
 g.do_plant_start_permanent_buffs();g.play_card(rt(1000001),0);
 assert.equal(e.metadata().events.length,0);assert.equal(e.metadata().remaining[0].power_pending,3);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios}));
