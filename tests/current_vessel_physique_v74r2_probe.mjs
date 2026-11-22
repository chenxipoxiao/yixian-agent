import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerVesselPhysique,installVesselPhysique,vesselPhysiqueFacts} from '../tools/current_vessel_physique_v74r2.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerVesselPhysique(root,swogi);const facts=vesselPhysiqueFacts(root),names=[];
const scenario=(name,fn)=>{fn();names.push(name);};
function fresh(id='774001',order=[0,1]){
 const g=new GameState(undefined,undefined,'vessel-physique-software');
 g.players.forEach(p=>{p.hp=100;p.max_hp=200;p.physique=20;p.max_physique=30;p.hand_count=1;p.cards=[id,'601011','601012'];p.post_deck_setup();});
 const e=installVesselPhysique(root,g,swogi,order),p=g.players[0];
 p.currently_triggering_card_idx=0;p.currently_playing_card_idx=0;p.currently_triggering_card_id=id;p.trigger_depth=1;
 return {g,e,p,q:g.players[1]};
}
for(const order of [[0,1],[1,0]])scenario('vessel-opening-repeat-'+order,()=>{
 const {g,e,q}=fresh('906071',order);g.do_opening(0);assert.equal(q.spirit_fusion_pot_stacks,2);
 g.do_opening(0);assert.equal(q.spirit_fusion_pot_stacks,4);assert.equal(e.metadata().events[0].player_index,order[0]);
 swogi['906071'].card_actions(g);assert.equal(q.spirit_fusion_pot_stacks,8);
});
scenario('vessel-absorb-order',()=>{
 const {g,p,q}=fresh('601011');p.spirit_fusion_pot_stacks=2;const seen=[];
 for(const key of ['reduce_idx_hp','reduce_idx_max_hp','increase_idx_max_hp','increase_idx_hp']){
  const fn=g[key].bind(g);g[key]=function(i,n,...args){seen.push([key,i,n]);return fn(i,n,...args);};
 }
 g.do_spirit_fusion_pot(0);
 assert.deepEqual(seen,[['reduce_idx_hp',0,9],['reduce_idx_max_hp',0,9],['increase_idx_max_hp',1,9],['increase_idx_hp',1,9]]);
 assert.equal(p.hp,91);assert.equal(q.hp,109);assert.equal(p.max_hp,191);assert.equal(q.max_hp,209);assert.equal(p.spirit_fusion_pot_stacks,1);
});
scenario('vessel-hidden-top-grade-downgrade',()=>{
 const {g,p,q}=fresh('774003');p.spirit_fusion_pot_stacks=1;g.do_spirit_fusion_pot(0);
 assert.equal(p.cards[0],'774002');assert.equal(p.hp,100);assert.equal(q.hp,100);assert.equal(p.spirit_fusion_pot_stacks,0);
});
scenario('vessel-dream-realm-is-not-rarity',()=>{
 const {g,p,q}=fresh('774025');p.spirit_fusion_pot_stacks=1;g.do_spirit_fusion_pot(0);
 assert.equal(p.cards[0],'774025');assert.equal(p.hp,91);assert.equal(q.hp,109);
});
scenario('vessel-unknown-identity-blocked-before-consume',()=>{
 const {g,p}=fresh();p.cards[0]='not-an-id';p.spirit_fusion_pot_stacks=1;
 assert.throws(()=>g.do_spirit_fusion_pot(0),/vessel_unknown_card/);assert.equal(p.spirit_fusion_pot_stacks,1);
});
for(const c of facts.cards.filter(c=>c.base_id===339))scenario('fist-physical-slots-and-per-hit-order-'+c.raw_id,()=>{
 const {g,p,e}=fresh(c.runtime_id);p.can_play[1]=false;const before=[];
 g.atk=n=>before.push([n,p.physique,p.agility]);g.executeCurrentVesselPhysique(c.runtime_id);
 assert.equal(before.length,c.config.attackCount+2);assert.deepEqual(before,before.map((_,i)=>[2,20+i,i]));
 assert.equal(p.physique,20+before.length);assert.equal(p.agility,before.length);assert.equal(e.metadata().events[0].normal_attack_count,2);
});
scenario('fist-count-snapshotted-before-hits',()=>{
 const {g,p}=fresh();let hits=0;g.atk=()=>{hits++;p.cards[1]='774011';};g.executeCurrentVesselPhysique('774001');assert.equal(hits,6);
});
for(const c of facts.cards.filter(c=>c.base_id===10000100))scenario('bones-exhaustion-and-callback-order-'+c.raw_id,()=>{
 const {g,p}=fresh(c.runtime_id);g.executeCurrentVesselPhysique(c.runtime_id);
 assert.equal(p.physique,21);assert.equal(p.agility,10);assert.equal(p.exercise_bones_stacks,c.config.otherParams[0]);
 const observed=[],gain=g.increase_idx_physique.bind(g);g.increase_idx_physique=(i,n)=>{observed.push(p.exercise_bones_stacks);return gain(i,n);};
 for(let n=c.config.otherParams[0];n>0;n--)assert.equal(g.do_exercise_bones(),3);
 assert.equal(g.do_exercise_bones(),0);assert.deepEqual(observed,Array.from({length:c.config.otherParams[0]},(_,i)=>c.config.otherParams[0]-1-i));
});
for(const c of facts.cards.filter(c=>c.base_id===10000073))scenario('dream-wave-realm-and-consumption-'+c.raw_id,()=>{
 const {g,p}=fresh(c.runtime_id);p.qi=3;g.executeCurrentVesselPhysique(c.runtime_id);
 assert.equal(p.qi,5);assert.equal(p.hp,100+c.config.otherParams[0]);assert.equal(p.agility,c.config.otherParams[1]+(c.config.level>=4?5:0));assert.equal(p.can_play[0],false);
});
scenario('dream-wave-reads-qi-after-heal-callback',()=>{
 const {g,p}=fresh('774024');p.qi=3;const heal=g.increase_idx_hp.bind(g);
 g.increase_idx_hp=(i,n)=>{heal(i,n);g.increase_idx_qi(i,2);};g.executeCurrentVesselPhysique('774024');assert.equal(p.agility,11);
});
scenario('all-alias-classifications',()=>{
 for(const c of facts.cards){assert.equal(swogi[c.runtime_id].is_consumption,c.config.cardType===1);assert.equal(swogi[c.runtime_id].is_continuous,c.config.cardType===2);assert.equal(swogi[c.runtime_id].is_add_physique,c.config.physique>0);}
});
scenario('nested-consumption-does-not-remove-actual-slot',()=>{
 const {g,p}=fresh('774024');p.trigger_depth=2;g.executeCurrentVesselPhysique('774024');assert.equal(p.can_play[0],true);assert.equal(p.qi,2);assert.equal(p.agility,6);
});
scenario('no-effects-no-audit-metadata',()=>{const {e}=fresh();assert.equal(e.metadata(),null);});
process.stdout.write(JSON.stringify({passed:true,scenarios:names.length,names}));
