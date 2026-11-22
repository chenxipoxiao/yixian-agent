import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installCurrentEngravings} from '../tools/current_engraving_effects_v20.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
let checked=0;
function fresh(effects=[{strategy_id:13006,slot:0}],configure=()=>{}) {
 const g=new GameState(undefined,undefined,'boundary-v20');
 for(const p of g.players)Object.assign(p,{cards:['601011','601011','601011'],hp:1000,max_hp:1000,qi:0,def:0});
 configure(g);
 const ledger=installCurrentEngravings(root,g,{players:[effects,[]]},[0,1]);
 return [g,ledger];
}
// A six-point EXTRA ATTACK after the chosen card, not an extra action.
{
 const [g,l]=fresh();g.play_card_inner('601011',0);
 assert.equal(g.players[1].hp,991);assert.equal(g.players[0].this_card_chases,0);
 assert.equal(l.pendingFor(g.players[0])[794],1);assert.equal(g.players[0].played_card_count,1);
 g.play_card_inner('601011',0);assert.equal(g.players[1].hp,988);checked++;
}
// The usage counter remains spent even if a replacement resets hadUsed.
{
 const [g,l]=fresh();g.play_card_inner('601011',0);g.players[0].can_post_action[0]=false;
 g.play_card_inner('601011',0);assert.equal(g.players[1].hp,988);assert.equal(l.pendingFor(g.players[0])[794],1);checked++;
}
for(const slot of [1,7]) {
 const [g,l]=fresh([{strategy_id:13006,slot}]);g.play_card_inner('601011',0);
 assert.equal(g.players[1].hp,997);assert.equal(l.pendingFor(g.players[0])[794],0);
 if(slot===1){g.play_card_inner('601011',1);assert.equal(g.players[1].hp,988);}
 checked++;
}
{
 const [g,l]=fresh();g.players[0].can_post_action[0]=true;g.play_card_inner('601011',0);
 assert.equal(g.players[1].hp,997);assert.equal(l.pendingFor(g.players[0])[794],0);checked++;
}
// Native double execution consumes the engraving only on its first play.
{
 const [g,l]=fresh();g.players[0].strike_twice_stacks=1;g.play_card('601011',0);
 assert.equal(g.players[1].hp,988);assert.equal(l.pendingFor(g.players[0])[794],1);checked++;
}
// Placement is after earlier extra attacks and before Crash Fist Shocked,
// with the once-only guard committed before the attack can cause reactions.
{
 const order=[];let l;
 const [g,ledger]=fresh(undefined,g=>{
  g.do_m_shifting_stars=()=>order.push('previous');
  g.do_crash_fist_shocked=()=>order.push('shocked');
 });l=ledger;
 const atk=g.atk.bind(g);g.atk=(n,extra=false)=>{
  order.push([n,extra,l.pendingFor(g.players[0])[794]]);return atk(n,extra);
 };
 g.play_card_inner('601011',0);
 assert.deepEqual(order,[[3,false,0],'previous',[6,true,1],'shocked']);checked++;
}
// A non-attacking card also triggers; poison is consumed by this extra
// attack. Guard/defense can block damage but cannot undo the once flag.
for(const enemy of [{},{guard_up:1},{def:100}]) {
 const [g,l]=fresh([{strategy_id:13001,slot:0},{strategy_id:13006,slot:0}],g=>{
  Object.assign(g.players[1],enemy);g.just_do_the_card_and_nothing_else=()=>g.increase_idx_def(0,3);
 });
 g.play_card_inner('601011',0);assert.equal(g.players[1].internal_injury,3);
 assert.equal(l.pendingFor(g.players[0])[544],0);assert.equal(l.pendingFor(g.players[0])[794],1);
 assert.equal(g.players[1].hp,enemy.guard_up||enemy.def?1000:994);checked++;
}
// Native sword-intent attack/cleanup participates, no independently invented
// raw-HP subtraction. Reflect damage runs before returning to the scheduler.
{
 const [g]=fresh(undefined,g=>{
  g.players[0].sword_intent=4;g.players[1].repel_citta_dharma_stacks=2;
  g.just_do_the_card_and_nothing_else=()=>{};
 });g.play_card_inner('601011',0);
 assert.equal(g.players[1].hp,990);assert.equal(g.players[0].hp,998);assert.equal(g.players[0].sword_intent,0);checked++;
}
// Effects remain owned by the player when active seats reverse.
{
 const [g,l]=fresh();const owner=g.players[0];g.players.reverse();g.play_card_inner('601011',0);
 assert.equal(owner.hp,997);assert.equal(l.pendingFor(owner)[794],0);
 g.players.reverse();g.play_card_inner('601011',0);assert.equal(g.players[1].hp,991);checked++;
}
// Client temp-card jump reaches13006. Unknown actual CardItem identity
// therefore stops before executing the nested body, never silently skips it.
for(const slot of [0,1]) {
 const [g,l]=fresh([{strategy_id:13006,slot}]);let bodies=0;
 g.players[0].trigger_depth=1;g.just_do_the_card_and_nothing_else=()=>bodies++;
 assert.throws(()=>g.trigger_card('601011',0),/engraving_temporary_card_identity_unresolved/);
 assert.equal(bodies,0);assert.equal(l.pendingFor(g.players[0])[794],0);checked++;
}
// Once794 is nonzero, the client branch cannot fire on any temporary card.
{
 const [g,l]=fresh();g.play_card_inner('601011',0);g.players[0].trigger_depth=1;
 g.trigger_card('601011',0);assert.equal(l.pendingFor(g.players[0])[794],1);assert.equal(g.players[1].hp,988);checked++;
}
// 13006 must never be prematurely spent by the pre-card engraving loop.
{
 const ids=[13001,13004,13006,13008,13009,13013,13016,13019];const [g,l]=fresh(ids.map(strategy_id=>({strategy_id,slot:0})));
 g.just_do_the_card_and_nothing_else=()=>assert.equal(l.pendingFor(g.players[0])[794],0);
 g.play_card_inner('601011',0);assert.ok(l.forPlayer(g.players[0]).every(e=>e.used));checked++;
}
for(const input of [
 {players:[[{strategy_id:13006,slot:0,used:true}],[]]},
 {players:[[{strategy_id:13006,slot:0}],[]],794:1},
 {players:[[{strategy_id:13006,slot:null}],[]]},
 {players:[[{strategy_id:13006,slot:0},{strategy_id:13006,slot:1}],[]]},
]){assert.throws(()=>installCurrentEngravings(root,new GameState(),input,[0,1]));checked++;}
console.log(JSON.stringify({passed:true,checked}));
