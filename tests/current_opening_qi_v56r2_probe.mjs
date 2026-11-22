import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createOpeningQi} from '../tools/current_opening_qi_v56.mjs';
import {installCurrentStartStates} from '../tools/current_start_states_v7.mjs';
import {createSeasonPassives} from '../tools/current_season_passives_v55.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const facts=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-start-states-v7.json')));
const passed=[];const scenario=(name,fn)=>{fn();passed.push(name);};
function fresh(ids=[[7005,7059,7109],[]],order=[0,1],open=true){
 const g=new GameState(undefined,undefined,'opening-qi-software');
 g.players.forEach(p=>{p.hp=100;p.max_hp=100;p.cards=['601011','601011','601011'];p.post_deck_setup();});
 const e=createOpeningQi(root,g,{players:ids},order);installCurrentStartStates(root,g);
 e.installBoundary(7109);e.installBoundary(7059);e.installBoundary(7005);
 if(open)g.do_plant_start_permanent_buffs();return {g,e};
}
scenario('startup-chain-and-cumulative-counter-once',()=>{
 const {g}=fresh();const p=g.players[0];assert.equal(p.cloud_sword_chain_count,1);assert.equal(p.cloud_sword_used_count,1);assert.equal(p.cloud_sea,2);
 g.do_plant_start_permanent_buffs();assert.equal(p.cloud_sword_used_count,1);assert.equal(p.cloud_sea,2);
});
scenario('sea-preserves-next-two-noncloud-uses',()=>{
 const {g}=fresh([[7005],[]]);const p=g.players[0];
 g.play_card('601011',0);assert.equal(p.cloud_sword_chain_count,2);assert.equal(p.cloud_sea,1);
 g.play_card('601011',1);assert.equal(p.cloud_sword_chain_count,3);assert.equal(p.cloud_sword_used_count,3);assert.equal(p.cloud_sea,0);
 g.play_card('601011',2);assert.equal(p.cloud_sword_chain_count,0);assert.equal(p.cloud_sword_used_count,3);
});
scenario('sea-consumption-combines-with7132',()=>{
 const {g}=fresh([[7005],[]]);const e=createSeasonPassives(root,g,swogi,{players:[[7132],[]]});e.installBoundary(7132);e.installBoundary(7050);
 g.play_card('601011',0);g.play_card('601011',1);assert.equal(g.players[0].def,4);assert.equal(g.players[0].cloud_sea,0);
});
scenario('no-qi-reward-before-own-startup',()=>{
 const {g,e}=fresh(undefined,undefined,false);g.increase_idx_qi(0,2);assert.equal(g.players[0].max_hp,100);assert.equal(g.players[0].agility,0);
 assert.equal(e.metadata().events.length,0);g.do_plant_start_permanent_buffs();g.increase_idx_qi(0,1);assert.equal(g.players[0].agility,5);assert.equal(g.players[0].max_hp,104);
});
scenario('zero-and-spending-do-not-consume-rewards',()=>{
 const {g,e}=fresh();g.increase_idx_qi(0,0);g.players[0].qi=4;g.reduce_idx_qi(0,2);
 const s=e.metadata().remaining[0];assert.equal(s.wine,3);assert.equal(s.wings,5);
});
for(const amount of [1,3,9])scenario('first-positive-qi-'+amount,()=>{
 const {g,e}=fresh();g.increase_idx_qi(0,amount);g.increase_idx_qi(0,amount);
 assert.equal(g.players[0].agility,5);assert.equal(g.players[0].max_hp,108);assert.equal(g.players[0].qi,2*amount);assert.equal(e.metadata().remaining[0].wine,1);
});
scenario('wine-three-events-not-three-qi',()=>{
 const {g}=fresh();for(const amount of [8,1,7,5])g.increase_idx_qi(0,amount);
 assert.equal(g.players[0].max_hp,112);assert.equal(g.players[0].hp,112);assert.equal(g.players[0].agility,5);
});
scenario('stillness-then-wine-then-forging-then-wings',()=>{
 const {g}=fresh();const p=g.players[0],calls=[];p.hp=70;p.stillness_citta_dharma_stacks=2;p.wind_spirit_forging_stacks=1;
 for(const [name,label] of [['increase_idx_hp','hp'],['increase_idx_max_hp','max'],['increase_idx_physique','physique']]){
  const original=g[name].bind(g);g[name]=(...args)=>{calls.push(label+':'+args[1]);return original(...args);};
 }
 const inc=g.increase_idx_x_by_c.bind(g);g.increase_idx_x_by_c=(idx,key,n)=>{if(key==='agility')calls.push('agility:'+n);return inc(idx,key,n);};
 g.increase_idx_qi(0,2);
 assert.equal(calls[0],'hp:4');assert.ok(calls.indexOf('max:4')<calls.indexOf('physique:2'));assert.ok(calls.indexOf('physique:2')<calls.indexOf('agility:5'));
});
scenario('current-forging-cap-preserved',()=>{
 const {g}=fresh();const p=g.players[0];p.wind_spirit_forging_stacks=1;
 for(let i=0;i<8;i++)g.increase_idx_qi(0,3);
 assert.equal(p.wind_spirit_forging_gained,facts.wind_forging.current_cap);assert.equal(p.physique,facts.wind_forging.current_cap);
});
scenario('halved-to-zero-keeps-charges',()=>{
 const {g,e}=fresh();g.players[0].dream_nine_evil_ruptsprite_stacks=1;g.increase_idx_qi(0,1);
 assert.equal(e.metadata().remaining[0].wine,3);assert.equal(g.players[0].agility,0);g.increase_idx_qi(0,2);assert.equal(g.players[0].qi,1);assert.equal(g.players[0].agility,5);
});
scenario('mortal-body-conversion-is-not-qi-gain',()=>{
 const {g,e}=fresh();g.players[0].mortal_body_stacks=1;g.increase_idx_qi(0,2);
 assert.equal(g.players[0].qi,0);assert.equal(g.players[0].physique,2);assert.equal(e.metadata().remaining[0].wine,3);assert.equal(g.players[0].agility,0);
});
scenario('both-owners-and-actual-object-order',()=>{
 const {g,e}=fresh([[7059,7109],[7059,7109]],[1,0]);g.increase_idx_qi(0,1);g.increase_idx_qi(1,1);
 assert.equal(g.players[0].agility,5);assert.equal(g.players[1].agility,0);
 g.players.reverse();g.do_plant_start_permanent_buffs();g.increase_idx_qi(0,1);assert.equal(g.players[0].agility,5);
 assert.deepEqual(e.metadata().events.filter(e=>e.strategy_id===7059&&e.phase==='positive_qi_after267').map(e=>e.player_index),[1,0]);
});
scenario('recursive-callback-consumes-wine-before-healing',()=>{
 const {g,e}=fresh();let nested=false;const max=g.increase_idx_max_hp.bind(g);
 g.increase_idx_max_hp=(idx,n)=>{max(idx,n);if(!nested){nested=true;g.increase_idx_qi(idx,1);}};
 g.increase_idx_qi(0,1);assert.equal(g.players[0].max_hp,108);assert.equal(g.players[0].agility,5);assert.equal(e.metadata().remaining[0].wine,1);
});
scenario('healing-cannot-restore-consumed-wine',()=>{
 const {g,e}=fresh();g.increase_idx_hp=()=>{};g.increase_idx_qi(0,1);
 assert.equal(g.players[0].max_hp,104);assert.equal(g.players[0].hp,100);assert.equal(e.metadata().remaining[0].wine,2);
});
scenario('startup-callback-order-keeps-later-grants-unarmed',()=>{
 const g=new GameState();g.players.forEach(p=>{p.hp=100;p.max_hp=100;p.cards=['601011','601011','601011'];p.post_deck_setup();});
 const e=createOpeningQi(root,g,{players:[[7005,7059,7109],[]]});e.installBoundary(7109);
 const after=g.do_plant_start_permanent_buffs.bind(g);g.do_plant_start_permanent_buffs=function(){this.increase_idx_qi(0,1);after();};
 e.installBoundary(7059);const before=g.do_plant_start_permanent_buffs.bind(g);g.do_plant_start_permanent_buffs=function(){this.increase_idx_qi(0,1);before();};
 e.installBoundary(7005);g.do_plant_start_permanent_buffs();
 assert.equal(g.players[0].qi,2);assert.equal(g.players[0].agility,5);assert.equal(g.players[0].max_hp,100);assert.equal(e.metadata().remaining[0].wine,3);
});
scenario('negative-reward-gain-rejected',()=>{
 const {g,e}=fresh();const before=e.metadata();assert.throws(()=>g.increase_idx_qi(0,-1),/nonnegative/);assert.deepEqual(before,e.metadata());
});
for(const value of [null,{players:[[7005,7005],[]]},{players:[[89],[]]},{players:[[],[]]},{players:[[7109],[]],outcome:1}])scenario('reject-'+JSON.stringify(value),()=>{
 assert.throws(()=>createOpeningQi(root,new GameState(),value),/opening_qi_unresolved/);
});
scenario('double-and-incomplete-boundaries-rejected',()=>{
 const {g,e}=fresh();assert.throws(()=>e.installBoundary(7005),/duplicate/);assert.throws(()=>createOpeningQi(root,g,{players:[[7005],[]]}),/already_installed/);
 const h=new GameState(),p=createOpeningQi(root,h,{players:[[7005],[]]});p.installBoundary(7005);assert.throws(()=>h.do_plant_start_permanent_buffs(),/incomplete/);
});
console.log(JSON.stringify({passed:true,scenarios:passed.length,names:passed}));
