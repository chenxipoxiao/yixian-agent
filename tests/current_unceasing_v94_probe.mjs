// Software fixtures check real attack modifiers, gains, and callbacks.
import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerUnceasing,unceasingFacts} from '../tools/current_unceasing_v94.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const prior=new Map(Object.entries(swogi).map(([id,c])=>[id,{...c}]));
const facts=unceasingFacts(root),ids=new Set(facts.cards.map(c=>c.runtime_id));
registerUnceasing(root,swogi);
for(const [id,c] of prior){
 if(!ids.has(id)){assert.deepEqual(swogi[id],c);continue;}
 const {card_actions:a,...old}=c,{card_actions:b,...now}=swogi[id];assert.deepEqual(old,now);assert.notEqual(a,b);
}
assert.throws(()=>registerUnceasing(root,swogi),/already_registered/);
let scenarios=0;
for(const [grade,attack,gain] of [[1,6,3],[2,8,4],[3,10,5]])for(const weak of [0,1]){
 const id='64201'+grade,g=new GameState(undefined,undefined,'unceasing-software');
 for(const p of g.players)Object.assign(p,{character:'sw3',hp:100,max_hp:200,qi:20,physique:20,max_physique:21,cards:[id,'111011','601011']});
 g.start_of_game_setup();const [a,b]=g.players;Object.assign(a,{hp:100,max_hp:200,physique:20,max_physique:21,weaken:weak});Object.assign(b,{hp:100,def:2});
 const events=[];
 for(const method of ['atk','add_c_of_x','increase_idx_hp']){
  const fn=g[method];g[method]=function(...args){events.push([method,...args]);return Reflect.apply(fn,this,args);};
 }
 g.players[0].currently_playing_card_idx=0;g.trigger_card(id,0);
 assert.equal(b.hp,100-(Math.floor(attack*(weak?0.6:1))-2));
 assert.equal(a.physique,20+gain);assert.equal(a.max_hp,200+gain);
 assert.equal(a.hp,100+gain+(gain-1));
 assert.deepEqual(events.filter(e=>e[0]==='atk'||e[0]==='add_c_of_x').slice(0,2),[['atk',attack],['add_c_of_x',gain,'physique']]);
 assert.deepEqual(events.filter(e=>e[0]==='increase_idx_hp').at(-1),['increase_idx_hp',0,gain]);scenarios++;
}
process.stdout.write(JSON.stringify({passed:true,scenarios,scope:'software checks; full real-replay comparison remains required'}));
