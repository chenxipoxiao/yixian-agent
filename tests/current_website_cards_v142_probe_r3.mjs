import assert from 'node:assert/strict';
import {execute} from '../tools/full_battle_bridge_web_v142r2.mjs';
const cases=[],scenario=(name,fn)=>{fn();cases.push(name);};
function fresh(cards,fn){
 const player={character:'sw1',hp:100,max_hp:100,qi:0,def:0,physique:0,max_physique:100,cultivation:50,round_number:12,destiny:100,hand_count:0,cards};
 return execute({players:[player,{...player,character:'he1',cards:['111011','111011','111011']}],first_player:0,seed:142,max_turns:128,include_trace:true,current_rules_context:{realms:[5,5]}},({game:g,swogi})=>{
  g.start_of_game_setup();for(const p of g.players)Object.assign(p,{hp:100,max_hp:100,qi:0,def:0});return fn(g,g.players[0],g.players[1],swogi);
 });
}
for(let tier=1;tier<=3;tier++){
 scenario('cloud-silence-'+tier+'-heal-and-grade-classification',()=>fresh(['94200'+tier,'111011','111012'],(g,p)=>{
  g.play_card(p.cards[0],0);assert.equal(p.hp,100+[10,16,22][tier-1]);assert.equal(p.max_hp,p.hp);
  assert.equal(g.is_unrestrained_sword('111011'),false);assert.equal(g.is_unrestrained_sword('111012'),true);
  assert.equal(p.can_play[0],false);p.dragon_devours_clouds_stacks=1;
  assert.equal(g.is_cloud_sword('111012'),true);assert.throws(()=>g.is_fake_unrestrained_sword('not-known'),/unknown_or_ambiguous_rarity/);
 }));
 scenario('cloud-steps-'+tier+'-odd-grid-repeat-once',()=>fresh(['94201'+tier,'111011','111011'],(g,p,q)=>{
  g.play_card(p.cards[0],0);assert.equal(p.qi,tier);assert.equal(p.cloud_sea,tier+1);assert.equal(p.agility,0);
  const hp=q.hp;g.play_card('111011',1);assert.equal(hp-q.hp,12);assert.equal(p.qi,tier);
  const next=q.hp;g.play_card('111011',2);assert.equal(next-q.hp,6);
 }));
 scenario('cloud-steps-'+tier+'-even-grid-agility',()=>fresh(['111011','94201'+tier,'111011'],(g,p,q)=>{
  g.play_card(p.cards[1],1);assert.equal(p.qi,tier);assert.equal(p.cloud_sea,tier+1);assert.equal(p.agility,10);
  const hp=q.hp;g.play_card('111011',2);assert.equal(hp-q.hp,6);
 }));
 scenario('night-howl-'+tier+'-attack-before-both-weaken',()=>fresh(['94202'+tier,'111011','111011'],(g,p,q)=>{
  q.def=99;g.play_card(p.cards[0],0);assert.equal(q.hp,100-[18,22,26][tier-1]);assert.equal(q.def,99);
  assert.equal(p.weaken,tier);assert.equal(q.weaken,tier);
 }));
}
scenario('205-creates-756-before-main-but-no-recursive-repeat',()=>fresh(['942011','111011','111011'],(g,p,q)=>{
 p.strike_twice_stacks=1;g.play_card(p.cards[0],0);assert.equal(p.qi,2);
 // Both402 bodies create a pending count. One cloud execution consumes one.
 const hp=q.hp;g.play_card('111011',1);assert.equal(hp-q.hp,12);
 const next=q.hp;g.play_card('111011',2);assert.equal(next-q.hp,12);
}));
scenario('756-kept-through-noncloud-card',()=>fresh(['942011','111041','111011'],(g,p,q)=>{
 g.play_card(p.cards[0],0);g.play_card(p.cards[1],1);const hp=q.hp;g.play_card(p.cards[2],2);assert.equal(hp-q.hp,12);
}));
scenario('756-unsupported-ultimate-interaction-refused',()=>fresh(['942011','111011','111011'],(g,p)=>{
 p.ultimate_overcome_formation_stacks=1;assert.throws(()=>g.play_card(p.cards[0],0),/756_280_interaction/);
}));
scenario('402-temporary-grid-not-guessed',()=>fresh(['942011','111011','111011'],(g,p)=>{
 p.trigger_depth=2;p.currently_triggering_card_id='942011';p.currently_triggering_card_idx=0;
 assert.throws(()=>g.executeWebsiteCard142('942011'),/temporary_402_grid_unresolved/);
}));
for (const card of ['942001','942011']) {
 scenario('outer-extreme-scheduler-combination-refused-'+card,()=>{
  assert.throws(()=>fresh(['145981',card,'111012'],()=>{throw new Error('guard_must_run_before_inspection');}),/755_756_extreme_footwork_schedule_unintegrated/);
 });
}
scenario('dynamic-mixed-board-rechecked-before-outer-scheduler',()=>fresh(['145981','111011','111012'],(g,p)=>{
 p.cards[1]='942011';assert.throws(()=>g.play_card('145981',0),/755_756_extreme_footwork_schedule_unintegrated/);
}));
scenario('temporary-755-body-rejected-with-extreme-scheduler',()=>fresh(['145981','111011','111012'],g=>{
 assert.throws(()=>g.executeWebsiteCard142('942001'),/755_756_extreme_footwork_schedule_unintegrated/);
}));
scenario('active-755-kept-in-admission-check-after-board-replacement',()=>fresh(['942001','111011','111012'],(g,p)=>{
 g.play_card('942001',0);p.cards=['145981','111011','111012'];
 assert.throws(()=>g.play_card('145981',0),/755_756_extreme_footwork_schedule_unintegrated/);
}));
console.log(JSON.stringify({passed:cases.length,cases,scope:'Explicit software mechanics; separate from complete real replay comparison.'}));
