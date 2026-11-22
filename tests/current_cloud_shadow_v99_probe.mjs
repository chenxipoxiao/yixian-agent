import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {cloudShadowFacts,registerCloudShadow,installCloudShadow} from '../tools/current_cloud_shadow_v99.mjs';
import {installCloudsRain} from '../tools/current_clouds_rain_v99.mjs';
import {installCurrentQiPayment} from '../tools/current_qi_payment_v79.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const saved=new Map(Object.entries(swogi)),facts=cloudShadowFacts(root);registerCloudShadow(root,swogi);
for(const [id,c] of saved)assert.equal(swogi[id],c);
assert.throws(()=>registerCloudShadow(root,swogi),/already_registered/);
const fixture=(id,setup=true)=>{
 const g=new GameState(undefined,undefined,'cloud-shadow-software');
 for(const p of g.players)Object.assign(p,{character:'sw3',hp:500,max_hp:500,qi:20,cards:[id,'601011','601011']});
 installCurrentQiPayment(g);const observer=installCloudShadow(root,g,swogi,[0,1]);
 if(setup)g.start_of_game_setup();return {g,observer,p:g.players[0]};
};
let scenarios=0;
for(const c of facts.cards)for(const reason of ['none','accepted','entangle','cap','683']){
 const {g,p,observer}=fixture(c.runtime_id);
 if(reason!=='none'){
  Object.assign(p,{this_card_chases:1,entangle:reason==='entangle'?1:0,chases:reason==='cap'?1:0,dream_predicament_for_immortals_stacks:reason==='683'?1:0});
  g.process_this_card_chases();
 }
 // Deliberately advance to a later turn: successful738 must survive this reset.
 Object.assign(p,{this_card_chases:0,chases:0,entangle:0,dream_predicament_for_immortals_stacks:0,increase_atk:4,currently_playing_card_idx:0});
 const attacks=[],atk=g.atk;g.atk=function(n){attacks.push([n,p.increase_atk]);return Reflect.apply(atk,this,[n]);};
 g.trigger_card(c.runtime_id,0);
 assert.deepEqual(attacks,[[c.config.attack,4]]);assert.equal(p.increase_atk,4+c.config.otherParams[0]);
 const e=observer.metadata().events.at(-1);assert.equal(e.successful_chases_before,reason==='accepted'?1:0);
 assert.equal(e.requested_chase,reason==='accepted');assert.equal(p.this_card_chases,reason==='accepted'?1:0);
 assert.equal(p.cloud_sword_chain_count,1);scenarios++;
}
for(const mode of ['ordinary','linked','cloud_sea_fate']){
 const {g,p,observer}=fixture('799001');
 Object.assign(p,{qi:1,cloud_sword_chain_count:mode==='linked'?1:0,endurance_as_cloud_sea_stacks:mode==='cloud_sea_fate'?1:0});
 g.sim_turn();assert.equal(p.qi,mode==='ordinary'?0:1);assert.equal(observer.metadata().events.length,1);scenarios++;
}
{
 const {g,p,observer}=fixture('799001');p.qi=0;g.sim_turn();assert.equal(observer.metadata(),null);assert.equal(p.qi,1);scenarios++;
}
{
 const {g,p}=fixture('799001',false);p.hand_count=3;
 const clouds=installCloudsRain(root,g,{players:[{board:[1000093,0,0],hand:[1000093,1010093,1020093]},null]},[0,1]);
 g.start_of_game_setup();const e=clouds.metadata().events[0];assert.equal(e.hand_cloud_count,3);assert.equal(e.board_cloud_count,1);scenarios++;
}
{
 const {g,p,observer}=fixture('799001');p.this_card_chases=1;g.process_this_card_chases();
 g.players.reverse();g.players[0].currently_playing_card_idx=0;g.trigger_card('799001',0);
 assert.equal(observer.metadata().events[0].successful_chases_before,0);assert.deepEqual(observer.metadata().successful_chases,[1,0]);scenarios++;
}
process.stdout.write(JSON.stringify({passed:true,scenarios,scope:'software boundaries; development full-battle comparisons required separately'}));
