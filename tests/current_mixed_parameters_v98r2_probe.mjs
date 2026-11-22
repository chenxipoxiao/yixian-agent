import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createMixedQueue} from '../tools/current_mixed_queue_v98.mjs';
import {registerHexagramThunder,installHexagramThunder} from '../tools/current_hexagram_thunder_v67.mjs';
import {installThunderTiming} from '../tools/current_thunder_timing_v68.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerHexagramThunder(root,swogi);
const facts=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-mixed-parameters-v98.json')));
let scenarios=0;
function fresh(id){const g=new GameState(undefined,undefined,'mixed-software');for(const p of g.players){p.character='he1';p.hp=500;p.max_hp=600;p.cards=[id,'601011','601011'];}g.start_of_game_setup();installHexagramThunder(root,g,swogi);installThunderTiming(root,g,swogi);return g;}
function body(g,id){Object.assign(g.players[0],{currently_triggering_card_id:id,currently_triggering_card_idx:0,currently_playing_card_idx:0});g.just_do_the_card_and_nothing_else(swogi[id]);}
for(const c of facts.cards.filter(c=>['lamp_flame','thunder_hexagram_formula'].includes(c.kind)))for(const forced of [false,true]){
 const g=fresh(c.runtime_id),p=g.players[0],r=c.reads[0],value=forced?r.hi:r.lo,seen=[],atk=g.atk.bind(g);
 p.hexagram=forced?1:0;p.triggered_hexagram_count=2;
 const q=createMixedQueue(swogi,g,[value],[1,0],facts);
 g.atk=n=>{seen.push([n,q.metadata().consumed]);return atk(n);};
 body(g,c.runtime_id);q.verifyTerminal();const e=q.metadata().events[0];
 assert.equal(e.player_index,1);assert.equal(e.forced_by_hexagram,forced);
 if(c.kind==='lamp_flame'){assert.deepEqual(seen,[[c.attack,0]]);assert.equal(g.players[1].internal_injury,value);assert.equal(p.hexagram,0);}
 else{assert.deepEqual(seen,[[value,1]]);assert.equal(p.triggered_hexagram_count,2+Number(forced));assert.equal(p.hexagram,Math.min(2+Number(forced),c.otherParams[0]));}
 scenarios++;
}
// Return from a preceding attack affects the next read, while debuff IDs do
// not spend the retained hexagram. Explicit -1 consumes one real queue item.
{
 const g=fresh('123051'),p=g.players[0];p.hexagram=1;
 const q=createMixedQueue(swogi,g,[9,101,-1,0],[0,1],facts);
 body(g,'123051');p.weaken=2;body(g,'312021');body(g,'312021');body(g,'121101');q.verifyTerminal();
 assert.deepEqual(q.metadata().events.map(e=>[e.type,e.value,e.forced_by_hexagram]),[['range',9,true],['debuff_id',101,false],['debuff_id',-1,false],['probability',0,true]]);
 assert.equal(p.triggered_hexagram_count,2);assert.equal(p.weaken,0);scenarios++;
}
for(const value of [0,1,2147483647]){
 const g=fresh('123111'),p=g.players[0];p.act_underhand_stacks=1;
 const q=createMixedQueue(swogi,g,[value],[0,1],facts);body(g,'123111');q.verifyTerminal();
 assert.equal(q.metadata().events[0].phase,'post_action');assert.equal(q.metadata().events[0].result,value<1);
 assert.equal(g.players[1].hp,value<1?488:500);scenarios++;
}
// Used/preemptive post-action branches must not consume the optional 108
// result. The following card receives the only item instead.
for(const cause of ['used','preemptive']){
 const g=fresh('123111'),p=g.players[0];p.act_underhand_stacks=1;
 if(cause==='used')p.can_post_action[0]=true;else p.preemptive_strike_stacks=1;
 const q=createMixedQueue(swogi,g,[3],[0,1],facts);body(g,'123111');body(g,'623031');q.verifyTerminal();
 assert.equal(q.metadata().events[0].kind,'lamp_flame');assert.equal(g.players[1].internal_injury,3);scenarios++;
}
for(const mode of ['underflow','leftover','range_fallback','range_high','forced_fail','buff_missing','unknown_buff','outside','unknown_consumer']){
 const g=fresh('623031');let stream=[1];
 if(mode==='leftover')stream=[1,2];if(mode==='range_fallback')stream=[-1];if(mode==='range_high')stream=[4];
 if(mode==='forced_fail')g.players[0].hexagram=1;
 if(mode==='buff_missing')stream=[101];if(mode==='unknown_buff')stream=[999];
 assert.throws(()=>{const q=createMixedQueue(swogi,g,stream,[0,1],facts);
  if(mode==='outside')g.rand_range(1,3);
  else if(mode==='unknown_consumer'){g.players[0].hexagram=1;g.trigger_hexagram(0);}
  else if(mode==='buff_missing'||mode==='unknown_buff')body(g,'312021');
  else{body(g,'623031');if(mode==='underflow')body(g,'623031');q.verifyTerminal();}
 },/mixed_parameters_unresolved/);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios,real_replays:false}));
