import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {nethermindFacts,registerNethermind,installNethermind} from '../tools/current_nethermind_v118.mjs';
import {registerLightningRepeat} from '../tools/current_lightning_repeat_v116.mjs';
import {installLightningInterleaving} from '../tools/current_lightning_interleaving_v118.mjs';
import {registerHexagramThunder,installHexagramThunder} from '../tools/current_hexagram_thunder_v118.mjs';
import {installCurrentQiPayment} from '../tools/current_qi_payment_v79.mjs';
import {createRegenOpening} from '../tools/current_regen_opening_v73.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const saved=new Map(Object.entries(swogi)),facts=nethermindFacts(root);
registerNethermind(root,swogi);registerLightningRepeat(root,swogi);registerHexagramThunder(root,swogi);
for(const [id,c] of saved)assert.equal(swogi[id],c);
assert.throws(()=>registerNethermind(root,swogi),/already_registered/);
const scenarios=[],scenario=(name,fn)=>{fn();scenarios.push(name);};
function fresh(id='811801',order=[0,1]){
 const g=new GameState(undefined,undefined,'nethermind-software');
 for(const p of g.players)Object.assign(p,{character:'dx4',hp:100,max_hp:500,physique:20,max_physique:80,qi:20,cards:[id,'601011','644021']});
 installCurrentQiPayment(g);const obs=installNethermind(root,g,swogi,order);
 g.start_of_game_setup();return {g,obs,p:g.players[0],q:g.players[1]};
}
for(const c of facts.cards){
 scenario('body-grade-'+c.raw_id,()=>{
  const {g,p,obs}=fresh(c.runtime_id),before={phy:p.physique,hp:p.hp,max:p.max_hp,qi:p.qi};
  g.play_card(c.runtime_id,0);
  assert.equal(p.physique,before.phy+c.config.physique);assert.equal(p.max_hp,before.max+c.config.physique);assert.equal(p.hp,before.hp);
  assert.equal(p.qi,before.qi);assert.equal(p.agility,10);assert.equal(p.meditation_of_xuan_stacks,c.config.otherParams[0]);
  assert.equal(p.internal_injury,0);assert.equal(p.regen,0);assert.equal(p.can_play[0],false);
  assert.equal(obs.metadata().events.length,1);
 });
 scenario('next-turn-order-grade-'+c.raw_id,()=>{
  const {g,p,obs}=fresh(c.runtime_id);g.sim_turn();
  assert.equal(p.internal_injury,0);assert.equal(p.regen,0);assert.equal(p.qi,20);
  const sequence=[],regen=g.do_regen.bind(g),injury=g.do_internal_injury.bind(g),startHp=p.hp;
  g.do_regen=function(){sequence.push(['regen',p.regen,p.hp]);return regen();};
  g.do_internal_injury=function(i,start){sequence.push(['injury',p.internal_injury,p.hp]);return injury(i,start);};
  g.sim_turn();const amount=c.config.otherParams[0];
  assert.deepEqual(sequence,[['regen',amount,startHp],['injury',amount,startHp+amount]]);
  assert.equal(p.hp,startHp);assert.equal(obs.metadata().events.filter(e=>e.kind==='391_turn_start').length,1);
 });
}
scenario('base81-and-extreme439-share391',()=>{
 const {g,p,obs}=fresh();g.play_card('644021',2);g.play_card('811801',0);g.do_meditation_of_xuan();
 assert.equal(p.meditation_of_xuan_stacks,4);assert.equal(p.internal_injury,4);assert.equal(p.regen,4);
 assert.equal(obs.metadata().events.at(-1).amount,4);
});
scenario('untouched-base-owner-delegates',()=>{
 const {g,p,obs}=fresh();g.play_card('644021',2);g.do_meditation_of_xuan();
 assert.equal(p.internal_injury,2);assert.equal(p.regen,2);assert.equal(obs.metadata(),null);
});
scenario('391-captured-before-both-callbacks',()=>{
 const {g,p,obs}=fresh();g.play_card('811801',0);const add=g.increase_idx_x_by_c.bind(g);
 // Synthetic callback verifies the saved-client local8 semantics.
 g.increase_idx_x_by_c=function(i,k,n){const r=add(i,k,n);if(k==='internal_injury')p.meditation_of_xuan_stacks+=7;return r;};
 g.do_meditation_of_xuan();assert.equal(p.internal_injury,2);assert.equal(p.regen,2);assert.equal(p.meditation_of_xuan_stacks,9);
 assert.equal(obs.metadata().events.at(-1).amount,2);
});
scenario('owner-tracked-across-seat-swap',()=>{
 const {g,p,q,obs}=fresh('811801',[1,0]);g.play_card('811801',0);g.players.reverse();g.do_meditation_of_xuan();
 assert.equal(q.internal_injury,0);g.players.reverse();g.do_meditation_of_xuan();assert.equal(p.internal_injury,2);
 assert.equal(obs.metadata().events.at(-1).player_index,1);
});
scenario('477-multiplies-later-ticks-only',()=>{
 const {g,p}=fresh();const e=createRegenOpening(root,g,{players:[[{strategy_id:7135,enabled:true}],[]]});
 e.installOpening(7135);e.installOpening(7103);g.do_plant_start_permanent_buffs();
 g.play_card('811801',0);g.do_meditation_of_xuan();assert.equal(p.regen,2);assert.equal(p.internal_injury,2);
 const hp=p.hp;g.do_regen();assert.equal(p.hp,hp+4);g.do_internal_injury(0,true);assert.equal(p.hp,hp);
 assert.deepEqual(e.metadata().events.filter(x=>x.phase.startsWith('turn_start_')).map(x=>x.requested),[4,4]);
});
scenario('763-keeps-pending-on-nonthunder',()=>{
 const {g,p}=fresh();p.cards=['811601','811801','601011'];p.post_deck_setup();const e=installLightningInterleaving(root,g,swogi);
 g.play_card('811601',0);g.play_card('811801',1);assert.equal(e.metadata().events.length,1);
 g.play_card('811601',0);assert.equal(e.metadata().events.find(x=>x.kind==='763_repeat_before_main').pending_before,1);
});
scenario('wind-thunder-neighbor-known-false',()=>{
 const {g,p}=fresh();p.cards=['767011','811801','601011'];p.post_deck_setup();const e=installHexagramThunder(root,g,swogi);
 g.play_card('767011',0);assert.equal(e.metadata().events.find(x=>x.kind==='card_body').as_attack,false);
});
scenario('temporary-effect-does-not-disable-caller-slot',()=>{
 const {g,p}=fresh();p.trigger_depth=1;p.currently_playing_card_idx=1;g.trigger_card('811801',0);p.trigger_depth=0;
 assert.equal(p.can_play[1],true);assert.equal(p.meditation_of_xuan_stacks,2);assert.equal(p.internal_injury,0);
});
process.stdout.write(JSON.stringify({passed:true,scenarios:scenarios.length,names:scenarios,scope:'Software boundaries; complete replay comparisons are separate'}));
