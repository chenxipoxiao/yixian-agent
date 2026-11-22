import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerFrenzyMantis,installFrenzyMantis} from '../tools/current_frenzy_mantis_v69.mjs';
import {installCurrentQiPayment} from '../tools/current_qi_payment_v61.mjs';
import {installCurrentSoundScheduler} from '../tools/current_sound_scheduler_v61.mjs';
import {installChasePayment} from '../tools/current_chase_payment_v61.mjs';
import {installChaseSoundScheduler} from '../tools/current_chase_sound_scheduler_v61.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));registerFrenzyMantis(root,swogi);
let scenarios=0;
function fresh(id,scheduler=installCurrentQiPayment,order=[0,1]){
 const g=new GameState(undefined,undefined,'frenzy-mantis-boundaries');
 for(const p of g.players){p.character='he1';p.hp=1000;p.max_hp=1000;p.cards=['601011','601011','601011'];p.max_physique=100;}
 g.players[0].cards[0]=id;scheduler(g,(_idx,_id,cost)=>cost);const ext=installFrenzyMantis(root,g,swogi,order);
 g.start_of_game_setup();return {g,p:g.players[0],q:g.players[1],ext};
}
function body(g){const p=g.players[0];p.currently_playing_card_idx=0;p.currently_triggering_card_idx=0;p.currently_triggering_card_id=p.cards[0];p.trigger_depth=1;swogi[p.cards[0]].card_actions(g);}
// Numeric levels, injury predicate and classification through actual cleanup.
for(let grade=1;grade<=3;grade++)for(const guard of ['none','defense','guard','forced']){
 const {g,p,q,ext}=fresh('76900'+grade);const atk=[4,10,16][grade-1];
 if(guard==='defense'||guard==='forced')q.def=100;
 if(guard==='guard')q.guard_up=1;
 if(guard==='forced'){p.fire_flame_blade_stacks=1;q.max_hp=1100;}
 g.play_card(p.cards[0],0);const injured=guard==='none'||guard==='forced';
 assert.equal(q.wound,injured?1:0);assert.equal(p.this_card_chases,injured?1:0);
 assert.equal(q.hp,guard==='none'?1000-atk:1000);
 assert.equal(p.cloud_sword_chain_count,1);assert.equal(p.unrestrained_sword_count,1);
 assert.equal(ext.metadata().events[0].injured_card,injured);scenarios++;
}
// Prior wound participates in this attack; the new layer arrives afterwards.
{const {g,q}=fresh('769002');q.wound=2;body(g);assert.equal(q.hp,988);assert.equal(q.wound,3);scenarios++;}
// Per-hit reset is distinct from per-card303, including a later noninjuring hit.
{const {g,p,q,ext}=fresh('769001');const attack=g.atk.bind(g);g.atk=n=>{attack(n);q.def=100;attack(1);};body(g);
 assert.equal(p.this_atk_injured,false);assert.equal(ext.metadata().events[0].injured_card,true);assert.equal(q.wound,1);scenarios++;}
// Nested OnAfterExecuted clears shared303; it is not restored to the outer card.
{const {g,q,ext}=fresh('769001');const attack=g.atk.bind(g);let nested=false;g.atk=n=>{attack(n);if(!nested){nested=true;q.def=100;g.trigger_card('601011',1);}};
 body(g);assert.equal(ext.metadata().events[0].injured_card,false);assert.equal(q.wound,0);scenarios++;}
// Cleanup prevents a previous injured card from leaking into the next use.
{const {g,p,q,ext}=fresh('769001');g.play_card(p.cards[0],0);q.def=100;g.play_card(p.cards[0],0);
 assert.deepEqual(ext.metadata().events.map(e=>e.injured_card),[true,false]);assert.equal(q.wound,1);scenarios++;}
// Mantis attack gain is between pairs; first-use post-strike occurs before eligibility.
for(let grade=1;grade<=3;grade++)for(const post of ['first','used','preemptive']){
 const {g,p,q,ext}=fresh('76901'+grade);const gain=grade+1;
 p.can_post_action[0]=post==='used';p.preemptive_strike_stacks=post==='preemptive'?1:0;
 p.p2_post_strike_stacks=1;p.hp=990;body(g);
 assert.equal(p.increase_atk,gain);assert.equal(q.hp,1000-6-(post==='first'?0:2*(3+gain)));
 assert.equal(p.def,post==='used'?0:2);assert.equal(p.max_hp,post==='used'?1000:1002);assert.equal(p.hp,post==='used'?990:992);
 assert.equal(ext.metadata().events[0].post_action,post!=='first');scenarios++;
}
// Each first-pair hit has its own guard check; attack gain still occurs.
for(const post of [false,true]){const {g,p,q}=fresh('769013');p.can_post_action[0]=post;q.guard_up=2;body(g);
 assert.equal(q.hp,post?986:1000);assert.equal(q.guard_up,0);assert.equal(p.increase_atk,4);scenarios++;}
// Two physical uses update hadUsed, unlike a temporary invocation.
{const {g,p,q}=fresh('769011');g.play_card(p.cards[0],0);g.play_card(p.cards[0],0);assert.equal(q.hp,970);assert.equal(p.played_post_action_count,2);scenarios++;}
{const {g,p}=fresh('769011');p.currently_playing_card_idx=1;p.currently_triggering_card_idx=0;p.currently_triggering_card_id=p.cards[0];p.trigger_depth=2;
 assert.throws(()=>swogi[p.cards[0]].card_actions(g),/temporary_post_action_identity/);scenarios++;}
// Chase requests pass through the four existing scheduler variants.
for(const scheduler of [installCurrentQiPayment,installCurrentSoundScheduler,installChasePayment,installChaseSoundScheduler]){
 const {g,p,ext}=fresh('769001',scheduler);p.entangle=1;g.sim_turn();assert.equal(p.entangle,0);assert.equal(p.can_post_action[1],false);assert.equal(ext.metadata().events.length,1);scenarios++;
}
{const {g,ext}=fresh('769001',installCurrentQiPayment,[1,0]);body(g);assert.equal(ext.metadata().events[0].player_index,1);scenarios++;}
console.log(JSON.stringify({passed:true,scenarios}));
