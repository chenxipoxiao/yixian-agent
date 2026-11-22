import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createSeasonPassives} from '../tools/current_season_passives_v55.mjs';
import {installTwinDependencies,registerTwinDependencies} from '../tools/current_twin_dependencies_v54.mjs';
import {installCarefreeTwin} from '../tools/current_carefree_twin_v54.mjs';
import {installCurrentQiPayment} from '../tools/current_qi_payment_v15.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));registerTwinDependencies(root,swogi);
const facts=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-twin-dependencies-v54.json')));
const rt=id=>facts.metadata[id].runtime_id,passed=[];
const scenario=(name,fn)=>{fn();passed.push(name);};
function fresh(raw=[[1000001,1000041,0],[0,0,0]],ids=[[7035,7050,7132],[]],order=[0,1]){
 const g=new GameState(undefined,undefined,'passive-software');
 g.players.forEach((p,i)=>{p.hp=100;p.max_hp=100;p.cards=raw[order[i]].map(rt);p.post_deck_setup();});
 const e=createSeasonPassives(root,g,swogi,{players:ids},order);e.installBoundary(7132);e.installBoundary(7050);return {g,e};
}
for(const n of [0,1,3,9])scenario('attack-gain-'+n,()=>{
 const {g,e}=fresh();g.increase_idx_x_by_c(0,'increase_atk',n);
 assert.equal(g.players[0].increase_atk,Math.max(0,n-1));assert.equal(g.players[0].wood_thorn,Number(n>0));
 assert.equal(e.metadata().events.length,Number(n>0));
});
scenario('gain-events-not-total-layers',()=>{
 const {g}=fresh();g.add_c_of_x(1,'increase_atk');g.add_c_of_x(1,'increase_atk');g.add_c_of_x(3,'increase_atk');
 assert.equal(g.players[0].wood_thorn,3);assert.equal(g.players[0].increase_atk,2);
});
scenario('conversion-before646',()=>{
 const {g}=fresh();g.players[0].convert_increase_atk_to_wood_thorn=2;
 g.add_c_of_x(4,'increase_atk');assert.equal(g.players[0].wood_thorn,3);assert.equal(g.players[0].increase_atk,1);
 g.add_c_of_x(1,'increase_atk');assert.equal(g.players[0].wood_thorn,4);assert.equal(g.players[0].increase_atk,1);
});
scenario('enemy-target-and-swapped-owner',()=>{
 const {g,e}=fresh(undefined,[[7035],[]],[1,0]);g.increase_idx_x_by_c(1,'increase_atk',3);
 assert.equal(g.players[1].wood_thorn,1);g.increase_idx_x_by_c(0,'increase_atk',3);assert.equal(g.players[0].wood_thorn,0);
 g.players.reverse();g.add_c_of_x(2,'increase_atk');assert.equal(g.players[0].wood_thorn,2);
 assert.deepEqual(e.metadata().events.map(e=>e.player_index),[0,0]);
});
scenario('negative-gain-rejected-atomically',()=>{
 const {g}=fresh();assert.throws(()=>g.add_c_of_x(-1,'increase_atk'),/invalid_attack_gain/);assert.equal(g.players[0].wood_thorn,0);
});
scenario('wood-thorn-before-attack-and-no-consumption',()=>{
 const {g}=fresh([[0,0,0],[0,0,0]],[[7035],[]]);g.players[0].hp=90;g.add_c_of_x(2,'increase_atk');
 g.play_card(rt(0),0);assert.equal(g.players[1].hp,95);assert.equal(g.players[0].hp,91);
 g.play_card(rt(0),1);assert.equal(g.players[1].hp,90);assert.equal(g.players[0].hp,92);assert.equal(g.players[0].wood_thorn,1);
});
scenario('wood-thorn-hp-loss-guard-before-main-attack',()=>{
 const {g}=fresh([[0,0,0],[0,0,0]],[[7035],[]]);g.players[0].hp=90;g.players[1].guard_up=1;g.add_c_of_x(2,'increase_atk');
 g.play_card(rt(0),0);assert.equal(g.players[1].guard_up,0);assert.equal(g.players[1].hp,96);assert.equal(g.players[0].hp,91);
});
scenario('wood-thorn-not-triggered-by-direct-damage',()=>{
 const {g}=fresh();g.players[0].hp=90;g.add_c_of_x(2,'increase_atk');g.deal_damage(3);
 assert.equal(g.players[0].hp,90);assert.equal(g.players[1].hp,97);assert.equal(g.players[0].wood_thorn,1);
});
scenario('water-from-cloud-and-later-owner-turn',()=>{
 const {g,e}=fresh(undefined,[[7050],[]]);assert.equal(g.is_cloud_sword(rt(1000001)),true);
 g.players[0].def=11;g.play_card(rt(1000001),0);assert.equal(g.players[0].moon_water_sword_formation_stacks,1);
 g.do_def_decay();assert.equal(g.players[0].def,11);assert.equal(g.players[0].moon_water_sword_formation_stacks,0);
 g.do_def_decay();assert.equal(g.players[0].def,5);assert.equal(e.metadata().events.filter(x=>x.phase==='owner_turn_def_decay').length,1);
});
scenario('water-consumes-even-with-zero-defence',()=>{
 const {g}=fresh(undefined,[[7050],[]]);g.play_card(rt(1000001),0);g.do_def_decay();
 assert.equal(g.players[0].moon_water_sword_formation_stacks,0);assert.equal(g.players[0].def,0);
});
scenario('water-coexists-with-native-formation-and-turtle',()=>{
 const {g}=fresh(undefined,[[7050],[]]);g.play_card(rt(1000041),1);g.play_card(rt(1000001),0);
 assert.equal(g.players[0].moon_water_sword_formation_stacks,4);g.players[0].black_earth_turtle_stacks=2;
 g.do_def_decay();assert.equal(g.players[0].moon_water_sword_formation_stacks,3);assert.equal(g.players[0].def,12);
});
scenario('noncloud-no-water-no-invented-chain',()=>{
 const {g,e}=fresh(undefined,[[7050],[]]);g.play_card(rt(0),2);
 assert.equal(g.players[0].moon_water_sword_formation_stacks,0);assert.equal(e.metadata().events.length,0);
});
scenario('formation-adds-sea-and-consumes-after-body',()=>{
 const {g,e}=fresh(undefined,[[7132],[]]);g.play_card(rt(1000041),1);
 assert.equal(g.players[0].def,12);assert.equal(g.players[0].cloud_sea,0);assert.equal(g.players[0].cloud_sword_chain_count,1);
 assert.deepEqual(e.metadata().events.map(x=>x.phase),['season_before_card_body','cloud_sea_consumed_after_card']);
});
scenario('cloud-never-consumes-sea-or-gains-extra-def',()=>{
 const {g}=fresh(undefined,[[7132],[]]);g.players[0].cloud_sea=2;g.play_card(rt(1000001),0);
 assert.equal(g.players[0].cloud_sea,2);assert.equal(g.players[0].def,0);assert.equal(g.players[0].cloud_sword_chain_count,1);
});
scenario('one-sea-per-noncloud-and-then-chain-breaks',()=>{
 const {g}=fresh(undefined,[[7132],[]]);g.players[0].cloud_sea=2;
 for(let i=0;i<2;i++)g.play_card(rt(0),2);
 assert.equal(g.players[0].def,4);assert.equal(g.players[0].cloud_sword_chain_count,2);assert.equal(g.players[0].cloud_sword_used_count,2);
 g.play_card(rt(0),2);assert.equal(g.players[0].cloud_sword_chain_count,0);assert.equal(g.players[0].def,4);
});
scenario('formation-classified-as-cloud-preserves-new-sea',()=>{
 const {g}=fresh(undefined,[[7050,7132],[]]);g.players[0].m_light_sword_stacks=2;
 g.play_card(rt(1000041),1);assert.equal(g.players[0].cloud_sea,1);assert.equal(g.players[0].def,10);
 assert.equal(g.players[0].moon_water_sword_formation_stacks,4);
});
scenario('temporary-card-uses-actual-identity',()=>{
 const {g,e}=fresh(undefined,[[7132],[]]);const native=g.just_do_the_card_and_nothing_else.bind(g);
 let called=false;g.just_do_the_card_and_nothing_else=function(card){if(!called){called=true;this.trigger_card(rt(1000041),0);}else return native(card);};
 g.play_card(rt(0),2);
 assert.ok(e.metadata().events.some(x=>x.trigger_depth===2&&x.card===rt(1000041)));
 assert.equal(g.players[0].def,12);assert.equal(g.players[0].cloud_sea,0);
});
scenario('repeated-execute-adds-and-spends-each-time',()=>{
 const raw=[[1000041,0,0],[0,0,0]],{g,e}=fresh(raw,[[7132],[]]);
 // A native repeat of the same effect traverses both before/after boundaries.
 g.play_card(rt(1000041),0);g.play_card(rt(1000041),0);
 assert.equal(g.players[0].def,24);assert.equal(e.metadata().events.length,4);
});
scenario('copy-identity-checked-after-transform',()=>{
 const raw=[[1000041,0,0],[0,0,0]],{g,e}=fresh(raw,[[7132],[]]);
 installTwinDependencies(root,g,swogi,{players:[true,false],raw_boards:raw},[0,1]);g.do_plant_start_permanent_buffs();
 g.do_continuous_tune(1);g.play_card(g.players[0].cards[1],1);assert.equal(g.players[0].def,12);
 assert.equal(e.metadata().events[0].card,rt(1000041));
});
scenario('failed-qi-payment-does-not-trigger-passive',()=>{
 const {g,e}=fresh([[1000029,0,0],[0,0,0]],[[7050,7132],[]]);installCurrentQiPayment(g);g.players[0].qi=0;g.sim_turn();
 assert.equal(e.metadata().events.length,0);assert.equal(g.players[0].qi,1);
});
scenario('both-owners-independent',()=>{
 const {g,e}=fresh(undefined,[[7050],[7050]]);g.play_card(rt(1000001),0);g.players.reverse();g.play_card(rt(1000001),0);
 assert.equal(g.players[0].moon_water_sword_formation_stacks,1);assert.equal(g.players[1].moon_water_sword_formation_stacks,1);
 assert.deepEqual(e.metadata().events.map(x=>x.player_index),[0,1]);
});
scenario('unknown-runtime-fails-closed',()=>{
 const {g}=fresh();assert.throws(()=>g.is_cloud_sword('unknown'),/unknown_card/);
});
for(const value of [null,{players:[[7035,7035],[]]},{players:[[7010],[]]},{players:[[],[]]},{players:[[7050],[]],outcome:1}])scenario('bad-ownership-'+JSON.stringify(value),()=>{
 const g=new GameState();assert.throws(()=>createSeasonPassives(root,g,swogi,value),/season_passives_unresolved/);
});
scenario('double-install-and-boundary-rejected',()=>{
 const {g,e}=fresh();assert.throws(()=>e.installBoundary(7050),/duplicate/);assert.throws(()=>createSeasonPassives(root,g,swogi,{players:[[7035],[]]}),/already_installed/);
});
console.log(JSON.stringify({passed:true,scenarios:passed.length,names:passed}));
