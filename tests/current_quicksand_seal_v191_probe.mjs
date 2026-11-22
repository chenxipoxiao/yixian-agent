import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerQuicksandSeal191,installQuicksandSeal191} from '../tools/current_quicksand_seal_v191.mjs';
import {installSeasonPrimitives} from '../tools/current_season_primitives_v163.mjs';
import {installCurrentQiPayment} from '../tools/current_qi_payment_v124.mjs';
import {installCurrentSoundScheduler} from '../tools/current_sound_scheduler_v124.mjs';
import {installChasePayment} from '../tools/current_chase_payment_v124.mjs';
import {installChaseSoundScheduler} from '../tools/current_chase_sound_scheduler_v124.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerQuicksandSeal191(root,swogi);let scenarios=0;
function fresh(grade=1,setup){
 const g=new GameState(undefined,undefined,'quicksand-software-boundaries');
 for(const p of g.players){p.character='he1';p.hp=1000;p.max_hp=1000;p.cards=['601011','601011'];p.max_physique=100;}
 g.players[0].cards=['601011','99101'+grade];
 installCurrentQiPayment(g);installSeasonPrimitives(g);setup?.(g);
 const ext=installQuicksandSeal191(root,g,swogi);g.start_of_game_setup();
 return {g,p:g.players[0],q:g.players[1],ext};
}
// All rarities trigger before they have been played; integer boundaries.
for(let grade=1;grade<=3;grade++)for(const defense of [0,3,4,7,8,17]){
 const {g,p,q,ext}=fresh(grade);p.def=defense;g.do_hard_bamboo();
 assert.equal(q.hp,1000-Math.trunc(defense/4));assert.equal(p.def,defense);
 assert.equal(ext.metadata().events.length,1);assert.equal(p.activate_earth_spirit_stacks,0);scenarios++;
}
// Actual body uses defense callbacks, activates earth, requests chase.
for(let grade=1;grade<=3;grade++){
 const {g,p}=fresh(grade);g.play_card(p.cards[1],1);
 assert.equal(p.def,[2,6,10][grade-1]);assert.equal(p.activate_earth_spirit_stacks,1);
 assert.equal(p.this_card_chases,1);assert.equal(p.cloud_sword_chain_count,0);scenarios++;
}
{const {g,p,q,ext}=fresh();p.cards=['991011','991012','991013'];p.def=20;g.do_hard_bamboo();
 assert.equal(q.hp,995);assert.equal(ext.metadata().events.length,1);scenarios++;}
{const {g,p,q}=fresh();p.def=20;p.cards[1]='601011';g.do_hard_bamboo();assert.equal(q.hp,1000);
 p.cards[1]='991013';g.do_hard_bamboo();assert.equal(q.hp,995);scenarios++;}
// Ordinary nonattack damage is absorbed by defense and guard.
{const {g,p,q}=fresh();p.def=20;q.def=3;g.do_hard_bamboo();assert.equal(q.hp,998);assert.equal(q.def,0);scenarios++;}
{const {g,p,q}=fresh();p.def=20;q.guard_up=1;g.do_hard_bamboo();assert.equal(q.hp,1000);assert.equal(q.guard_up,0);scenarios++;}
// Defense is read after the preceding effect and all of its callbacks.
{const {g,p,q,ext}=fresh(1,g=>{const f=g.do_hard_bamboo.bind(g);g.do_hard_bamboo=()=>{f();g.increase_idx_def(0,8);};});
 p.def=8;p.hard_bamboo_stacks=1;g.do_hard_bamboo();assert.equal(q.hp,994);
 assert.equal(ext.metadata().events[0].defense,16);scenarios++;}
// Run the four real schedulers: unplayed seal follows bamboo and precedes cat.
for(const scheduler of [installCurrentQiPayment,installCurrentSoundScheduler,installChasePayment,installChaseSoundScheduler]){
 const order=[];const {g,p,ext}=fresh(1,g=>{
  const bamboo=g.do_hard_bamboo.bind(g),cat=g.do_three_tailed_cat.bind(g);
  g.do_hard_bamboo=()=>{order.push('bamboo');bamboo();};
  g.do_three_tailed_cat=()=>{order.push('cat');cat();};
 });
 scheduler(g,(_p,_id,cost)=>cost);p.def=16;
 const damage=g.deal_damage.bind(g);g.deal_damage=n=>{order.push('seal');damage(n);};g.sim_turn();
 assert.deepEqual(order,['bamboo','seal','cat']);
 assert.equal(ext.metadata().events.filter(e=>e.kind==='card_body').length,0);
 assert.equal(ext.metadata().events.length,1);scenarios++;
}
{const {g,p}=fresh();p.def=NaN;assert.throws(()=>g.do_hard_bamboo(),/integer_range/);scenarios++;}
console.log(JSON.stringify({passed:true,scenarios,scope:'software edge cases; not independent replay acceptance'}));
