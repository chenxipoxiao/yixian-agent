import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerBowRaven,bow_ravenFacts} from '../tools/current_bow_raven_v96.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const saved=new Map(Object.entries(swogi).map(([id,c])=>[id,{...c}]));
const ids=new Set(bow_ravenFacts(root).cards.map(c=>c.runtime_id));registerBowRaven(root,swogi);
for(const [id,c] of saved){
 if(!ids.has(id)){assert.deepEqual(swogi[id],c);continue;}
 const {card_actions:a,...old}=c,{card_actions:b,...now}=swogi[id];assert.deepEqual(old,now);assert.notEqual(a,b);
}
assert.throws(()=>registerBowRaven(root,swogi),/already_registered/);
const fixture=cards=>{
 const g=new GameState(undefined,undefined,'bow-raven-software');
 for(const p of g.players)Object.assign(p,{character:'sw3',hp:500,max_hp:500,qi:20,cards:[...cards]});
 g.start_of_game_setup();return g;
};
let scenarios=0;
for(const grade of [1,2,3])for(const qi of [0,1,3,4,8,20])for(const inDeck of [true,false]){
 const id='71403'+grade,g=fixture(inDeck?[id,'111011','601011']:['111011','111011','601011']),me=g.players[0];
 Object.assign(me,{qi,def:0,currently_playing_card_idx:0});g.trigger_card(id,0);
 const expected=grade===1?Math.min(qi*2,6):grade===2?Math.min(qi*2,16):qi*2;
 assert.equal(me.def,expected);assert.equal(me.this_card_chases,inDeck?1:0);scenarios++;
}
for(const [grade,gain] of [[1,12],[2,20],[3,28]])for(const underhand of [false,true]){
 const id='12512'+grade,g=fixture([id,'111011','601011']),me=g.players[0];
 Object.assign(me,{hp:80,max_hp:100,hp_gained:0,hexagram:underhand?2:1,act_underhand_stacks:underhand?1:0,currently_playing_card_idx:0});
 const attacks=[],atk=g.atk;g.atk=function(...args){attacks.push(args);return Reflect.apply(atk,this,args);};
 g.trigger_card(id,0);assert.equal(me.max_hp,100+gain);assert.equal(me.hp,80+gain);
 assert.equal(me.hexagram,0);assert.deepEqual(attacks,underhand?[[8+Math.floor(gain/4)]]:[]);
 assert.equal(me.this_card_chases,1);assert.equal(g.used_randomness,false);
 // The second use must not repeat the first-use grant.
 me.hexagram=1;const hp=me.hp,max=me.max_hp;g.trigger_card(id,0);assert.equal(me.hp,hp);assert.equal(me.max_hp,max);
 assert.equal(attacks.at(-1)[0],8+Math.floor(gain/4));scenarios++;
}
process.stdout.write(JSON.stringify({passed:true,scenarios,scope:'explicit software fixtures, not independent battle acceptance'}));
