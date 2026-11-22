import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createRegenOpening} from '../tools/current_regen_opening_v73.mjs';
import {createPalmVigor} from '../tools/current_palm_vigor_v72.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const names=[],scenario=(name,fn)=>{fn();names.push(name);};
function fresh(entries=[[{strategy_id:7135,enabled:true}],[]],order=[0,1]){
 const g=new GameState(undefined,undefined,'regen-opening-software');
 g.players.forEach(p=>{p.hp=100;p.max_hp=200;p.hand_count=1;p.cards=['601011','601011','601011'];p.post_deck_setup();});
 const e=createRegenOpening(root,g,{players:entries},order);
 e.installOpening(7135);e.installOpening(7103);return {g,e};
}
for(const hp of [1,9,10,49,100,101,199])scenario('7103-current-hp-floor-'+hp,()=>{
 const {g,e}=fresh([[{strategy_id:7103}],[]]);g.players[0].hp=hp;g.do_plant_start_permanent_buffs();
 const amount=Math.trunc(hp/10);assert.equal(g.players[0].hp,hp+amount);assert.equal(g.players[0].max_hp,200+amount);assert.equal(e.metadata().events[0].requested,amount);
});
scenario('7103-max-first-and-normal-appetite',()=>{
 const {g}=fresh([[{strategy_id:7103}],[]]);g.players[0].appetite=3;g.do_plant_start_permanent_buffs();
 assert.equal(g.players[0].max_hp,210);assert.equal(g.players[0].hp,113);
});
scenario('7103-heal-prevention-keeps-max-gain',()=>{
 const {g}=fresh([[{strategy_id:7103}],[]]);g.players[0].prevent_gain_hp_stacks=1;g.do_plant_start_permanent_buffs();
 assert.equal(g.players[0].max_hp,210);assert.equal(g.players[0].hp,100);
});
scenario('7103-before15018-and-plants',()=>{
 const g=new GameState(undefined,undefined,'regen-opening-software');
 g.players.forEach(p=>{p.hp=100;p.max_hp=200;p.hand_count=1;p.cards=['601011','601011','601011'];p.post_deck_setup();});
 const e=createRegenOpening(root,g,{players:[[{strategy_id:7103}],[]]});
 const palm=createPalmVigor(root,g,swogi,{players:[[15018],[]]});palm.installOpening();e.installOpening(7135);e.installOpening(7103);
 g.players[0].origin_herb_stacks=10;g.do_plant_start_permanent_buffs();
 assert.equal(e.metadata().events[0].after.hp,110);assert.equal(palm.metadata().events[0].before.hp,110);assert.equal(g.players[0].hp,133);
});
scenario('7135-both-player-regeneration',()=>{
 const {g,e}=fresh();g.do_plant_start_permanent_buffs();
 for(let i=0;i<2;i++){g.players[0].regen=3;g.do_regen();assert.equal(g.players[0].hp,106);g.players.reverse();}
 assert.deepEqual(e.metadata().events[0].target_order,[0,1]);assert.equal(e.metadata().events.filter(x=>x.phase==='turn_start_regeneration').length,2);
});
scenario('7135-before-opening-no-effect',()=>{
 const {g}=fresh();g.players[0].regen=3;g.do_regen();assert.equal(g.players[0].hp,103);
});
scenario('7135-disabled',()=>{
 const {g,e}=fresh([[{strategy_id:7135,enabled:false}],[]]);g.do_plant_start_permanent_buffs();g.players[0].regen=3;g.do_regen();
 assert.equal(g.players[0].hp,103);assert.equal(e.metadata().events.length,1);assert.deepEqual(e.metadata().events[0].after,[0,0]);
});
scenario('7135-two-owners-presence-not-fourfold',()=>{
 const {g,e}=fresh([[{strategy_id:7135,enabled:true}],[{strategy_id:7135,enabled:true}]]);
 g.do_plant_start_permanent_buffs();g.players.reverse();g.do_plant_start_permanent_buffs();g.players[0].regen=3;g.do_regen();
 assert.equal(g.players[0].hp,106);assert.equal(e.metadata().events.at(-1).marker477,2);
});
scenario('7135-swapped-initiative',()=>{
 const {g,e}=fresh([[{strategy_id:7135,enabled:true}],[]],[1,0]);g.do_plant_start_permanent_buffs();g.players.reverse();g.do_plant_start_permanent_buffs();
 assert.deepEqual(e.metadata().events[0].target_order,[0,1]);g.players.reverse();g.players[0].regen=3;g.do_regen();assert.equal(g.players[0].hp,106);assert.equal(e.metadata().events.at(-1).player_index,1);
});
scenario('7135-does-not-multiply-other-heals-or-appetite',()=>{
 const {g}=fresh();g.do_plant_start_permanent_buffs();g.players[0].regen=3;g.players[0].appetite=2;
 g.do_regen();assert.equal(g.players[0].hp,108);g.heal(3);assert.equal(g.players[0].hp,113);
 g.players[0].regen_tune_stacks=4;g.do_regen_tune();assert.equal(g.players[0].hp,119);
});
scenario('7135-regeneration-prevention-and-cap',()=>{
 const {g}=fresh();g.do_plant_start_permanent_buffs();g.players[0].regen=3;g.players[0].prevent_gain_hp_stacks=1;g.do_regen();assert.equal(g.players[0].hp,100);
 g.players[0].prevent_gain_hp_stacks=0;g.players[0].hp=198;g.do_regen();assert.equal(g.players[0].hp,200);
});
scenario('7135-injury-start-only',()=>{
 const {g,e}=fresh();g.do_plant_start_permanent_buffs();g.players[0].internal_injury=3;
 g.do_internal_injury(0,true);assert.equal(g.players[0].hp,94);g.do_internal_injury(0,false);assert.equal(g.players[0].hp,91);
 assert.equal(e.metadata().events.filter(x=>x.phase==='turn_start_internal_injury').length,1);
});
scenario('7135-injury-other-seat',()=>{
 const {g,e}=fresh();g.do_plant_start_permanent_buffs();g.players[1].internal_injury=3;g.do_internal_injury(1,true);
 assert.equal(g.players[1].hp,94);assert.equal(e.metadata().events.at(-1).player_index,1);
});
scenario('7135-repeat-loop-and-consumption',()=>{
 const {g,e}=fresh();g.do_plant_start_permanent_buffs();g.players[0].internal_injury=3;g.players[0].m_endless_entanglement_stacks=2;
 g.do_internal_injury(0,true);assert.equal(g.players[0].hp,82);assert.equal(g.players[0].m_endless_entanglement_stacks,0);
 assert.equal(e.metadata().events.filter(x=>x.phase==='turn_start_internal_injury').length,3);
});
scenario('7135-nested-damage-not-multiplied',()=>{
 const {g}=fresh();g.do_plant_start_permanent_buffs();g.players[0].internal_injury=3;
 const previous=g.reduce_idx_hp;let nested=false;
 g.reduce_idx_hp=function(idx,amt,...rest){const result=previous.call(this,idx,amt,...rest);if(!nested){nested=true;this.reduce_idx_hp(idx,1);}return result;};
 g.do_internal_injury(0,true);assert.equal(g.players[0].hp,93);
});
scenario('7135-zero-buffs-no-calls',()=>{
 const {g,e}=fresh();g.do_plant_start_permanent_buffs();g.do_regen();g.do_internal_injury(0,true);assert.equal(e.metadata().events.length,1);
});
scenario('7135-no-selected-resonance',()=>{
 const {g}=fresh();g.do_plant_start_permanent_buffs();g.players[0].internal_injury=3;g.players[0].resonance_indomitable_will_stacks=1;
 assert.throws(()=>g.do_internal_injury(0,true),/selected_resonance/);assert.equal(g.players[0].hp,100);
});
scenario('7135-overflow-blocked',()=>{
 const {g}=fresh();g.do_plant_start_permanent_buffs();g.players[0].regen=2147483647;
 assert.throws(()=>g.do_regen(),/overflow/);g.players[0].internal_injury=2147483647;assert.throws(()=>g.do_internal_injury(0,true),/overflow/);
});
scenario('opening-repeated-blocked',()=>{
 const {g}=fresh();g.do_plant_start_permanent_buffs();assert.throws(()=>g.do_plant_start_permanent_buffs(),/opening_repeated/);
});
scenario('unknown-or-missing-switch-blocked',()=>{
 for(const value of [{players:[[{strategy_id:7135}],[]]},{players:[[{strategy_id:7135,enabled:0}],[]]},{players:[[{strategy_id:7062}],[]]}]){
  const g=new GameState();assert.throws(()=>createRegenOpening(root,g,value),/explicit_ownership/);
 }
});
scenario('exception-restores-hp-callback',()=>{
 const {g}=fresh();g.do_plant_start_permanent_buffs();g.players[0].internal_injury=3;
 const bad=()=>{throw new Error('fixture-callback');};g.reduce_idx_hp=bad;
 assert.throws(()=>g.do_internal_injury(0,true),/fixture-callback/);assert.equal(g.reduce_idx_hp,bad);
});
console.log(JSON.stringify({passed:true,scenarios:names.length,names,real_replay_calibration:false}));
