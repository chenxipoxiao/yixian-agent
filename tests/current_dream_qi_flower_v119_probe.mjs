import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerDreamBasics,installDreamBasics} from '../tools/current_dream_basics_v93r2.mjs';
import {registerDreamQiFlower,installDreamQiFlower,dreamQiFlowerFacts} from '../tools/current_dream_qi_flower_v119.mjs';
import {installCurrentQiPayment} from '../tools/current_qi_payment_v79.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerDreamBasics(root,swogi);const prior=new Map(Object.entries(swogi)),facts=dreamQiFlowerFacts(root);
registerDreamQiFlower(root,swogi);
for(const [id,c] of prior)if(!facts.cards.some(x=>x.runtime_id===id))assert.equal(swogi[id],c);
assert.throws(()=>registerDreamQiFlower(root,swogi),/already_registered/);
const cases=[],scenario=(name,fn)=>{fn();cases.push(name);};
function fresh(cards=['D12061','111011','111011']){
 const g=new GameState(undefined,undefined,'dream-qi-flower-software');
 for(const p of g.players)Object.assign(p,{character:'he1',hp:100,max_hp:300,qi:20,cards:[...cards]});
 installCurrentQiPayment(g);installDreamBasics(root,g,swogi);const obs=installDreamQiFlower(root,g,swogi);
 g.start_of_game_setup();return {g,p:g.players[0],q:g.players[1],obs};
}
for(const c of facts.cards){
 scenario('realm-body-'+c.raw_id,()=>{
  const {g,p,q,obs}=fresh([c.runtime_id,'111011','111011']),hp=p.hp,qi=p.qi;
  g.play_card(c.runtime_id,0);
  if(c.kind==='qi'){
   assert.equal(p.qi,qi+c.config.anima);assert.equal(p.increase_atk,c.config.otherParams[0]);assert.equal(p.next_attack_deals_extra,0);
  }else{
   assert.equal(q.internal_injury,1);assert.equal(p.hp,hp+(c.config.level>3?5:0));
   g.play_card(c.runtime_id,0);
   assert.equal(p.hp,hp+(c.config.level>3?10:c.config.otherParams[1]));
   assert.equal(q.internal_injury,c.config.level>3?2+Math.floor(10/c.config.otherParams[2]):2);
   assert.deepEqual(obs.metadata().events.filter(x=>x.kind==='card_body').map(x=>x.post_action),[false,true]);
  }
 });
}
for(const neighbors of [['D11014','D11015'],['D11013','D11014'],['D11015','D11013'],['D11014','111011']]){
 scenario('adjacency-'+neighbors.join('-'),()=>{
  const {g,p,obs}=fresh([neighbors[0],'111011',neighbors[1]]);
  g.check_adjacent_effects_before_card(1,'111011');const n=neighbors.filter(x=>x.startsWith('D1101')).length;
  assert.equal(p.dream_qi_perfusion_guarantee_injured,n);assert.equal(obs.metadata().events.at(-1).matching_neighbors,n);
  p.dream_qi_perfusion_guarantee_injured=0;g.play_card('111011',1);assert.equal(p.dream_qi_perfusion_guarantee_injured,0);
 });
}
scenario('unchanged-two-low-adjacency',()=>{
 const {g,p,obs}=fresh(['D11013','111011','D11013']);g.check_adjacent_effects_before_card(1,'111011');
 assert.equal(p.dream_qi_perfusion_guarantee_injured,2);assert.equal(obs.metadata(),null);
});
scenario('high-flower-uses-total-adjusted-healing-including-overflow',()=>{
 const {g,p,q,obs}=fresh(['D12064','111011','111011']);p.hp=p.max_hp;p.hp_gained=24;
 g.play_card('D12064',0);g.play_card('D12064',0);
 assert.equal(p.hp,p.max_hp);assert.equal(p.hp_gained,34);assert.equal(q.internal_injury,8);
 assert.equal(obs.metadata().events.at(-1).counter313,34);
});
scenario('high-flower-reads-after-post-action-callback',()=>{
 const {g,p,q,obs}=fresh(['D12065','111011','111011']);p.hp_gained=3;
 g.if_post_action=function(){assert.equal(p.hp_gained,8);this.increase_idx_hp(0,7);return true;};
 g.play_card('D12065',0);assert.equal(q.internal_injury,4);assert.equal(obs.metadata().events.at(-1).counter313,15);
});
scenario('blocked-healing-does-not-inflate313',()=>{
 const {g,p,q,obs}=fresh(['D12064','111011','111011']);p.prevent_gain_hp_stacks=1;p.hp_gained=19;p.preemptive_strike_stacks=1;
 g.play_card('D12064',0);assert.equal(p.hp_gained,19);assert.equal(q.internal_injury,4);assert.equal(obs.metadata().events.at(-1).counter313,19);
});
scenario('unadmitted-game-temporary-native-behavior-unchanged',()=>{
 const {g,p,obs}=fresh(['111011','111011','111011']);p.trigger_depth=1;p.currently_playing_card_idx=1;g.trigger_card('D12064',1);
 assert.equal(g.currentDreamQiFlowerActive,false);assert.equal(obs.metadata(),null);
});
scenario('new-qi-known-thunder-metadata-does-not-affect-classification',()=>{
 for(const c of facts.cards){assert.equal(swogi[c.runtime_id].is_thunder,prior.get(c.runtime_id).is_thunder);assert.equal(swogi[c.runtime_id].qi_cost,0);}
});
console.log(JSON.stringify({scenarios:cases.length,cases}));
