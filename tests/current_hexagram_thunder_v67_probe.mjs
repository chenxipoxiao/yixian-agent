import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerHexagramThunder,installHexagramThunder} from '../tools/current_hexagram_thunder_v67.mjs';
import {installCurrentQiPayment} from '../tools/current_qi_payment_v61.mjs';
import {installCurrentSoundScheduler} from '../tools/current_sound_scheduler_v61.mjs';
import {installChasePayment} from '../tools/current_chase_payment_v61.mjs';
import {installChaseSoundScheduler} from '../tools/current_chase_sound_scheduler_v61.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));registerHexagramThunder(root,swogi);
let scenarios=0;
function fresh(cards,order=[0,1],scheduler=installCurrentQiPayment){
 const g=new GameState(undefined,undefined,'hexagram-thunder-boundaries');
 for(const p of g.players){p.character='he1';p.hp=1000;p.max_hp=1000;p.cards=['601011','601011','601011'];p.max_physique=100;}
 g.players[0].cards=[...cards];scheduler(g,(_idx,_id,cost)=>cost);
 const ext=installHexagramThunder(root,g,swogi,order);g.start_of_game_setup();return {g,p:g.players[0],q:g.players[1],ext};
}
function body(g,slot){const p=g.players[0];p.currently_playing_card_idx=slot;p.currently_triggering_card_idx=slot;p.currently_triggering_card_id=p.cards[slot];p.trigger_depth=1;swogi[p.cards[slot]].card_actions(g);}
// Per-level formation values, one non-attack damage per positive gain, no zero/loss trigger.
for(let level=1;level<=3;level++){
 const {g,p,q,ext}=fresh(['76700'+level,'601011','601011']);body(g,0);
 assert.equal(p.hexagram_formacide_stacks,level);assert.equal(p.can_play[0],false);
 q.def=2;g.increase_idx_hexagram(0,4);assert.equal(q.def,0);assert.equal(q.hp,1000-(4*level-2));
 const hp=q.hp;g.increase_idx_hexagram(0,0);g.reduce_idx_hexagram(0,3);assert.equal(q.hp,hp);assert.equal(p.hexagram,1);
 assert.equal(ext.metadata().events.filter(e=>e.kind==='hexagram_gain').length,1);scenarios++;
}
// Existing normal and extreme formations stack; attack boosts do not affect non-attack damage.
{
 const {g,p,q}=fresh(['767001','601011','601011']);p.hexagram_formacide_stacks=5;p.increase_atk=9;body(g,0);g.increase_idx_hexagram(0,2);assert.equal(q.hp,988);scenarios++;
}
// Astrological star gain precedes damage; dream healing/defence follow it.
{
 const {g,p}=fresh(['767002','601011','601011']);body(g,0);p.astrology_stacks=1;p.dream_yin_yang_formation_hp_stacks=2;p.dream_yin_yang_formation_def_stacks=3;
 const calls=[];g.increase_idx_star_power=()=>calls.push('star');g.deal_damage_inner=(n)=>calls.push('damage:'+n);g.increase_idx_hp=()=>calls.push('hp');g.increase_idx_def=()=>calls.push('def');
 g.increase_idx_hexagram(0,2);assert.deepEqual(calls,['star','damage:4','hp','def']);scenarios++;
}
// Wind: physical wraparound, both directions, consumed neighbors still count.
for(const dir of [1,-1])for(const neighbor of [1,3])for(const inactive of [false,true]){
 const cards=['767012','601011','601011','601011'];cards[neighbor]='767021';const {g,p,q,ext}=fresh(cards);p.card_play_direction=dir;p.can_play[neighbor]=!inactive;p.hexagram=2;
 g.rng=()=>{throw new Error('guaranteed branch used rng');};body(g,0);
 assert.equal(q.hp,984);assert.equal(p.qi,1);assert.equal(p.hexagram,0);assert.equal(p.triggered_hexagram_count,2);assert.equal(p.chases,1);
 assert.equal(ext.metadata().events.at(-1).as_attack,true);scenarios++;
}
// A distant thunder does not turn defense into attack; magnitude and chance consume separately.
for(let grade=1;grade<=3;grade++)for(const hex of [0,1,2]){
 const {g,p,q,ext}=fresh(['76701'+grade,'601011','767021','601011']);p.hexagram=hex;const values=[0.5,0.99];let randomCalls=0;g.rng=()=>values[randomCalls++];body(g,0);
 const hi=[11,16,21][grade-1],amount=hex?hi:1+Math.floor(0.5*hi);
 assert.equal(p.def,amount);assert.equal(q.hp,1000);assert.equal(p.chases,hex===2?1:0);assert.equal(randomCalls,2-Math.min(hex,2));
 assert.equal(ext.metadata().events.at(-1).as_attack,false);scenarios++;
}
// Qi gain happens before magnitude, so a qi-to-hexagram effect can force that magnitude.
{
 const {g,p}=fresh(['767011','601011','601011']);p.spiritual_divination_stacks=1;g.rng=()=>0.8;body(g,0);assert.equal(p.def,11);assert.equal(p.hexagram,0);assert.equal(p.triggered_hexagram_count,1);assert.equal(p.chases,0);scenarios++;
}
// Lotus levels and the 1% boundary; each random operation has its own hexagram use.
for(let grade=1;grade<=3;grade++)for(const proc of [0.0099,0.01]){
 const {g,p,q}=fresh(['76702'+grade,'601011','601011']);const seq=[0,proc];g.rng=()=>seq.shift();body(g,0);
 assert.equal(q.hp,1000-1-(proc<0.01?[5,7,9][grade-1]:0));assert.equal(p.hexproof,2);assert.equal(seq.length,0);scenarios++;
}
for(const hex of [1,2]){
 const {g,p,q}=fresh(['767023','601011','601011']);p.hexagram=hex;let calls=0;
 g.rng=()=>{calls++;return 0.5;};body(g,0);assert.equal(q.hp,1000-15-(hex===2?9:0));assert.equal(p.hexproof,2);assert.equal(calls,hex===2?0:1);scenarios++;
}
// Shared chase scheduler enforces entangle and chase limits after the body request.
for(const scheduler of [installCurrentQiPayment,installCurrentSoundScheduler,installChasePayment,installChaseSoundScheduler]){
 const {g,p,ext}=fresh(['767011','601011','601011'],[0,1],scheduler);p.hexagram=2;p.entangle=1;g.sim_turn();
 assert.equal(p.entangle,0);assert.equal(p.can_post_action[1],false);assert.equal(ext.metadata().events.filter(e=>e.kind==='card_body').length,1);scenarios++;
}
// Stable original seats and malformed physical neighbors stop rather than guessing.
{
 const {g,p,ext}=fresh(['767011','601011','601011'],[1,0]);p.hexagram=2;body(g,0);assert.equal(ext.metadata().events[0].player_index,1);
 p.cards[1]='unknown-runtime';assert.throws(()=>body(g,0),/unknown_neighbor_identity/);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios}));
