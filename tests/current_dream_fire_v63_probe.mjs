import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerDreamFire,installDreamFire,installSeasonStarOpening,usesDreamFlag} from '../tools/current_dream_fire_v63.mjs';
import {registerElementFlag} from '../tools/current_element_flag_v62r2.mjs';
import {installDreamFlag} from '../tools/current_element_flag_v63.mjs';
import {installCurrentQiPayment} from '../tools/current_qi_payment_v61.mjs';
import {installCurrentSoundScheduler} from '../tools/current_sound_scheduler_v61.mjs';
import {installChasePayment} from '../tools/current_chase_payment_v61.mjs';
import {installChaseSoundScheduler} from '../tools/current_chase_sound_scheduler_v61.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerElementFlag(root,swogi);registerDreamFire(root,swogi);
let scenarios=0;
function fresh(cards=['601011','601011','601011']){
 const g=new GameState(undefined,undefined,'dream-fire-boundaries');
 for(const p of g.players){p.character='sw1';p.hp=200;p.max_hp=200;p.max_physique=100;p.cards=['601011','601011','601011'];p.hand_count=0;}
 g.players[0].cards=[...cards];return g;
}
for(let tier=1;tier<=5;tier++){
 const id='D1317'+tier,g=fresh([id,'601011','601011']),o=installDreamFire(root,g,swogi,[1,0]);g.start_of_game_setup();
 const p=g.players[0],q=g.players[1];g.play_card(id,0);
 assert.equal(p.activate_fire_spirit_stacks,1);assert.equal(p.def,tier<4?2:6);
 const damage=tier<4?4+2*tier:6;assert.equal(q.hp,200-damage);assert.equal(q.max_hp,200-damage);assert.equal(q.times_max_hp_reduced,1);
 assert.equal(p.dream_fire_formation_stacks,tier<4?0:tier-1);assert.equal(p.can_play[0],tier<4);
 assert.equal(o.metadata().events[0].player_index,1);scenarios++;
}
for(let tier=1;tier<=5;tier++)for(const slot of [0,1]){
 const raw=6990090+10000*tier,g=fresh(['762001','601011','601011']);g.players[0].cards[0]='601011';g.players[0].cards[slot]='762001';g.players[0].hand_count=2;
 const value={hands:[[raw,7000031],null]};assert.equal(usesDreamFlag(root,value),true);
 const o=installDreamFlag(root,g,swogi,value);g.start_of_game_setup();g.play_card('762001',slot);
 assert.equal(o.metadata().events[0].formation.raw,raw);assert.equal(g.players[0].can_play[slot],true);
 assert.equal(g.players[0].dream_fire_formation_stacks,tier<4?0:tier-1);assert.equal(g.players[0].hp,slot===0?190:200);
 assert.deepEqual(value.hands[0],[raw,7000031]);scenarios++;
}
assert.equal(usesDreamFlag(root,{hands:[[7000031,7040090],null]}),false);scenarios++;
// Counter672 counts negative requests, including zero-capacity reductions, not
// the number of HP points lost. Zero and increased maxHP do not increment it.
{
 const g=fresh();g.start_of_game_setup();const q=g.players[1];
 g.reduce_idx_max_hp(1,0);assert.equal(q.times_max_hp_reduced,0);
 g.increase_idx_max_hp(1,5);assert.equal(q.times_max_hp_reduced,0);
 g.reduce_idx_max_hp(1,300);assert.equal(q.times_max_hp_reduced,1);assert.equal(q.max_hp,0);
 g.reduce_idx_max_hp(1,7);assert.equal(q.times_max_hp_reduced,2);assert.equal(q.max_hp,0);scenarios++;
}
for(let rank=1;rank<=3;rank++)for(const active of [false,true])for(const guard of [false,true]){
 const id='76300'+rank,g=fresh([id,'601011','601011']);g.start_of_game_setup();const p=g.players[0],q=g.players[1];
 q.times_max_hp_reduced=2;p.activate_fire_spirit_stacks=active?1:0;q.guard_up=guard?1:0;
 g.play_card(id,0);const hit=guard?0:4+6*rank+6,extra=active?Math.floor(hit/5):0;
 assert.equal(q.hp,200-hit-extra);assert.equal(q.max_hp,200-extra);assert.equal(q.times_max_hp_reduced,2+(extra>0?1:0));scenarios++;
}
// Pin request order independently of the usual attack having lowered HP.
{
 const g=fresh();g.start_of_game_setup();const calls=[];g.players[0].activate_fire_spirit_stacks=1;
 g.atk=()=>{g.players[0].damage_dealt_to_hp_by_this_card_atk=10;};
 const max=g.reduce_idx_max_hp.bind(g),hp=g.reduce_idx_hp.bind(g);
 g.reduce_idx_max_hp=(i,n)=>{calls.push('max');return max(i,n);};g.reduce_idx_hp=(i,n)=>{calls.push('hp');return hp(i,n);};
 swogi['763001'].card_actions(g);assert.deepEqual(calls,['max','hp']);assert.equal(g.players[1].hp,196);scenarios++;
}
const schedulers=[g=>installCurrentQiPayment(g),g=>installCurrentSoundScheduler(g),g=>installChasePayment(g,x=>x),g=>installChaseSoundScheduler(g,x=>x)];
for(const scheduler of schedulers)for(const limit of [0,1])for(const entangled of [false,true]){
 const g=fresh(['762001','601011','601011']);scheduler(g);g.players[0].hand_count=1;
 installDreamFlag(root,g,swogi,{hands:[[7040090],null]});g.start_of_game_setup();
 const p=g.players[0],q=g.players[1];p.max_chases=limit;p.entangle=entangled?1:0;
 g.sim_turn();const chase=limit===1&&!entangled;
 assert.equal(q.times_max_hp_reduced,chase?2:1);assert.equal(p.def,chase?10:6);assert.equal(q.max_hp,chase?190:194);
 assert.equal(q.hp,chase?187:194);assert.equal(p.can_play[0],true);scenarios++;
}
for(const scheduler of schedulers){
 const g=fresh(['762001','601011','601011']);scheduler(g);g.players[0].hand_count=1;installDreamFlag(root,g,swogi,{hands:[[7040090],null]});g.start_of_game_setup();
 g.players[1].hp=9;g.sim_turn();assert.equal(g.players[1].hp,-1);assert.equal(g.players[1].times_max_hp_reduced,2);
 assert.equal(g.players[0].def,10);assert.equal(g.players[0].next_card_index,1);assert.equal(g.game_over,true);scenarios++;
}
// Empty and preexisting star grids: only one hexagram, never star power or qi.
for(const owner of [0,1]){
 const g=fresh(),v={players:[[],[]]};v.players[owner]=[11002];
 const o=installSeasonStarOpening(root,g,v,[1,0]);g.start_of_game_setup();const p=g.players[1-owner];
 assert.equal(p.hexagram,1);assert.equal(p.star_power,0);assert.equal(p.qi,0);
 assert.deepEqual(p.is_star_point.slice(2,8),[true,true,true,true,true,true]);
 const after=JSON.stringify(o.metadata());if(g.players[0]!==p)g.swap_players();g.do_plant_start_permanent_buffs();assert.equal(p.hexagram,1);assert.equal(JSON.stringify(o.metadata()),after);scenarios++;
}
// Explicit preexisting full grid before the opening avoids AddXingWei's qi branch.
{
 const g=fresh();g.players[0].is_star_point=Array(8).fill(true);const o=installSeasonStarOpening(root,g,{players:[[11002],[]]});
 g.do_plant_start_permanent_buffs();assert.equal(g.players[0].qi,0);assert.deepEqual(o.metadata().events[0].added,[]);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios}));
