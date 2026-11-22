import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerParrot,installParrot,parrotFacts} from '../tools/current_parrot_v78.mjs';
import {installPreparationConsumption} from '../tools/current_preparation_v77.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerParrot(root,swogi);const cards=parrotFacts(root).cards,names=[];
function scenario(name,fn){fn();names.push(name);}
function fresh(id=cards[0].runtime_id,slot=0,order=[0,1]){
 const g=new GameState(undefined,undefined,'parrot-boundaries');
 g.players.forEach(p=>{p.hp=50;p.max_hp=100;p.cards=['601011','601011','601011'];p.hand_count=0;});
 g.players[0].cards[slot]=id;g.players.forEach(p=>p.post_deck_setup());
 const e=installParrot(root,g,swogi,order);return {g,e,p:g.players[0],q:g.players[1]};
}
function play(g,id,slot){g.players[0].currently_playing_card_idx=slot;g.play_card_inner(id,slot);}
for(const c of cards)for(const order of [[0,1],[1,0]])scenario('heal-copy-restore-'+c.raw_id+'-'+order[0],()=>{
 const {g,e,p,q}=fresh(c.runtime_id,1,order);play(g,c.runtime_id,1);
 assert.equal(p.hp,50+c.config.otherParams[0]);assert.equal(q.hp,47);assert.equal(p.cards[1],c.runtime_id);
 assert.equal(p.can_play[1],true);assert.equal(p.trigger_depth,0);assert.equal(e.metadata().events[0].player_index,order[0]);
 assert.equal(e.metadata().events[0].guard_after,0);play(g,c.runtime_id,1);assert.equal(q.hp,44);
});
scenario('loop-guard-before-nested-heal',()=>{
 const {g,e,p,q}=fresh(cards[1].runtime_id);q.cards[0]=cards[2].runtime_id;play(g,cards[1].runtime_id,0);
 assert.equal(p.hp,56);assert.equal(q.hp,50);assert.equal(p.cards[0],cards[1].runtime_id);
 assert.equal(e.metadata().events.filter(x=>x.kind==='copy_loop_blocked').length,1);assert.equal(e.metadata().events[0].guard_after,0);
});
scenario('read-live-target-each-time',()=>{
 const {g,e,p,q}=fresh();play(g,cards[0].runtime_id,0);q.cards[0]=cards[2].runtime_id;play(g,cards[0].runtime_id,0);
 assert.equal(q.hp,47);assert.equal(p.hp,54);assert.deepEqual(e.metadata().events.filter(e=>e.kind==='parrot_body').map(e=>e.copy_target),['601011',cards[2].runtime_id]);
});
scenario('no-opponent-grid-heals-without-copy',()=>{
 const {g,e,p,q}=fresh(cards[0].runtime_id,2);q.cards=['601011'];play(g,cards[0].runtime_id,2);
 assert.equal(p.hp,52);assert.equal(q.hp,50);assert.equal(e.metadata().events[0].copy_target,null);assert.equal(e.metadata().events[0].guard_after,0);
});
scenario('unsupported-live-target-remains-unresolved',()=>{
 const {g,p,q}=fresh();q.cards[0]='111011';assert.throws(()=>play(g,cards[0].runtime_id,0),/copy_target_not_admitted/);
 assert.equal(p.cards[0],cards[0].runtime_id);
});
scenario('temporary-card-really-uses-same-physical-grid',()=>{
 const {g,p}=fresh(cards[0].runtime_id,2),body=g.just_do_the_card_and_nothing_else.bind(g);let observed;
 g.just_do_the_card_and_nothing_else=function(c){if(p.trigger_depth===2)observed=[p.cards[2],p.currently_triggering_card_idx,p.currently_playing_card_idx];return body(c);};
 play(g,cards[0].runtime_id,2);assert.deepEqual(observed,['601011',2,2]);assert.equal(p.cards[2],cards[0].runtime_id);
});
scenario('guard-up-and-negative-final-hp-preserved',()=>{
 const {g,p,q}=fresh();q.guard_up=1;play(g,cards[0].runtime_id,0);assert.equal(q.hp,50);assert.equal(q.guard_up,0);
 q.hp=1;play(g,cards[0].runtime_id,0);assert.equal(q.hp,-2);
});
scenario('copy-does-not-double-consume-663',()=>{
 const {g,p}=fresh();installPreparationConsumption(root,g,swogi,{players:[[{strategy_id:13015,slot:1}],[]]});
 p.consume_next_card_played_stacks=2;play(g,cards[0].runtime_id,0);
 assert.equal(p.consume_next_card_played_stacks,1);assert.equal(p.can_play[0],false);assert.equal(p.cards[0],cards[0].runtime_id);
});
scenario('copied-normal-before-after-hooks-run',()=>{
 const {g,p,q}=fresh();p.sword_intent=5;play(g,cards[0].runtime_id,0);assert.equal(q.hp,42);assert.equal(p.sword_intent,0);
});
console.log(JSON.stringify({passed:true,scenarios:names.length,names}));
