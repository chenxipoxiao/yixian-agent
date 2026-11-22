import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createExorcismQueue} from '../tools/current_exorcism_queue_v114.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const facts=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-debuff-parameters-v87r2.json')));
let scenarios=0;
function fresh(){
 const g=new GameState(undefined,undefined,'exorcism-software');
 for(const p of g.players){p.character='he1';p.hp=80;p.max_hp=120;p.max_physique=100;p.physique=20;p.cards=['601011','601011','601011'];}
 g.start_of_game_setup();const p=g.players[0];p.currently_triggering_card_idx=0;p.currently_triggering_card_id='601011';p.trigger_depth=1;return g;
}
const slots=order=>({players:order[0]===0?[[{strategy_id:13002,slot:0}],[]]:[[],[{strategy_id:13002,slot:0}]]});
const install=(g,stream,order=[0,1])=>createExorcismQueue(swogi,g,stream,order,facts,slots(order));
const play=g=>g.consume_exorcism_engraving_v114(0,2,4);
function body(g,id){g.players[0].currently_triggering_card_id=id;g.just_do_the_card_and_nothing_else(swogi[id]);}
for(const order of [[0,1],[1,0]]){
 const g=fresh(),q=install(g,[-1,-1,-1,-1],order);play(g);q.verifyTerminal();
 assert.equal(g.players[0].hp,88);assert.equal(q.metadata().consumed,4);
 assert(q.metadata().events.every(e=>e.player_index===order[0]));
 assert.throws(()=>play(g),/engraving_already_used/);scenarios++;
}
// Removal callbacks complete before the remaining no-op healing; card readers
// then continue the same queue rather than opening a second stream.
{
 const g=fresh(),p=g.players[0];p.styx=1;p.internal_injury=5;
 const q=install(g,[367,100,-1,-1,100,100]);play(g);
 assert.equal(p.hp,81);assert.equal(p.internal_injury,4);
 body(g,'143021');body(g,'645021');q.verifyTerminal();
 assert.equal(q.metadata().consumed,6);
 assert.deepEqual(q.metadata().events.filter(e=>Object.hasOwn(e,'queue_index')).map(e=>e.kind),
  ['engraving_13002','engraving_13002','engraving_13002','engraving_13002','crash_truncate','demon_breaking_palm']);
 assert.equal(p.internal_injury,2);scenarios++;
}
for(const kind of ['unknown','absent','underflow','leftover','temporary','slot','other_rng']){
 const g=fresh(),stream=kind==='unknown'?[999,-1,-1,-1]:kind==='absent'?[100,-1,-1,-1]:kind==='underflow'?[-1]:kind==='leftover'?[-1,-1,-1,-1,-1]:[-1,-1,-1,-1];
 const q=install(g,stream);
 if(kind==='unknown')assert.throws(()=>play(g),/unknown_buff_id/);
 else if(kind==='absent')assert.throws(()=>play(g),/selected_debuff_not_present/);
 else if(kind==='underflow')assert.throws(()=>play(g),/parameter_underflow/);
 else if(kind==='leftover'){play(g);assert.throws(()=>q.verifyTerminal(),/unused_parameters/);}
 else if(kind==='temporary'){g.players[0].trigger_depth=2;assert.throws(()=>play(g),/engraving_slot_or_temporary/);assert.equal(q.metadata().consumed,0);}
 else if(kind==='slot')assert.throws(()=>g.consume_exorcism_engraving_v114(1,2,4),/engraving_slot_or_temporary/);
 else assert.throws(()=>g.rand_range(0,1),/unsupported_consumer/);
 scenarios++;
}
for(const values of [[],[true],[-2],[2147483648]]){assert.throws(()=>install(fresh(),values),/invalid_stream/);scenarios++;}
console.log(JSON.stringify({passed:true,scenarios}));
