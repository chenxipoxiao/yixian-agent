import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installCurrentEngravings} from '../tools/current_engraving_effects_v19.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
let checked=0;
function fresh(effects,fields={},enemy={}) {
 const g=new GameState(undefined,undefined,'boundary-v19');
 Object.assign(g.players[0],{cards:['601011','601011','601011'],hp:50,max_hp:100,qi:0,def:0},fields);
 Object.assign(g.players[1],{cards:['601011'],hp:1000,max_hp:1000,qi:0,def:0},enemy);
 const ledger=installCurrentEngravings(root,g,{players:[effects,[]]},[0,1]);
 return [g,ledger];
}
// A defense-only body can arm poison, but ordinary damage must not spend it.
for(const enemy of [{},{def:100},{guard_up:1}]) {
 const [g,l]=fresh([{strategy_id:13001,slot:0}],{},enemy);
 g.just_do_the_card_and_nothing_else=()=>g.increase_idx_def(0,3);
 g.play_card_inner('601011',0);assert.equal(l.pendingFor(g.players[0])[544],3);
 g.players[0].currently_triggering_card_id='601011';
 g.players[0].currently_triggering_card_idx=0;g.players[0].currently_playing_card_idx=0;
 g.deal_damage(2);assert.equal(l.pendingFor(g.players[0])[544],3);
 g.atk(2);assert.equal(g.players[1].internal_injury,3);assert.equal(l.pendingFor(g.players[0])[544],0);
 g.atk(2);assert.equal(g.players[1].internal_injury,3);checked++;
}
// Poison applies after return damage and existing curse effects, including a
// lethal hit; it does not need the attack to cause positive HP damage.
{
 const [g]=fresh([{strategy_id:13001,slot:0}],{soul_wound_curse_formation_stacks:1},{repel_citta_dharma_stacks:4});
 const observed=[],add=g.increase_idx_debuff.bind(g);
 g.increase_idx_debuff=(idx,key,n)=>{if(key==='internal_injury')observed.push([n,g.players[0].hp]);return add(idx,key,n);};
 g.play_card_inner('601011',0);assert.deepEqual(observed,[[1,46],[3,46]]);checked++;
}
// Heal uses cumulative loss (including costs), not current missing HP. Integer
// rounding and max-HP-before-heal order are important at a nearly full bar.
for(const lost of [0,4,5,9,19,100]) {
 const [g]=fresh([{strategy_id:13004,slot:0}],{hp:99,max_hp:100,hp_lost:lost});
 g.play_card_inner('601011',0);const amount=Math.trunc(lost/5);
 assert.equal(g.players[0].max_hp,100+amount);assert.equal(g.players[0].hp,99+amount);checked++;
}
{
 const [g]=fresh([{strategy_id:13004,slot:0}],{guard_up:1});
 g.reduce_idx_hp(0,12);g.reduce_idx_hp(0,10,true);g.increase_idx_hp(0,10);
 assert.equal(g.players[0].hp_lost,10);g.play_card_inner('601011',0);
 assert.equal(g.players[0].hp,52);assert.equal(g.players[0].max_hp,102);checked++;
}
for(const id of [13004,13013,13019]) {
 const [g]=fresh([{strategy_id:id,slot:0}],{hp:-1,hp_lost:50});
 g.play_card_inner('601011',0);assert.equal(g.players[0].hp,-1);checked++;
}
// Temporary guard is consumed before permanent guard. Unspent temporary
// charges expire at the owner's next turn, never at the opponent's turn.
for(const hits of [0,1,2,3]) {
 const [g,l]=fresh([{strategy_id:13008,slot:0}],{guard_up:1});const owner=g.players[0];
 g.play_card_inner('601011',0);assert.equal(owner.guard_up,3);
 for(let i=0;i<hits;i++)g.reduce_idx_hp(0,7);
 assert.equal(owner.hp,50);assert.equal(l.pendingFor(owner)[745],Math.max(0,2-hits));
 g.players.reverse();g.do_def_decay();assert.equal(owner.guard_up,3-hits);
 g.players.reverse();g.do_def_decay();assert.equal(owner.guard_up,hits<3?1:0);checked++;
}
{
 const [g,l]=fresh([{strategy_id:13008,slot:0}]);g.play_card_inner('601011',0);
 g.reduce_idx_hp(0,3,true);g.reduce_idx_hp(0,4,false,true);g.reduce_idx_hp(0,0);
 assert.equal(g.players[0].guard_up,2);assert.equal(l.pendingFor(g.players[0])[745],2);
 g.do_def_decay();assert.equal(g.players[0].guard_up,0);assert.equal(g.players[0].hp,43);checked++;
}
// Clearing guard by a separate effect does not consume the 745 counter.
{
 const [g,l]=fresh([{strategy_id:13008,slot:0}]);g.play_card_inner('601011',0);
 g.reduce_idx_x_by_c(0,'guard_up',2);g.add_c_of_x(3,'guard_up');
 assert.equal(l.pendingFor(g.players[0])[745],2);g.do_def_decay();assert.equal(g.players[0].guard_up,1);checked++;
}
// Liangyi reads resulting hexagram, and a healing-prohibition still permits
// its separate maximum-HP gain.
for(const blocked of [0,1]) {
 const [g]=fresh([{strategy_id:13013,slot:0}],{hexagram:4,prevent_gain_hp_stacks:blocked});
 g.play_card_inner('601011',0);assert.equal(g.players[0].hexagram,5);
 assert.equal(g.players[0].max_hp,105);assert.equal(g.players[0].hp,blocked?50:55);checked++;
}
// All eight current negative counters count, including indigestion; count
// layers, not types. Nonpositive counters are excluded by the client list.
{
 const [g]=fresh([{strategy_id:13019,slot:0}],{internal_injury:2,weaken:3,flaw:4,decrease_atk:5,entangle:6,wound:7,styx:8,indigestion:9});
 let amount;const heal=g.increase_idx_hp.bind(g);g.increase_idx_hp=(idx,n)=>{amount=n;return heal(idx,n);};
 g.play_card_inner('601011',0);assert.equal(amount,50);assert.equal(g.players[0].hp,91);checked++;
}
{
 const [g]=fresh([{strategy_id:13019,slot:0}],{weaken:-2,flaw:0,internal_injury:3});
 g.play_card_inner('601011',0);assert.equal(g.players[0].hp,59);checked++;
}
// The seven effects share one client-ordered first-use ledger. Nested
// temporary executions and a double play never consume/repeat it early.
{
 const ids=[13001,13004,13008,13009,13013,13016,13019];
 const [g,l]=fresh(ids.map(strategy_id=>({strategy_id,slot:1})),{hp_lost:20,strike_twice_stacks:1});
 g.players[0].trigger_depth=1;g.trigger_card('601011',1);g.players[0].trigger_depth=0;
 assert.ok(l.forPlayer(g.players[0]).every(e=>!e.used));
 g.play_card('601011',1);assert.ok(l.forPlayer(g.players[0]).every(e=>e.used));
 assert.equal(g.players[0].max_hp,105);assert.equal(g.players[0].guard_up,2);
 assert.equal(g.players[1].internal_injury,3);checked++;
}
for(const invalid of [null,{players:[[],[]],extra:1},{players:[[{strategy_id:13007,slot:0}],[]]},
 {players:[[{strategy_id:13004,slot:-1}],[]]},{players:[[{strategy_id:13008,slot:8}],[]]},
 {players:[[{strategy_id:13013,slot:0},{strategy_id:13013,slot:0}],[]]},
 {players:[[{strategy_id:13019,slot:0,used:true}],[]]}]) {
 assert.throws(()=>installCurrentEngravings(root,new GameState(),invalid,[0,1]));checked++;
}
console.log(JSON.stringify({passed:true,checked}));
