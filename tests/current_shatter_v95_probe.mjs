// Real trigger and damage path, explicit software fixtures.
import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerShatter,shatterFacts} from '../tools/current_shatter_v95.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const before=new Map(Object.entries(swogi).map(([id,c])=>[id,{...c}]));
const ids=new Set(shatterFacts(root).cards.map(c=>c.runtime_id));registerShatter(root,swogi);
for(const [id,c] of before){
 if(!ids.has(id)){assert.deepEqual(swogi[id],c);continue;}
 const {card_actions:a,...old}=c,{card_actions:b,...now}=swogi[id];assert.deepEqual(old,now);assert.notEqual(a,b);assert.equal(now.hp_cost,8);
}
assert.throws(()=>registerShatter(root,swogi),/already_registered/);
let scenarios=0;
for(const [grade,count] of [[1,2],[2,3],[3,4]])for(const [def,hploss,remaining] of [[0,3*count,0],[5,3*count-2,0],[30,0,30-6*count]]){
 const id='14509'+grade,g=new GameState(undefined,undefined,'shatter-software');
 for(const p of g.players)Object.assign(p,{character:'sw3',hp:100,max_hp:100,qi:20,cards:[id,'111011','601011']});
 g.start_of_game_setup();const [a,b]=g.players;Object.assign(b,{hp:100,def});
 const seen=[],atk=g.atk;g.atk=function(...args){seen.push({args,marker:a.crash_fist_shatter_stacks});return Reflect.apply(atk,this,args);};
 a.currently_playing_card_idx=0;g.trigger_card(id,0);
 assert.equal(b.hp,100-hploss);assert.equal(b.def,remaining);assert.equal(a.crash_fist_shatter_stacks,1);
 assert.deepEqual(seen,Array.from({length:count},()=>({args:[3,false,true],marker:0})));scenarios++;
}
process.stdout.write(JSON.stringify({passed:true,scenarios,scope:'software body/count/smash/post-marker checks; not independent battle acceptance'}));
