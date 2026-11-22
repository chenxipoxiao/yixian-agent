import {createSeasonPassives} from '../tools/current_season_passives_v93r3.mjs';
import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerDreamBasics,installDreamBasics} from '../tools/current_dream_basics_v93r2.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));registerDreamBasics(root,swogi);
let scenarios=0;
function setup(cards){
 const g=new GameState(undefined,undefined,'v93r2-source-boundary');
 for(const p of g.players)Object.assign(p,{character:'dx1',hp:100,max_hp:200,qi:0,cards:[...cards]});
 g.start_of_game_setup();g.players[0].currently_playing_card_idx=0;return {g,p:g.players[0],q:g.players[1]};
}
{
 const {g,p}=setup(['D14151','601011']);installDreamBasics(root,g,swogi);
 Object.assign(p,{internal_injury:1,weaken:2,flaw:3,decrease_atk:4,entangle:5,wound:6,styx:7,indigestion:8});
 g.trigger_card('D14151',0);assert.equal(p.def,43);assert.equal(p.entangle,5);assert.equal(p.physique,0);scenarios++;
}
{
 const {g,p}=setup(['D14152','601011']);installDreamBasics(root,g,swogi);p.indigestion=-4;
 g.trigger_card('D14152',0);assert.equal(p.def,10);scenarios++;
}
{
 const {g,p}=setup(['D14191','601011']);let seen=[];const native=g.do_pre_crash_fist.bind(g);
 g.do_pre_crash_fist=function(id){seen.push({id,physique:p.physique,depth:p.trigger_depth});return native(id);};
 const observer=installDreamBasics(root,g,swogi);g.trigger_card('D14191',0);
 assert.equal(p.physique,2);assert.equal(p.dream_exercise_fist_physique_stacks,0);assert.equal(p.later_dream_exercise_fist_physique_stacks,0);
 p.trigger_depth=1;g.trigger_card('601011',1);p.trigger_depth=0;
 assert.deepEqual(seen.at(-1),{id:'601011',physique:4,depth:2});assert.equal(p.physique,4);
 g.trigger_card('601011',1);assert.equal(p.physique,4);assert.equal(observer.metadata().events.filter(x=>x.kind==='before_card_707').length,1);scenarios++;
}
{
 const {g,p,q}=setup(['D11011','601011']);installDreamBasics(root,g,swogi);
 g.trigger_card('D11011',0);assert.equal(p.qi,1);assert.equal(p.next_attack_deals_extra,5);
 g.trigger_card('601011',1);assert.equal(q.hp,92);assert.equal(p.next_attack_deals_extra,0);
 g.trigger_card('601011',1);assert.equal(q.hp,89);scenarios++;
}
{
 const {g,p,q}=setup(['D11013','601011','D11013']);const observer=installDreamBasics(root,g,swogi);
 let during=0;const body=g.just_do_the_card_and_nothing_else.bind(g);
 g.just_do_the_card_and_nothing_else=function(id){during=p.dream_qi_perfusion_guarantee_injured;return body(id);};
 q.def=100;p.penetrate=2;g.trigger_card('601011',1);
 assert.equal(during,2);assert.equal(p.penetrate,0);assert.equal(p.dream_qi_perfusion_guarantee_injured,0);
 assert.equal(observer.metadata().events[0].matching_neighbors,2);scenarios++;
}
{
 const {g,p}=setup(['D11013','601011']);installDreamBasics(root,g,swogi);
 const seasons=createSeasonPassives(root,g,swogi,{players:[[7050,7132],[]]});seasons.installBoundary(7050);seasons.installBoundary(7132);
 assert.equal(g.is_cloud_sword('D11013'),false);assert.equal(g.is_sword_formation('D11013'),false);
 g.trigger_card('D11013',0);assert.equal(p.qi,1);assert.equal(p.cloud_sea,0);assert.equal(p.moon_water_sword_formation_stacks,0);scenarios++;
}
process.stdout.write(JSON.stringify({passed:true,scenarios,scope:'source-boundary checks, not replay acceptance'}));
