import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerDreamSwords,installDreamSwordObserver} from '../tools/current_dream_swords_v43.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const {installCurrentQiPayment}=await import('../tools/current_qi_payment_v15.mjs');
registerDreamSwords(root,swogi);let scenarios=0;
function fresh(cards=['601011','601011','601011']){
 const g=new GameState(undefined,undefined,'dream-swords-software');
 for(const p of g.players){p.character='sw3';p.hp=500;p.max_hp=500;p.max_physique=100;p.cards=[...cards];p.hand_count=0;}
 g.start_of_game_setup();return g;
}
function body(g,id){const p=g.players[0];p.currently_triggering_card_id=id;p.currently_triggering_card_idx=0;
 p.currently_playing_card_idx=0;p.trigger_depth=1;g.just_do_the_card_and_nothing_else(swogi[id]);}
// Ten actual runtime bodies, independent of stale declarative swogi actions.
for(let grade=1;grade<=5;grade++){
 const id='D1103'+grade,g=fresh([id,'601011','601011']),p=g.players[0];
 const m=installDreamSwordObserver(root,g,swogi);p.cloud_sword_chain_count=3;p.cloud_sword_used_count=7;
 body(g,id);assert.equal(g.players[1].hp,500-[6,8,8,4,4][grade-1]);
 assert.equal(p.cloud_sea,grade<4?1:2);assert.equal(p.sword_intent,[2,2,3,6,16][grade-1]);
 assert.equal(p.cloud_sword_used_count,7);assert.equal(p.cloud_sword_chain_count,3);
 assert.equal(m.metadata().events[0].raw_id,1000070+(grade-1)*10000);assert.ok(g.is_cloud_sword(id)&&g.is_sword(id));scenarios++;
}
for(let grade=1;grade<=5;grade++){
 const id='D1108'+grade,g=fresh([id,'601011','601011']),p=g.players[0];p.qi=7;
 body(g,id);assert.equal(g.players[1].hp,500-[3,5,5,5,10][grade-1]);
 assert.equal(p.qi,grade<4?7:0);assert.equal(p.sword_qi,grade<3?1:grade===3?2:9);
 assert.ok(g.is_spirit_sword(id)&&g.is_sword(id));scenarios++;
}
for(let grade=1;grade<=5;grade++){
 const id='D1103'+grade,g=fresh([id,'601011','601011']);body(g,id);
 assert.equal(g.players[0].sword_intent,grade===5?2:0);scenarios++;
}
// Grade5 emits2 then2*previous720; generic gain callbacks see both requests.
{
 const g=fresh(['D11035','601011','601011']),p=g.players[0];p.cloud_sword_used_count=3;
 const calls=[],add=g.increase_idx_x_by_c.bind(g);
 g.increase_idx_x_by_c=(idx,key,n)=>{if(key==='sword_intent')calls.push(n);return add(idx,key,n);};
 g.play_card('D11035',0);assert.deepEqual(calls,[2,6]);assert.equal(p.sword_intent,8);
 assert.equal(p.cloud_sword_used_count,4);assert.equal(p.cloud_sword_chain_count,1);
 g.play_card('601011',1);assert.equal(p.cloud_sea,1);assert.equal(p.cloud_sword_used_count,5);assert.equal(p.cloud_sword_chain_count,2);scenarios++;
}
// Owning any grade extends625 to ordinary swords before that Dharma is played.
for(let grade=1;grade<=5;grade++){
 const g=fresh(['111011','D1108'+grade,'601011']),p=g.players[0];p.sword_qi=4;
 const m=installDreamSwordObserver(root,g,swogi);g.play_card('111011',0);
 assert.equal(g.players[1].hp,490);assert.equal(p.sword_qi,4);
 assert.equal(m.metadata().events.length,1);assert.equal(m.metadata().events[0].requested_damage,4);scenarios++;
}
for(const [id,owned,expected] of [['111011',false,500],['111051',true,500],['D11081',false,496]]){
 const g=fresh([id,owned?'D11081':'601011','601011']);g.players[0].sword_qi=4;g.do_sword_qi(id);
 assert.equal(g.players[1].hp,expected);assert.equal(g.players[0].sword_qi,4);scenarios++;
}
//625 is ordinary damage, unaffected by sword intent, and can be blocked by defense.
{
 const g=fresh(['111011','D11081','601011']);g.players[0].sword_qi=4;g.players[0].sword_intent=30;
 g.players[1].def=2;g.do_sword_qi('111011');assert.equal(g.players[1].hp,498);assert.equal(g.players[1].def,0);
 assert.equal(g.players[0].sword_intent,30);assert.equal(g.players[0].sword_qi,4);scenarios++;
}
for(const value of [0,-1]){
 const g=fresh(['111011','D11081','601011']);g.players[0].sword_qi=value;g.do_sword_qi('111011');
 assert.equal(g.players[1].hp,500);scenarios++;
}
// A temporary/nested trigger executes the body but skips the passive zone.
{
 const g=fresh(['D11081','601011','601011']),p=g.players[0];p.trigger_depth=1;p.currently_playing_card_idx=0;p.sword_qi=4;
 const m=installDreamSwordObserver(root,g,swogi);g.trigger_card('D11081',0);
 assert.equal(g.players[1].hp,497);assert.equal(p.sword_qi,5);
 assert.deepEqual(m.metadata().events.map(e=>[e.kind,e.trigger_depth]),[['card_body',2]]);scenarios++;
}
// Payment consumes only a complete shortfall; otherwise gather and retain625.
const costCard='114061';
assert.equal(swogi[costCard].name,'Giant Kun Spirit Sword');assert.equal(swogi[costCard].qi_cost,3);
for(const [qi,swordQi,played,leftQi,leftSword] of [[1,5,true,0,3],[1,1,false,2,1],[3,5,true,0,5]]){
 const g=fresh([costCard,'601011','601011']),p=g.players[0];installCurrentQiPayment(g);p.max_chases=0;p.qi=qi;p.sword_qi=swordQi;
 g.sim_turn();assert.equal(p.next_card_index,played?1:0);assert.equal(p.qi,leftQi);assert.equal(p.sword_qi,leftSword);scenarios++;
}
{
 const g=fresh(),m=installDreamSwordObserver(root,g,swogi,[1,0]);assert.equal(m.metadata(),null);
 assert.throws(()=>installDreamSwordObserver(root,g,swogi),/already/);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios}));
