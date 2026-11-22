import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerDiligentChaseWind,installDiligent,diligentFacts} from '../tools/current_diligent_chasewind_v90r2.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const facts=diligentFacts(root),before=new Map(facts.cards.map(c=>[c.runtime_id,{...swogi[c.runtime_id]}]));
registerDiligentChaseWind(root,swogi);
for(const c of facts.cards){
 const {card_actions:a,...old}=before.get(c.runtime_id),{card_actions:b,...now}=swogi[c.runtime_id];
 assert.deepEqual(old,now);assert.notEqual(a,b);
}
let scenarios=0;
function fresh(id){
 const g=new GameState(undefined,undefined,'current-diligent-software');
 for(const p of g.players)Object.assign(p,{character:'sw3',hp:1000,max_hp:1000,qi:20,cards:[id,'111011','601011']});
 const observer=installDiligent(root,g,swogi);g.start_of_game_setup();g.players[0].currently_playing_card_idx=0;
 return {g,p:g.players[0],observer};
}
for(let grade=1;grade<=3;grade++)for(const prior of [0,4]){
 const id='11512'+grade,{g,p}=fresh(id);p.cloud_sword_chain_count=prior;p.cloud_sword_used_count=9;
 g.trigger_card(id,0);
 assert.equal(p.def,[2,8,12][grade-1]);assert.equal(p.cloud_sea,2);
 assert.equal(p.cloud_sword_chain_count,prior+[2,2,3][grade-1]);
 assert.equal(p.cloud_sword_used_count,9+[2,2,3][grade-1]);assert.equal(p.this_card_chases,1);scenarios++;
}
for(let grade=1;grade<=3;grade++)for(const qualified of [false,true]){
 const id='71407'+grade,{g,p,observer}=fresh(id),threshold=[85,80,75][grade-1];
 p.cultivation=threshold-(qualified?0:1);const enemyHp=g.players[1].hp;g.trigger_card(id,0);
 assert.equal(enemyHp-g.players[1].hp,[6,10,14][grade-1]);
 assert.equal(p.m_diligent_sword_stacks,qualified?2:1);assert.equal(p.this_card_chases,0);
 g.trigger_card('601011',2);assert.equal(p.m_diligent_sword_stacks,qualified?2:1);
 g.trigger_card('111011',1);assert.equal(p.m_diligent_sword_stacks,qualified?1:0);assert.equal(p.this_card_chases,1);
 assert.equal(observer.metadata().events.filter(e=>e.kind==='before_card_consume591_add315').length,1);scenarios++;
}
for(const guard of ['existing315','at_limit','flying_brush','entangle']){
 const {g,p}=fresh('714071');p.cultivation=85;g.trigger_card('714071',0);
 if(guard==='existing315'){p.this_card_chases=1;p.flying_brush_stacks=2;}
 if(guard==='at_limit'){p.chases=p.max_chases;p.flying_brush_stacks=2;}
 if(guard==='flying_brush')p.flying_brush_stacks=2;
 if(guard==='entangle')p.entangle=1;
 g.trigger_card('111011',1);
 const consumes=!['existing315','at_limit'].includes(guard);
 assert.equal(p.m_diligent_sword_stacks,consumes?1:2);
 if(guard!=='entangle')assert.equal(p.flying_brush_stacks,2);
 // Native chases counts accepted actions; entangle prevents the extra action
 // after591 was already consumed. It must not refund591.
 if(guard==='entangle'){g.process_this_card_chases();assert.equal(p.chases,0);assert.equal(p.entangle,0);assert.equal(p.m_diligent_sword_stacks,1);}
 scenarios++;
}
// An existing charge can apply before a second Diligent body replenishes it.
{
 const {g,p}=fresh('714071');p.cultivation=85;g.trigger_card('714071',0);g.trigger_card('714071',0);
 assert.equal(p.m_diligent_sword_stacks,3);assert.equal(p.this_card_chases,1);scenarios++;
}
// Raw19 and20019 currently share an alias. The exact-ID ultimate exception is
// deliberately unresolved when it matters; never infer it from the name.
{
 const {g,p}=fresh('714071');p.cultivation=85;g.trigger_card('714071',0);
 p.quench_of_sword_heart_ultimate_stacks=1;
 assert.throws(()=>g.trigger_card('611033',1),/ambiguous_exact_raw19/);scenarios++;
}
assert.throws(()=>registerDiligentChaseWind(root,swogi),/already_registered/);
process.stdout.write(JSON.stringify({passed:true,scenarios,metadata_preserved:6,
 scope:'Actual trigger, chase-payment, and nonfinite-state software checks; not replay acceptance'}));
