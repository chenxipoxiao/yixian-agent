import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {cloudCatFacts,registerCloudCat,installCloudCat} from '../tools/current_cloud_cat_v115.mjs';
import {installCloudsRain} from '../tools/current_clouds_rain_v115.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const saved=new Map(Object.entries(swogi)),facts=cloudCatFacts(root);registerCloudCat(root,swogi);
for(const [id,c] of saved)assert.equal(swogi[id],c);
assert.throws(()=>registerCloudCat(root,swogi),/already_registered/);
const fixture=(id,setup=true)=>{
 const g=new GameState(undefined,undefined,'cloud-cat-software');
 for(const p of g.players)Object.assign(p,{character:'sw3',hp:500,max_hp:500,qi:20,cards:[id,'601011','601011']});
 const observer=installCloudCat(root,g,swogi,[0,1]);
 if(setup)g.start_of_game_setup();return {g,observer,p:g.players[0],q:g.players[1]};
};
let scenarios=0;
for(const c of facts.cards){
 const {g,p,q,observer}=fixture(c.runtime_id);p.currently_playing_card_idx=0;
 g.trigger_card(c.runtime_id,0);
 assert.equal(p.max_hp,500+c.config.otherParams[0]);assert.equal(p.hp,p.max_hp);
 assert.equal(q.hp,500-c.config.otherParams[1]);assert.equal(p.can_play[0],false);
 const es=observer.metadata().events;assert.equal(es.length,2);assert.equal(es[1].kind,'757_after_cloud');
 assert.equal(es[1].base_attack,c.config.otherParams[1]);scenarios++;
 // A later ordinary attack must not trigger757; its body still acts normally.
 const hp=q.hp;g.trigger_card('601011',1);assert.equal(q.hp,hp-3);assert.equal(observer.metadata().events.length,2);scenarios++;
}
{
 const {g,p,q,observer}=fixture('811501');p.trigger_depth=1;
 g.trigger_card('811501',0);assert.equal(q.hp,500);assert.equal(observer.metadata().events.length,1);
 // Temporary execution gains757, but skips its own outer post-card trigger.
 p.trigger_depth=0;g.trigger_card('811501',0);assert.equal(q.hp,492);
 assert.equal(observer.metadata().events.at(-1).base_attack,8);scenarios++;
}
{
 const {g,p,q,observer}=fixture('811501');Object.assign(p,{increase_atk:2,sword_intent:3});q.def=4;
 g.trigger_card('811501',0);
 assert.equal(q.def,0);assert.equal(q.hp,495);assert.equal(p.sword_intent,0);
 assert.equal(observer.metadata().events.at(-1).base_attack,4);scenarios++;
}
{
 const {g,p,q,observer}=fixture('811501');g.trigger_card('811501',0);const hp=p.hp;
 g.players.reverse();g.trigger_card('601011',0);assert.equal(p.hp,hp-3);
 assert.equal(observer.metadata().events.length,2);scenarios++;
}
{
 const {g,p}=fixture('811501',false);p.hand_count=3;
 const obs=installCloudsRain(root,g,{players:[{board:[403,0,0],hand:[403,10403,20403]},null]},[0,1]);
 g.start_of_game_setup();assert.equal(obs.metadata().events[0].hand_cloud_count,3);assert.equal(obs.metadata().events[0].board_cloud_count,1);scenarios++;
}
{
 const {g,p}=fixture('811501');p.cloud_sword_endless_stacks=2;
 assert.throws(()=>g.trigger_card('811501',0),/446_nonattacking_interaction/);scenarios++;
}
{
 const {g,p,observer}=fixture('601011');g.trigger_card('601011',0);assert.equal(observer.metadata(),null);
 assert.throws(()=>installCloudCat(root,g,swogi),/already_installed/);scenarios++;
}
process.stdout.write(JSON.stringify({passed:true,scenarios,scope:'scheduler and attack-boundary software probes, not replay acceptance'}));
