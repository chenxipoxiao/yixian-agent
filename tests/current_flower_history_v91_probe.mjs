import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installFlowerHistory} from '../tools/current_flower_history_v91.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
function run(prefix,owner=true,patched=true){
 const g=new GameState(undefined,undefined,'flower-history-software');
 for(const p of g.players)Object.assign(p,{character:'fe3',hp:1000,max_hp:1000,qi:20,cards:['133091','131053','632011']});
 g.players[0].blossom_dance_stacks=Number(owner);
 const observer=patched?installFlowerHistory(root,g,swogi):null;g.start_of_game_setup();
 const p=g.players[0];p.currently_playing_card_idx=0;
 for(const id of prefix)g.trigger_card(id,0);
 p.this_card_chases=0;
 const before={qi:p.qi,max_hp:p.max_hp};g.trigger_card('632011',2);
 return {g,p,observer,before};
}
let scenarios=0;
// Original bug: the water formation has been consumed; a later earth card
// replaces330, but the completed water card still establishes766.
for(const prefix of [['133091','131053'],['133091','601011']]){
 const old=run(prefix,true,false),now=run(prefix);
 assert.equal(old.p.this_card_chases,0);assert.equal(now.p.this_card_chases,1);
 assert.equal(now.p.qi-now.before.qi,2);assert.equal(now.p.max_hp,now.before.max_hp);
 assert.equal(now.observer.metadata().events.at(-1).generating_interaction,false);scenarios++;
}
for(const prefix of [[],['131053']]){assert.equal(run(prefix).p.this_card_chases,0);scenarios++;}
{
 const a=run(['133091']),b=run(['133091'],true,false);
 assert.equal(a.p.this_card_chases,1);assert.equal(a.p.qi,b.p.qi);assert.equal(a.p.max_hp,b.p.max_hp);scenarios++;
}
{
 const a=run(['133091','131053'],false);assert.equal(a.p.this_card_chases,0);assert.equal(a.observer.metadata(),null);scenarios++;
}
// Chase request still enters the existing payment/cap/entangle scheduler.
{
 const {g,p}=run(['133091','131053']);p.entangle=1;g.process_this_card_chases();
 assert.equal(p.chases,0);assert.equal(p.entangle,0);scenarios++;
}
{
 const {g,p}=run(['133091','131053']);p.chases=p.max_chases;g.process_this_card_chases();
 assert.equal(p.chases,p.max_chases);scenarios++;
}
process.stdout.write(JSON.stringify({passed:true,scenarios,scope:'source-derived interaction checks, not replay acceptance'}));
