import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerDreamIntentWater,installDreamIntentWater} from '../tools/current_dream_intent_water_v92.mjs';
import {installFlowerHistory} from '../tools/current_flower_history_v92.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));registerDreamIntentWater(root,swogi);
let scenarios=0;
function setup(id){
 const g=new GameState(undefined,undefined,'v92-source-boundary');
 for(const p of g.players)Object.assign(p,{character:'sw3',hp:100,max_hp:200,qi:0,cards:[id,'601011']});
 const observer=installDreamIntentWater(root,g,swogi);g.start_of_game_setup();g.players[0].currently_playing_card_idx=0;
 return {g,p:g.players[0],q:g.players[1],observer};
}
for(let i=1;i<=3;i++){
 const id='75285'+i,{g,p}=setup(id);g.trigger_card(id,0);
 assert.equal(p.sword_intent,i+2);assert.equal(p.this_card_chases,0);assert.equal(p.next_attack_double_sword_intent_and_increase_atk,0);scenarios++;
}
for(let i=1;i<=3;i++){
 const id='75303'+i,{g,p,q,observer}=setup(id);p.qi=3;p.force_of_water=4;q.def=3;
 const base=[5,7,9,5,10][i-1]+7;g.trigger_card(id,0);
 const n=base-3,heal=i>=4?Math.floor(n/3):0;
 assert.equal(q.hp,100-n);assert.equal(p.hp,100+heal);assert.equal(p.max_hp,200+heal);
 assert.equal(p.qi,3);assert.equal(p.force_of_water,4);assert.equal(observer.metadata().events[0].base_attack,base);scenarios++;
}
{
 const {g,p,q}=setup('753033');q.guard_up=1;g.trigger_card('753033',0);
 assert.equal(q.hp,100);assert.equal(p.hp,100);assert.equal(p.max_hp,200);scenarios++;
}
{
 const {g,p}=setup('753031');p.blossom_dance_stacks=1;const observer=installFlowerHistory(root,g,swogi);g.trigger_card('753031',0);
 assert.equal(observer.metadata().events.at(-1).water_count,1);scenarios++;
}
process.stdout.write(JSON.stringify({passed:true,scenarios,scope:'source-derived checks, not replay or policy acceptance'}));
