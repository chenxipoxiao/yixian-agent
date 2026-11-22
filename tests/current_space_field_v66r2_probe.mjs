import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerSpaceField,installSpaceField} from '../tools/current_space_field_v66r2.mjs';
import {installCurrentQiPayment} from '../tools/current_qi_payment_v61.mjs';
import {installCurrentSoundScheduler} from '../tools/current_sound_scheduler_v61.mjs';
import {installChasePayment} from '../tools/current_chase_payment_v61.mjs';
import {installChaseSoundScheduler} from '../tools/current_chase_sound_scheduler_v61.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));registerSpaceField(root,swogi);
const ID='D26035';let scenarios=0;
function fresh(cards=['601011','601011',ID],order=[0,1],scheduler=installCurrentQiPayment){
 const g=new GameState(undefined,undefined,'space-field-boundary');
 for(const p of g.players){p.character='sw1';p.hp=1000;p.max_hp=1000;p.cards=['601011','601011','601011'];p.max_physique=100;}
 g.players[0].cards=[...cards];scheduler(g,(_idx,_id,cost)=>cost);
 const ext=installSpaceField(root,g,swogi,order);g.start_of_game_setup();return {g,p:g.players[0],q:g.players[1],ext};
}
// Every slot of each valid deck length: only last two skip, in the same action.
for(let n=3;n<=8;n++)for(let idx=0;idx<n;idx++){
 const cards=Array(n).fill('601011');cards[idx]=ID;const {g,p,ext}=fresh(cards);p.next_card_index=idx;
 g.sim_turn();const skipped=ext.metadata().events.filter(e=>e.kind==='first_use_skip');
 assert.equal(skipped.length,Number(idx>=n-2));assert.equal(p.can_post_action[idx],true);
 assert.equal(p.chases,0);assert.equal(p.qi,0);assert.equal(ext.metadata().events.filter(e=>e.kind==='empty_body_executed').length,Number(idx<n-2));
 scenarios++;
}
// A skip preserves chain, hp, qi and action budget; the second encounter uses it.
{
 const {g,p,ext}=fresh();p.next_card_index=2;p.cloud_sword_chain_count=4;p.qi=7;
 g.do_skip_next_card();assert.equal(p.next_card_index,0);assert.equal(p.cloud_sword_chain_count,4);assert.equal(p.qi,7);assert.equal(p.can_post_action[2],true);
 p.next_card_index=2;g.do_skip_next_card();assert.equal(p.next_card_index,2);g.sim_turn();
 assert.equal(ext.metadata().events.filter(e=>e.kind==='first_use_skip').length,1);
 assert.equal(ext.metadata().events.filter(e=>e.kind==='empty_body_executed').length,1);scenarios++;
}
// Two adjacent fields skip once each, including reverse traversal and consumed neighbor.
for(const dir of [1,-1]){
 const {g,p,ext}=fresh(['601011','601011',ID,ID]);p.next_card_index=dir===1?2:3;p.card_play_direction=dir;
 g.do_skip_next_card();assert.equal(ext.metadata().events.length,2);assert.equal(p.can_post_action[2],true);assert.equal(p.can_post_action[3],true);scenarios++;
}
{
 const {g,p,ext}=fresh(['601011','601011',ID]);p.can_play[0]=false;p.next_card_index=2;g.do_skip_next_card();assert.equal(p.next_card_index,1);assert.equal(ext.metadata().events.length,1);scenarios++;
}
// External skip bypasses a field without marking it used; its own first use remains.
{
 const {g,p,ext}=fresh();p.next_card_index=2;p.skip_next_card_stacks=1;g.do_skip_next_card();assert.equal(p.can_post_action[2],false);assert.equal(ext.metadata().events.length,0);
 p.next_card_index=2;g.do_skip_next_card();assert.equal(ext.metadata().events.length,1);scenarios++;
}
// Shared skip integration works with all four current action schedulers.
for(const scheduler of [installCurrentQiPayment,installCurrentSoundScheduler,installChasePayment,installChaseSoundScheduler]){
 const {g,p,ext}=fresh(undefined,[0,1],scheduler);p.next_card_index=2;g.sim_turn();
 assert.equal(ext.metadata().events.filter(e=>e.kind==='first_use_skip').length,1);assert.equal(p.can_post_action[0],true);scenarios++;
}
// Explicit history, seats, and deferred resources.
for(const order of [[0,1],[1,0]]){
 const {g,p,ext}=fresh(undefined,order);p.next_card_index=2;p.can_post_action[2]=true;g.do_skip_next_card();assert.equal(p.next_card_index,2);assert.equal(ext.metadata().events.length,0);
 const cultivation=p.cultivation,finished=ext.postBattle(true),unfinished=ext.postBattle(false);
 assert.equal(finished[0].player_index,order[0]);assert.equal(finished[0].applied,false);assert.equal(finished[0].next_battle_allowed,false);
 assert.equal(unfinished[0].status,'combat_not_terminal');assert.equal(p.cultivation,cultivation);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios}));
