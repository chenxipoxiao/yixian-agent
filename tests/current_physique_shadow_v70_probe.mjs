import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerPhysiqueShadow,installPhysiqueShadow} from '../tools/current_physique_shadow_v70.mjs';
import {installCurrentDelayedEffects} from '../tools/current_delayed_effects_v70.mjs';
import {installCurrentQiPayment} from '../tools/current_qi_payment_v61.mjs';
import {installCurrentSoundScheduler} from '../tools/current_sound_scheduler_v61.mjs';
import {installChasePayment} from '../tools/current_chase_payment_v61.mjs';
import {installChaseSoundScheduler} from '../tools/current_chase_sound_scheduler_v61.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));registerPhysiqueShadow(root,swogi);
let scenarios=0;
function fresh(id,scheduler=installCurrentQiPayment){
 const g=new GameState(undefined,undefined,'physique-shadow-boundaries');
 for(const p of g.players){p.character='dx1';p.hp=900;p.max_hp=1000;p.cards=['601011','601011','601011'];p.max_physique=100;}
 g.players[0].cards[0]=id;scheduler(g,(_idx,_id,cost)=>cost);installCurrentDelayedEffects(root,g,swogi);
 const ext=installPhysiqueShadow(root,g,swogi,[0,1]);g.start_of_game_setup();return {g,p:g.players[0],q:g.players[1],ext};
}
function body(g,slot=0){const p=g.players[0];p.currently_playing_card_idx=slot;p.currently_triggering_card_idx=slot;p.currently_triggering_card_id=p.cards[slot];p.trigger_depth=1;swogi[p.cards[slot]].card_actions(g);}
// Three grades; existing physique overflow heals only the gained excess.
for(let grade=1;grade<=3;grade++)for(const overflow of [false,true]){
 const {g,p}=fresh('77000'+grade);const gain=grade+1;p.physique=9;p.max_physique=overflow?10:100;
 const order=[];for(const k of ['increase_idx_qi','increase_idx_physique']){const old=g[k].bind(g);g[k]=(...a)=>{order.push(k);return old(...a);};}
 body(g);assert.equal(p.qi,2);assert.equal(p.physique,9+gain);assert.equal(p.max_hp,1000+gain);
 assert.equal(p.hp,900+(overflow?gain-1:0));assert.equal(p.increase_atk,gain);assert.deepEqual(order,['increase_idx_qi','increase_idx_physique']);scenarios++;
}
// Both sides' internal injury, after physique and heal; count post-gain physique.
for(let grade=1;grade<=5;grade++)for(const protect of [false,true]){
 const {g,p,q,ext}=fresh('77001'+grade);p.physique=21;if(protect)q.hexproof=1;
 const gain=[2,2,3,3,3][grade-1],heal=[4,6,7,4,4][grade-1];body(g);
 const inj=grade<=3?2:Math.floor((21+gain)/(grade===4?12:10));
 assert.equal(p.physique,21+gain);assert.equal(p.hp,900+heal);assert.equal(p.internal_injury,inj);
 assert.equal(q.internal_injury,protect?Math.max(0,inj-1):inj);assert.equal(ext.metadata().events[0].internal_injury,inj);scenarios++;
}
{const {g,p,q}=fresh('770015');body(g);assert.equal(p.internal_injury,0);assert.equal(q.internal_injury,0);scenarios++;}
// Low tiers add exactly one base attack for any positive debuff, not per layer.
for(let grade=1;grade<=3;grade++)for(const debuff of [0,1,7]){
 const {g,p,q}=fresh('77002'+grade);p.indigestion=debuff;body(g);assert.equal(q.hp,900-2*(grade+4+(debuff>0?1:0)));assert.equal(p.hp,900);scenarios++;
}
for(let grade=4;grade<=5;grade++){const {g,p,q}=fresh('77002'+grade);p.indigestion=8;body(g);assert.equal(q.hp,900-2*(grade===4?1:3));assert.equal(p.agility,grade===4?10:12);scenarios++;}
// Actual scheduler charges exactly four HP. Direct temporary body does not repay.
for(const scheduler of [installCurrentQiPayment,installCurrentSoundScheduler,installChasePayment,installChaseSoundScheduler]){
 const {g,p}=fresh('770021',scheduler);g.sim_turn();assert.equal(p.hp,896);assert.equal(p.hp_cost_card_count,1);scenarios++;
}
// Physical circular neighbor, direction reversal and inactive grid are respected.
for(const direction of [1,-1])for(const slot of [0,2])for(const grade of [4,5]){
 const {g,p,q,ext}=fresh('601011');const next=(slot+direction+3)%3;p.cards[next]='77002'+grade;
 p.card_play_direction=direction;p.can_play[next]=false;p.indigestion=5;p.internal_injury=-3;
 g.play_card(p.cards[slot],slot);assert.equal(q.hp,895);const e=ext.metadata().events.find(e=>e.kind==='shadow_neighbor_attack');assert.equal(e.amount,2);assert.equal(e.next_slot,next);scenarios++;
}
// Adjacent passive does not leak to any after-card attack, even if a caller omits is_extra.
{const {g,p,q,ext}=fresh('770001');p.cards[1]='770024';p.indigestion=6;p.stance_of_fierce_attack_stacks=1;
 g.do_god_luck_approach=function(){this.atk(2);};g.play_card(p.cards[0],0);
 assert.equal(q.hp,891);assert.equal(ext.metadata().events.filter(e=>e.kind==='shadow_neighbor_attack').length,0);scenarios++;}
// Nested body uses its own physical next grid; its cleanup does not restore382.
{const {g,p,q,ext}=fresh('601011');p.cards=['601011','770024','601011'];p.indigestion=4;
 const old=g.just_do_the_card_and_nothing_else.bind(g);let nested=false;g.just_do_the_card_and_nothing_else=function(c){if(!nested){nested=true;this.trigger_card('601011',2);}return old(c);};
 g.play_card('601011',0);assert.equal(q.hp,892);assert.equal(ext.metadata().events.filter(e=>e.kind==='shadow_neighbor_attack').length,1);scenarios++;}
// No current card outside a trigger means no adjacency bonus.
{const {g,p,q,ext}=fresh('601011');p.cards[1]='770024';p.indigestion=8;g.atk(3);assert.equal(q.hp,897);assert.equal(ext.metadata(),null);scenarios++;}
console.log(JSON.stringify({passed:true,scenarios}));
