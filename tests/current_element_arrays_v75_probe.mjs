import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {elementArraysFacts,registerElementArrays,installElementArrays,usesNewArrayFlag} from '../tools/current_element_arrays_v75.mjs';
import {registerVesselPhysique,installVesselPhysique} from '../tools/current_vessel_physique_v74r2.mjs';
import {createSeasonPassives} from '../tools/current_season_passives_v75.mjs';
import {installCurrentSeasonContext} from '../tools/current_season_context_v27.mjs';
import {installCurrentDelayedDamage} from '../tools/current_delayed_damage_v70.mjs';
import {installArrayFlag} from '../tools/current_element_flag_v75.mjs';
import {registerElementFlag} from '../tools/current_element_flag_v62r2.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerVesselPhysique(root,swogi);registerElementArrays(root,swogi);registerElementFlag(root,swogi);
const f=elementArraysFacts(root),names=[];
const scenario=(name,fn)=>{fn();names.push(name);};
function fresh(id='775012',order=[0,1]){
 const g=new GameState(undefined,undefined,'element-arrays-software');
 g.players.forEach((p,i)=>{p.hp=100;p.max_hp=150;p.cards=i===0?[id,'601011','601011']:['601011','601011','601011'];p.hand_count=0;p.post_deck_setup();});
 installCurrentDelayedDamage(g);installVesselPhysique(root,g,swogi,order);const e=installElementArrays(root,g,swogi,order),p=g.players[0];
 p.currently_triggering_card_idx=0;p.currently_playing_card_idx=0;p.currently_triggering_card_id=id;p.trigger_depth=1;
 return {g,e,p,q:g.players[1]};
}
for(const c of f.cards)scenario('body-and-continuous-'+c.raw_id,()=>{
 const {g,p,e}=fresh(c.runtime_id);g.executeCurrentElementArray(c.runtime_id);
 assert.equal(p.qi,c.config.anima);assert.equal(p.can_play[0],false);
 assert.equal(swogi[c.runtime_id].is_continuous,true);assert.equal(swogi[c.runtime_id].is_consumption,false);assert.equal(swogi[c.runtime_id].is_spirit_seal_or_formation,true);
 if(c.base_id===7000104){assert.equal(p.water_spirit_formation_stacks,1);assert.equal(p.activate_water_spirit_stacks,0);assert.equal(p.this_card_chases,1);}
 else{
  assert.equal(p.activate_wood_spirit_stacks,1);assert.equal(p.wood_thorn,c.config.level>=4?1:0);
  assert.equal(p.dream_wood_spirit_formation_attack_steal_hp_stacks,c.config.level<=4?c.config.otherParams[0]:0);
  assert.equal(p.convert_increase_atk_to_wood_thorn,c.config.level===5?4:0);assert.equal(p.max_hp,c.config.level===5?175:150);assert.equal(p.hp,100);
 }
 assert.equal(e.metadata().events[0].raw_card_id,c.raw_id);
});
scenario('realm4-counter-order',()=>{
 const {g}=fresh('775014'),seen=[],add=g.increase_idx_x_by_c.bind(g);
 g.increase_idx_x_by_c=(i,k,n)=>{if(['dream_wood_spirit_formation_attack_steal_hp_stacks','wood_thorn'].includes(k))seen.push(k);return add(i,k,n);};
 g.executeCurrentElementArray('775014');assert.deepEqual(seen,['dream_wood_spirit_formation_attack_steal_hp_stacks','wood_thorn']);
});
scenario('steal-before-shielded-attack-consume-before-hp',()=>{
 const {g,p,q}=fresh('775012');g.executeCurrentElementArray('775012');p.hp=50;q.def=100;
 const seen=[],loss=g.reduce_idx_hp.bind(g);g.reduce_idx_hp=(i,n,...a)=>{if(i===1)seen.push([n,p.dream_wood_spirit_formation_attack_steal_hp_stacks]);return loss(i,n,...a);};
 for(let i=0;i<5;i++)g.atk(3);
 assert.deepEqual(seen,[[1,3],[1,2],[1,1],[1,0]]);assert.equal(q.hp,96);assert.equal(q.def,85);assert.equal(p.hp,54);
});
scenario('wood-thorn-before-finite-steal',()=>{
 const {g,p,q}=fresh('775014');g.executeCurrentElementArray('775014');p.hp=50;q.def=100;
 const seen=[],loss=g.reduce_idx_hp.bind(g);g.reduce_idx_hp=(i,n,...a)=>{if(i===1)seen.push([n,p.dream_wood_spirit_formation_attack_steal_hp_stacks]);return loss(i,n,...a);};
 g.atk(3);assert.deepEqual(seen,[[1,5],[1,4]]);assert.equal(p.hp,52);assert.equal(q.hp,98);
});
scenario('conversion-cap-is-per-gain-not-consumed',()=>{
 const {g,p,q}=fresh('775015');g.executeCurrentElementArray('775015');
 g.increase_idx_x_by_c(0,'increase_atk',6);g.increase_idx_x_by_c(0,'increase_atk',3);
 assert.equal(p.increase_atk,2);assert.equal(p.wood_thorn,8);assert.equal(p.convert_increase_atk_to_wood_thorn,4);
 p.hp=50;q.def=100;g.atk(10);assert.equal(p.hp,58);assert.equal(q.hp,92);assert.equal(q.def,88);
});
scenario('7035-one-point-conversion-precedes646',()=>{
 const {g,p}=fresh('775015');createSeasonPassives(root,g,swogi,{players:[[7035],[]]});g.executeCurrentElementArray('775015');
 g.increase_idx_x_by_c(0,'increase_atk',6);assert.equal(p.increase_atk,1);assert.equal(p.wood_thorn,6);assert.equal(p.convert_increase_atk_to_wood_thorn,4);
 g.increase_idx_x_by_c(0,'increase_atk',0);assert.equal(p.wood_thorn,6);
});
for(const id of ['775001','775002','775003'])scenario('water-pre-card-reader-'+id,()=>{
 const {g,p,e}=fresh(id);p.water_spirit_formation_stacks=2;p.trigger_depth=0;g.trigger_card(id,0);
 const c=f.cards.find(c=>c.runtime_id===id),body=e.metadata().events[0];assert.equal(body.before.qi,2);assert.equal(body.after.qi,2+c.config.anima);assert.equal(p.water_spirit_formation_stacks,3);
});
for(const has of [false,true])scenario('23080-generating-formation-'+has,()=>{
 const {g,p,e}=fresh('775012');if(has)installCurrentSeasonContext(root,g,swogi,{players:[[23080],[]]},[0,1]);
 p.water_spirit_formation_stacks=2;p.trigger_depth=0;g.trigger_card('775012',0);
 assert.equal(e.metadata().events[0].before.qi,has?2:0);assert.equal(p.qi,has?3:1);
});
for(const c of f.cards)scenario('vessel-array-grade-'+c.raw_id,()=>{
 const {g,p,q}=fresh(c.runtime_id);p.spirit_fusion_pot_stacks=1;g.do_spirit_fusion_pot(0);
 assert.equal(p.spirit_fusion_pot_stacks,0);
 if(c.config.rarity>0){assert.equal(p.cards[0],f.extra_transform_cards[c.raw_id-10000].runtime_id);assert.equal(p.hp,100);}
 else{assert.equal(p.cards[0],c.runtime_id);assert.equal(p.hp,91);assert.equal(q.hp,109);}
});
for(const raw of [7040081,7020104])scenario('flag-first-hidden-array-'+raw,()=>{
 const {g,p,e}=fresh('762001');p.hand_count=2;const hands=[[raw,7000031],null];
 assert.equal(usesNewArrayFlag(root,{hands}),true);const flag=installArrayFlag(root,g,swogi,{hands});
 p.trigger_depth=0;g.trigger_card('762001',0);const event=flag.metadata().events[0];
 assert.equal(event.formation.raw,raw);assert.equal(event.flag_remains_playable,true);assert.equal(p.cards[0],'762001');assert.equal(e.metadata().events[0].trigger_depth,2);
 if(raw===7040081)assert.equal(p.max_hp,175);else assert.equal(p.water_spirit_formation_stacks,1);
});
scenario('flag-unknown-first-is-not-skipped',()=>{
 const {g,p}=fresh('762001');p.hand_count=2;const flag=installArrayFlag(root,g,swogi,{hands:[[7040074,7040081],null]});
 p.trigger_depth=0;assert.throws(()=>g.trigger_card('762001',0),/unmapped_first_formation/);assert.equal(p.convert_increase_atk_to_wood_thorn,0);assert.deepEqual(flag.metadata().events,[]);
});
scenario('no-new-effect-keeps-metadata-absent',()=>{assert.equal(fresh('601011').e.metadata(),null);});
process.stdout.write(JSON.stringify({passed:true,scenarios:names.length,names}));
