import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installSeasonWater} from '../tools/current_season_water_v76.mjs';
import {installCurrentDelayedEffects} from '../tools/current_delayed_effects_v76.mjs';
import {installCurrentQiPayment} from '../tools/current_qi_payment_v76.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const names=[],scenario=(name,fn)=>{fn();names.push(name);};
function fresh(ids=[7032],order=[0,1],round=12,initial=undefined){
 const g=new GameState(undefined,undefined,'season-water-software');
 g.players.forEach(p=>{p.hp=100;p.max_hp=150;p.cards=['601011','601011','601011'];p.hand_count=0;p.round_number=round;p.post_deck_setup();});
 installCurrentDelayedEffects(root,g,swogi);installCurrentQiPayment(g);
 const owners=[[],[]];owners[order[0]]=ids;
 const e=installSeasonWater(root,g,swogi,{players:owners},order,initial),p=g.players[0],q=g.players[1];
 g.current_water_selected_card('601011',0);return {g,e,p,q};
}
for(const round of [1,12,13,15])for(const order of [[0,1],[1,0]])scenario('3012-round-seat-'+round+'-'+order[0],()=>{
 const {g,e,p}=fresh([3012],order,round);p.dream_cloud_sword_softheart_gain_def=3;
 const events=[],increase=g.increase_idx_def.bind(g);g.increase_idx_def=(i,n)=>{events.push(n);return increase(i,n);};
 g.do_dream_cloud_sword_softheart_gain_def();assert.equal(events.at(-1),round>=13?4:2);
 const event=e.metadata().events.at(-1);assert.equal(event.player_index,order[0]);assert.equal(event.after-event.before,round>=13?4:2);
});
scenario('3012-normal-defense-callback-and-ordered-hook',()=>{
 const {g,p,e}=fresh([3012]);p.prevent_gain_def_stacks=1;g.do_dream_cloud_sword_softheart_gain_def();assert.equal(p.def,0);assert.equal(e.metadata().events[0].requested,2);
 p.prevent_gain_def_stacks=0;const observed=[];g.do_wood_spirit_all_things_grow=()=>observed.push(e.metadata().events.length);g.sim_turn();assert.deepEqual(observed,[2]);
});
scenario('7032-post-shield-not-base-multiplier',()=>{
 const {g,p,q,e}=fresh();p.force_of_water=5;q.def=3;g.do_force_of_water();assert.equal(q.hp,97);assert.equal(q.def,0);
 const s=e.metadata().events.find(x=>x.kind==='576_post_shield_wound_scale');assert.deepEqual([s.damage_before,s.damage_after],[2,3]);
});
scenario('7032-penetrate-wound-and-separate-display',()=>{
 const {g,p,q,e}=fresh();p.force_of_water=5;p.penetrate=3;q.def=3;q.wound=2;g.do_force_of_water();assert.equal(q.hp,90);assert.equal(p.penetrate,0);
 const s=e.metadata().events.find(x=>x.kind==='576_post_shield_wound_scale');assert.deepEqual([s.damage_before,s.damage_after,s.fengrui_before,s.fengrui_after],[7,10,3,4]);
});
scenario('7032-tripod-precedes576',()=>{
 const {g,p,q,e}=fresh();p.force_of_water=5;p.penetrate=3;p.metal_spirit_giant_tripod_stacks=1;q.def=3;q.wound=2;g.do_force_of_water();assert.equal(q.hp,79);
 const s=e.metadata().events.find(x=>x.kind==='576_post_shield_wound_scale');assert.deepEqual([s.damage_before,s.damage_after,s.fengrui_before,s.fengrui_after],[14,21,6,9]);
});
scenario('7032-guard-block-skips-wounded-scaling',()=>{
 const {g,p,q,e}=fresh();p.force_of_water=5;p.penetrate=3;q.guard_up=1;g.do_force_of_water();assert.equal(q.hp,100);assert.equal(p.penetrate,3);assert.equal(q.guard_up,0);assert.equal(e.metadata().events.filter(x=>x.kind==='576_post_shield_wound_scale').length,0);
});
scenario('7032-ignore-guard-is-consumed-before-scaling',()=>{
 const {g,p,q}=fresh();p.force_of_water=5;p.ignore_guard_up=1;p.penetrate=3;q.guard_up=1;g.do_force_of_water();assert.equal(q.hp,88);assert.equal(p.ignore_guard_up,0);assert.equal(q.guard_up,1);
});
scenario('7032-reflection-stays-nonattack',()=>{
 const {g,p,q,e}=fresh();p.force_of_water=5;q.repel_citta_dharma_stacks=2;g.do_force_of_water();assert.equal(q.hp,93);assert.equal(p.hp,98);assert.equal(e.metadata().events.filter(x=>x.kind==='576_post_shield_wound_scale').length,1);
});
scenario('7032-billows-count-snapshot-rereads-water',()=>{
 const {g,p,q,e}=fresh();p.force_of_water=5;p.m_water_spirit_billows_stacks=2;
 const loss=g.reduce_idx_hp.bind(g);let hits=0;g.reduce_idx_hp=(i,n,...a)=>{const value=loss(i,n,...a);if(i===1&&n>0&&++hits===1){p.force_of_water=9;p.m_water_spirit_billows_stacks=0;}return value;};
 g.do_force_of_water();assert.equal(q.hp,80);assert.deepEqual(e.metadata().events.filter(x=>x.kind==='7032_add382_then576').map(x=>x.base_attack),[5,9]);
});
scenario('7032-billows-late-consumption-no-early-death',()=>{
 const {g,p,q,e}=fresh();p.force_of_water=5;p.m_water_spirit_billows_stacks=2;q.hp=1;g.do_force_of_water();assert.equal(q.hp,-13);assert.equal(p.m_water_spirit_billows_stacks,2);
 g.current_water_blade_cleanup();assert.equal(p.m_water_spirit_billows_stacks,1);assert.equal(e.metadata().events.at(-1).kind,'484_late_turn_cleanup');
});
scenario('7032-no-water-but-late-billows-cleanup',()=>{
 const {g,p,q,e}=fresh();p.m_water_spirit_billows_stacks=1;g.do_force_of_water();assert.equal(q.hp,100);assert.deepEqual(e.metadata().events,[]);g.current_water_blade_cleanup();assert.equal(p.m_water_spirit_billows_stacks,0);
});
scenario('7032-selected-star-slot-and-context-restoration',()=>{
 const {g,p,q}=fresh();p.force_of_water=5;p.star_power=3;p.is_star_point[0]=true;p.currently_playing_card_idx=undefined;p.currently_triggering_card_id=undefined;p.currently_triggering_card_idx=undefined;
 g.do_force_of_water();assert.equal(q.hp,88);assert.equal(p.currently_playing_card_idx,undefined);assert.equal(p.currently_triggering_card_id,undefined);assert.equal(g.current_water_blade_active(p),false);
});
scenario('7032-card-selection-retained-on-qi-failure',()=>{
 const {g,p,q,e}=fresh();const costly=Object.keys(swogi).find(k=>swogi[k].qi_cost>=3&&!swogi[k].opening&&!swogi[k].decrease_qi_cost_by_x&&!swogi[k].water_spirit_cost_0_qi&&!swogi[k].cloud_hit_cost_0_qi);
 assert.ok(costly);p.cards=[costly,costly,costly];p.force_of_water=5;p.star_power=3;p.is_star_point=[true,true,true];p.qi=0;g.sim_turn();
 const event=e.metadata().events.find(x=>x.kind==='7032_add382_then576');assert.equal(event.card,costly);assert.equal(q.hp,88);assert.equal(p.qi,1);
});
scenario('7032-does-not-trigger-returning-edge-card-bonus',()=>{
 const {g,p,q}=fresh();const edge=Object.keys(swogi).find(k=>swogi[k].name==='Metal Spirit - Returning Edge');assert.ok(edge);p.cards[0]=edge;g.current_water_selected_card(edge,0);
 p.activate_metal_spirit_stacks=1;p.force_of_water=5;p.penetrate=3;g.do_force_of_water();assert.equal(p.penetrate,0);assert.equal(q.hp,88);
});
scenario('7032-normal-attacks-do-not-reuse576',()=>{
 const {g,p,q}=fresh();p.force_of_water=5;g.do_force_of_water();p.currently_triggering_card_id='601011';p.currently_triggering_card_idx=0;p.currently_playing_card_idx=0;g.atk(5);assert.equal(q.hp,88);
});
scenario('7032-error-cleans-temporary-context',()=>{
 const {g,p}=fresh();p.force_of_water=5;g.atk=()=>{throw new Error('test-handler-failed');};assert.throws(()=>g.do_force_of_water(),/test-handler-failed/);assert.equal(g.current_water_blade_active(p),false);assert.equal(p.currently_triggering_card_id,undefined);
});
scenario('7032-float32-floor-and-overflow-rejection',()=>{
 const {g,p}=fresh();p.force_of_water=5;g.atk=()=>{assert.equal(g.current_water_blade_damage(p,16777217,3),25165824);assert.throws(()=>g.current_water_blade_damage(p,2147483647,0),/scaled_damage_outside_int32/);};g.do_force_of_water();
});
scenario('7032-ambiguous-zero-or-negative-start-refused',()=>{
 for(const n of [0,-1])for(const field of ['force_of_water','m_water_spirit_billows_stacks'])assert.throws(()=>fresh([7032],[0,1],12,[{[field]:n},{}]),/initial_presence_unresolved/);
});
scenario('unrelated-owner-keeps-native-water',()=>{
 const {g,p,q}=fresh([3012]);p.force_of_water=5;q.def=3;g.do_force_of_water();assert.equal(q.hp,98);
});
process.stdout.write(JSON.stringify({passed:true,scenarios:names.length,names}));
