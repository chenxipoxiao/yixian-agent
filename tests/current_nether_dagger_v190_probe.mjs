import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installFrenzyMantis} from '../tools/current_card_injury_v190.mjs';
import {registerNetherDagger190,installNetherDagger190} from '../tools/current_nether_dagger_v190.mjs';
import {installCurrentQiPayment} from '../tools/current_qi_payment_v61.mjs';
import {installSeasonDebuff} from '../tools/current_season_debuff_v124.mjs';

const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));
await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerNetherDagger190(root,swogi);
let scenarios=0;
function fresh(grade=1){
 const g=new GameState(undefined,undefined,'nether-dagger-boundaries');
 for(const p of g.players){p.character='he1';p.hp=1000;p.max_hp=1000;p.cards=['601011','601011'];p.max_physique=100;}
 g.players[0].cards[0]='99021'+grade;
 installCurrentQiPayment(g,(_idx,_id,cost)=>cost);
 installFrenzyMantis(root,g,swogi);
 installSeasonDebuff(g);
 const ext=installNetherDagger190(root,g,swogi);
 g.start_of_game_setup();
 return {g,p:g.players[0],q:g.players[1],ext};
}
function body(g){
 const p=g.players[0];p.currently_playing_card_idx=0;p.currently_triggering_card_idx=0;
 p.currently_triggering_card_id=p.cards[0];p.trigger_depth=1;
 swogi[p.cards[0]].card_actions(g);
}
// Exercise actual attack, defense, guard and cleanup in all configured rarities.
for(let grade=1;grade<=3;grade++)for(const guard of ['none','defense','guard','forced']){
 const {g,p,q,ext}=fresh(grade);
 if(guard==='defense'||guard==='forced')q.def=100;
 if(guard==='guard')q.guard_up=1;
 if(guard==='forced'){p.fire_flame_blade_stacks=1;q.max_hp=1100;}
 g.play_card(p.cards[0],0);
 assert.equal(p.internal_injury,1);
 assert.equal(q.hp,guard==='none'?1000-[2,6,10][grade-1]:1000);
 assert.equal(q.internal_injury,guard==='none'||guard==='forced'?3:0);
 assert.equal(g.currentHasCardInjury303(p),false);
 assert.equal(ext.metadata().events[0].injured_card,guard==='none'||guard==='forced');
 assert.equal(p.cloud_sword_chain_count,0);assert.equal(p.unrestrained_sword_count,0);
 assert.equal(p.this_card_chases,0);scenarios++;
}
// Own prevention is applied before the attack; opponent prevention remains ordinary.
{const {g,p,q}=fresh();p.internal_injury=5;p.hexproof=1;body(g);
 assert.equal(p.internal_injury,5);assert.equal(p.hexproof,0);assert.equal(q.internal_injury,7);scenarios++;}
{const {g,p,q}=fresh();q.hexproof=2;body(g);
 assert.equal(p.internal_injury,1);assert.equal(q.internal_injury,1);assert.equal(q.hexproof,0);scenarios++;}
// The shared debuff callback can enlarge the first addition.
{const {g,p,q}=fresh();p.snake_shadow=2;body(g);
 assert.equal(p.internal_injury,3);assert.equal(q.internal_injury,5);scenarios++;}
// An explicitly simulated post-attack callback proves the amount is reread then.
{const {g,p,q}=fresh();const attack=g.atk.bind(g);
 g.atk=n=>{attack(n);g.increase_idx_debuff(0,'internal_injury',8);};body(g);
 assert.equal(p.internal_injury,9);assert.equal(q.internal_injury,11);scenarios++;}
//303 is card lifetime, not the last individual hit's status.
{const {g,p,q,ext}=fresh();g.atk(1);q.def=100;body(g);
 assert.equal(p.this_atk_injured,false);assert.equal(ext.metadata().events[0].injured_card,true);
 assert.equal(q.internal_injury,3);scenarios++;}
// Nested cleanup clears shared303 without restoring the outer card's value.
{const {g,q,ext}=fresh();const attack=g.atk.bind(g);let nested=false;
 g.atk=n=>{attack(n);if(!nested){nested=true;q.def=100;g.trigger_card('601011',1);}};body(g);
 assert.equal(ext.metadata().events[0].injured_card,false);assert.equal(q.internal_injury,0);scenarios++;}
// A prior successful use cannot leak injury state into a blocked next use.
{const {g,p,q,ext}=fresh();g.play_card(p.cards[0],0);q.def=100;g.play_card(p.cards[0],0);
 assert.deepEqual(ext.metadata().events.map(e=>e.injured_card),[true,false]);
 assert.equal(p.internal_injury,2);assert.equal(q.internal_injury,3);scenarios++;}
{const {g}=fresh();assert.throws(()=>g.currentHasCardInjury303({}),/injury_player_identity/);scenarios++;}
console.log(JSON.stringify({passed:true,scenarios,scope:'explicit software boundaries, not independent replay calibration'}));
