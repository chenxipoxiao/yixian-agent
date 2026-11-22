import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerExtremeFootwork,installExtremeFootwork} from '../tools/current_extreme_footwork_v44r2.mjs';
import {installCurrentQiPayment} from '../tools/current_qi_payment_v15.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerExtremeFootwork(root,swogi);let scenarios=0;
function fresh(id='145981'){
 const g=new GameState(undefined,undefined,'footwork-software');
 for(const p of g.players){p.character='sw3';p.hp=500;p.max_hp=500;p.max_physique=100;p.cards=[id,'601011','601011'];p.hand_count=0;}
 g.start_of_game_setup();const m=installExtremeFootwork(root,g,swogi);return {g,p:g.players[0],m};
}
for(let grade=1;grade<=3;grade++){
 const id='14598'+grade,{g,p,m}=fresh(id),calls=[],qi=g.increase_idx_qi.bind(g);
 g.increase_idx_qi=(idx,n)=>{calls.push(n);return qi(idx,n);};
 assert.equal(g.is_crash_fist(id),false);assert.equal(swogi[id].qi_cost,0);
 g.play_card(id,0);assert.equal(p.qi,2*(grade-1));assert.equal(p.agility,10);assert.equal(p.crash_footwork_stacks,1);
 assert.equal(p.can_play[0],false);assert.equal(g.is_crash_fist('601011'),true);
 assert.deepEqual(calls,grade===1?[]:[2*(grade-1)]);assert.equal(m.metadata().events.filter(e=>e.kind==='card_body').length,1);scenarios++;
}
// Distinguish first ordinary play,205-before355, and already-active297.
for(const [prior,twice,double,bodies,leftDouble] of [[0,0,1,1,1],[0,1,1,3,0],[0,1,2,3,1],[0,1,0,2,0],[1,0,1,2,0],[1,1,1,3,0]]){
 const {g,p,m}=fresh('145983');p.crash_footwork_stacks=prior;p.strike_twice_stacks=twice;p.crash_fist_double_stacks=double;
 g.play_card('145983',0);assert.equal(p.qi,4*bodies);assert.equal(p.agility,10*bodies);
 assert.equal(p.crash_fist_double_stacks,leftDouble);assert.equal(p.crash_footwork_stacks,prior+bodies);
 assert.equal(p.strike_twice_stacks,0);assert.equal(m.metadata().events.filter(e=>e.kind==='card_body').length,bodies);scenarios++;
}
// No retroactive pre-card consumption on the first body; next ordinary attack qualifies.
{
 const {g,p}=fresh();p.crash_fist_poke_stacks=5;p.crash_fist_block_stacks=7;
 g.play_card('145981',0);assert.equal(p.def,0);assert.equal(p.crash_fist_block_stacks,7);assert.equal(p.crash_fist_poke_stacks,5);
 g.play_card('601011',1);assert.equal(p.def,7);assert.equal(p.crash_fist_block_stacks,0);assert.equal(p.crash_fist_poke_stacks,0);
 assert.equal(g.players[1].hp,492);scenarios++;
}
// Agility-driven chase respects caps and entangle; no direct chase request.
for(const [cap,entangle,agility,chases,remaining] of [[1,0,0,1,0],[0,0,10,0,0],[1,1,0,0,0]]){
 const {g,p}=fresh();p.max_chases=cap;p.entangle=entangle;g.play_card('145981',0);
 assert.equal(p.this_card_chases,0);g.process_this_card_chases();
 assert.equal(p.agility,agility);assert.equal(p.chases,chases);assert.equal(p.entangle,remaining);scenarios++;
}
for(let grade=1;grade<=3;grade++){
 const {g,p}=fresh('14598'+grade);installCurrentQiPayment(g);p.max_chases=0;
 g.sim_turn();assert.equal(p.next_card_index,1);assert.equal(p.qi,2*(grade-1));assert.equal(p.agility,10);assert.equal(p.can_play[0],false);scenarios++;
}
// Runtime classification cannot inflate the static deck crash count.
{
 const {g,p}=fresh();const before=g.count_crash_fists_in_hand();g.play_card('145981',0);
 assert.equal(g.count_crash_fists_in_hand(),before);assert.equal(before,0);scenarios++;
}
// Nested temporary identity remains fail-closed, not silently approximated.
{
 const {g,p}=fresh();p.trigger_depth=1;p.currently_playing_card_idx=0;
 assert.throws(()=>g.trigger_card('145981',0),/temporary_card_identity/);scenarios++;
}
{
 const {g,m}=fresh();assert.equal(m.metadata(),null);assert.throws(()=>installExtremeFootwork(root,g,swogi),/already/);scenarios++;
}
//329 is tested after205; an extra205 body can exhaust one temporary狂剑 count.
for(const [twice,clearHeart,expectedBodies,leftTwin] of [[0,1,3,0],[1,1,3,1],[1,2,4,0]]){
 const {g,p}=fresh('145983');p.strike_twice_stacks=twice;p.unrestrained_sword_clear_heart_stacks=clearHeart;
 p.unrestrained_sword_twin_dragons_stacks=1;p.crash_fist_double_stacks=1;
 g.play_card('145983',0);assert.equal(p.qi,expectedBodies*4);assert.equal(p.unrestrained_sword_twin_dragons_stacks,leftTwin);
 assert.equal(p.crash_fist_double_stacks,0);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios}));
