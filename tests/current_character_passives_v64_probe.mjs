import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerCharacterPassives,installCharacterPassives} from '../tools/current_character_passives_v64.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerCharacterPassives(root,swogi);let scenarios=0;
const fields=['internal_injury','weaken','flaw','decrease_atk','entangle','wound','styx','indigestion'];
function fresh(cards=['601011','601011','601011']){
 const g=new GameState(undefined,undefined,'character-passives-boundaries');
 for(const p of g.players){p.character='sw1';p.hp=200;p.max_hp=200;p.max_physique=100;p.cards=['601011','601011','601011'];p.hand_count=0;}
 g.players[0].cards=[...cards];const o=installCharacterPassives(root,g,swogi,[1,0]);g.start_of_game_setup();return {g,o,p:g.players[0],q:g.players[1]};
}
// Passive starts with ownership, duplicates do not multiply it, both seats work.
for(const copies of [1,2])for(const seat of [0,1])for(const field of fields){
 const {g,o,p,q}=fresh(Array(copies).fill('764001').concat(['601011']));if(seat===1){q.cards=p.cards;p.cards=['601011'];}
 const target=g.players[seat],before=target.physique;g.increase_idx_debuff(seat,field,3);
 assert.equal(target.physique,before+3);g.reduce_idx_x_by_c(seat,field,99);assert.equal(target.physique,before+6);
 g.reduce_idx_x_by_c(seat,field,1);assert.equal(target.physique,before+6);
 assert.deepEqual(o.metadata().events.filter(e=>e.kind==='415_debuff_change').map(e=>e.actual_layers),[3,3]);scenarios++;
}
for(let rank=1;rank<=3;rank++){
 const {g,p}=fresh(['76400'+rank,'601011']);p.character='dx3';p.hp=150;
 g.play_card('76400'+rank,0);const n=rank+2;assert.equal(p.styx,n);assert.equal(p.physique,n);assert.equal(p.hp,150+3*n);assert.equal(p.max_hp,200+n);scenarios++;
}
{
 const {g,p}=fresh(['764001','601011']);p.hexproof=3;g.increase_idx_debuff(0,'weaken',2);assert.equal(p.physique,0);
 g.increase_idx_debuff(0,'flaw',3);assert.equal(p.physique,2);assert.equal(p.flaw,2);
 p.cards=['601011'];g.increase_idx_debuff(0,'flaw',2);assert.equal(p.physique,2);scenarios++;
}
// Physique increases capacity before the styx heal. Crossing the physique limit
// converts only the excess to HP through the existing physique callback.
for(const loss of [false,true]){
 const {g,p}=fresh(['764001']);p.character='dx3';p.max_physique=2;p.physique=1;
 if(loss){p.styx=3;g.reduce_idx_x_by_c(0,'styx',5);}else g.increase_idx_debuff(0,'styx',3);
 assert.equal(p.physique,4);assert.equal(p.max_hp,203);assert.equal(p.hp,203);scenarios++;
}
// Drunken flaw conversion precedes the physique callback.
{
 const {g,p}=fresh(['764001']);p.flaw=2;p.drunken_fist_stance_stacks=3;let atCallback;
 const cb=g.increase_idx_physique.bind(g);g.increase_idx_physique=(i,n)=>{atCallback=p.increase_atk;return cb(i,n);};
 g.reduce_idx_x_by_c(0,'flaw',9);assert.equal(atCallback,6);scenarios++;
}
for(let rank=1;rank<=3;rank++){
 const {g,p,q,o}=fresh(['76401'+rank,'601011']);g.play_card('76401'+rank,0);
 assert.equal(p.qi,rank+1);assert.equal(p.agility,4);assert.equal(p.can_play[0],false);
 assert.equal(q.hp,200-rank-1);let ev=o.metadata().events.filter(e=>e.kind==='762_after_card');assert.equal(ev.length,1);assert.equal(ev[0].base_attack,rank+1);
 g.play_card('601011',1);assert.equal(q.hp,200-2*(rank+1)-3);scenarios++;
}
// Count all eight category1 fields and floor the sum/2, once per real card.
for(const count of [0,1,2,7,8,9]){
 const {g,p}=fresh(['764011','601011']);g.play_card('764011',0);fields.forEach((k,i)=>p[k]=i<count?1:0);if(count===9)p.internal_injury++;
 const attacks=[];g.atk=(n,extra)=>attacks.push([n,extra]);g.play_card('601011',1);
 assert.deepEqual(attacks,[[3,undefined],[2+Math.floor(count/2),true]]);scenarios++;
}
{
 const {g,p,o}=fresh(['764011','764012','601011']);g.play_card('764011',0);g.play_card('764012',1);
 assert.equal(o.metadata().events.filter(e=>e.kind==='762_after_card').at(-1).stacks,5);
 swogi['764099']=Object.freeze({...swogi['601011'],card_actions:game=>game.trigger_card('601011',2)});
 const before=o.metadata().events.filter(e=>e.kind==='762_after_card').length;g.play_card('764099',2);
 assert.equal(o.metadata().events.filter(e=>e.kind==='762_after_card').length,before+1);scenarios++;
}
// The extra attack sees cleared crash-fist/card attack bonus, and runs before
// God Luck Avoid's heal/DEF. Damage callbacks continue to be the native ones.
{
 const {g,p}=fresh(['764011','141011']);g.play_card('764011',0);
 p.god_luck_avoid_stacks=1;p.hp=100;const seen=[],atk=g.atk.bind(g);
 g.atk=function(n,extra){if(extra)seen.push({bonus:p.bonus_atk_amt,hp:p.hp,def:p.def});return atk(n,extra);};
 g.play_card('141011',1);assert.equal(seen.at(-1).bonus,0);assert.equal(seen.at(-1).hp,100);assert.equal(p.hp,102);assert.equal(p.def,3);scenarios++;
}
for(let rank=1;rank<=3;rank++){
 const {g,p}=fresh(['76402'+rank,'601011']);p.max_chases=0;g.sim_turn();
 assert.equal(p.hp,198);assert.equal(p.agility,7+3*rank);assert.equal(p.overwhelming_power_stacks,2);assert.equal(p.can_play[0],false);scenarios++;
}
// Overflow shields before non-attack damage; force loss refills353 before362.
for(const seat of [0,1]){
 const {g,p,q}=fresh(['764021','601011']);if(seat===1){q.cards=p.cards;p.cards=['601011'];}
 const owner=g.players[seat];owner.force=2;owner.max_force=3;owner.overwhelming_power_stacks=4;
 const hits=[];g.deal_damage_inner=(n,isAttack,idx)=>hits.push({n,isAttack,idx,force:owner.force,def:owner.def});
 g.increase_idx_force(seat,3);assert.deepEqual(hits,[{n:8,isAttack:false,idx:seat,force:3,def:2}]);
 hits.length=0;owner.endless_force_stacks=2;g.reduce_idx_force(seat,5);
 assert.deepEqual(hits,[{n:12,isAttack:false,idx:seat,force:2,def:2}]);scenarios++;
}
{
 const {g,p}=fresh(['764021','764023','601011']);g.play_card('764021',0);g.play_card('764023',1);
 assert.equal(p.overwhelming_power_stacks,4);assert.equal(p.force,0);assert.equal(p.def,0);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios}));
