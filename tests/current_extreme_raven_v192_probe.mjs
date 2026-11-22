import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerExtremeRaven192,installExtremeRaven192} from '../tools/current_extreme_raven_v192.mjs';
import {installSeasonPrimitives} from '../tools/current_season_primitives_v163.mjs';
import {installCurrentQiPayment} from '../tools/current_qi_payment_v124.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerExtremeRaven192(root,swogi);let scenarios=0;
function fresh(grade=1){
 const g=new GameState(undefined,undefined,'raven-software-boundaries');
 for(const p of g.players){p.character='he1';p.hp=1000;p.max_hp=1000;p.cards=['601011','601011'];p.max_physique=100;}
 g.players[0].cards=['99209'+grade,'601011'];
 installCurrentQiPayment(g);installSeasonPrimitives(g);
 const ext=installExtremeRaven192(root,g,swogi);g.start_of_game_setup();
 return {g,p:g.players[0],q:g.players[1],ext};
}
for(let grade=1;grade<=3;grade++)for(const qi of [0,2,11]){
 const {g,p,q,ext}=fresh(grade);p.qi=qi;g.play_card(p.cards[0],0);
 assert.equal(q.hp,994);assert.equal(p.qi,qi+grade);assert.equal(p.def,4*(qi+grade));
 assert.equal(p.this_card_chases,0);assert.equal(p.cloud_sword_chain_count,0);
 assert.equal(ext.metadata().events.length,1);scenarios++;
}
for(const blocked of ['defense','guard']){
 const {g,p,q}=fresh(3);if(blocked==='defense')q.def=20;else q.guard_up=1;
 g.play_card(p.cards[0],0);assert.equal(q.hp,1000);assert.equal(p.qi,3);assert.equal(p.def,12);scenarios++;
}
// The card reads qi after both the attack and qi-gain callbacks, not a cached value.
{const {g,p,ext}=fresh(2);p.qi=5;const order=[];
 const atk=g.atk.bind(g),gain=g.increase_idx_qi.bind(g),def=g.increase_idx_def.bind(g);
 g.atk=n=>{order.push('attack');atk(n);p.qi-=3;};
 g.increase_idx_qi=(i,n)=>{order.push('qi');gain(i,n);p.qi+=7;};
 g.increase_idx_def=(i,n)=>{order.push('defense');return def(i,n);};
 g.play_card(p.cards[0],0);assert.deepEqual(order,['attack','qi','defense']);
 assert.equal(p.qi,11);assert.equal(p.def,44);assert.equal(ext.metadata().events[0].qi_after_attack,2);scenarios++;
}
for(const afterGain of [0,-1,-20]){
 const {g,p}=fresh(1);const gain=g.increase_idx_qi.bind(g);let defCalls=0;
 g.increase_idx_qi=(i,n)=>{gain(i,n);p.qi=afterGain;};
 g.increase_idx_def=()=>{defCalls++;};g.play_card(p.cards[0],0);
 assert.equal(defCalls,0);assert.equal(p.def,0);scenarios++;
}
// Actual engine classification consumers recognize the new sword identity.
{const {g,p}=fresh(1);assert.equal(g.is_spirit_sword(p.cards[0]),true);
 assert.equal(swogi[p.cards[0]].is_sword,true);assert.equal(swogi[p.cards[0]].is_add_qi,true);
 assert.equal(swogi[p.cards[0]].is_cloud_sword,false);
 p.resonance_inheritance_of_spirit_sword_stacks=1;
 g.do_resonance_inheritance_of_spirit_sword(p.cards[0]);
 assert.equal(p.qi,2);assert.equal(p.resonance_inheritance_of_spirit_sword_stacks,0);scenarios++;
}
{const {g,p,ext}=fresh();g.play_card('601011',1);assert.equal(ext.metadata(),null);scenarios++;}
{const {g,p}=fresh();p.currently_triggering_card_id='992092';
 assert.throws(()=>g.executeExtremeRaven192('992091'),/card_identity/);scenarios++;}
{const {g,p}=fresh();p.qi=536870911;assert.throws(()=>g.play_card(p.cards[0],0),/integer_range/);scenarios++;}
console.log(JSON.stringify({passed:true,scenarios,scope:'software timing/classification boundaries; not independent replay acceptance'}));
