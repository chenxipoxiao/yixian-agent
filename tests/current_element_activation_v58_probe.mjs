import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createElementActivation} from '../tools/current_element_activation_v58.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const names=[],scenario=(name,fn)=>{fn();names.push(name);};
const fields={237:'activate_metal_spirit_stacks',238:'activate_wood_spirit_stacks',239:'activate_water_spirit_stacks',240:'activate_fire_spirit_stacks',241:'activate_earth_spirit_stacks'};
const branches=[[10109,[239,238]],[20109,[238,240]],[30109,[240,241]],[40109,[241,237]],[50109,[237,239]]];
function fresh(ids=[[7028,7084],[]],talents=[[10109],[]],order=[0,1]){
 const g=new GameState(undefined,undefined,'element-activation-software');
 for(const p of g.players){p.hp=p.max_hp=100;p.cards=['601011','601011','601011'];p.post_deck_setup();}
 const e=createElementActivation(root,g,{players:ids,innate_talents:talents},order);e.installOpening();return {g,e};
}
for(const [talent,buffs] of branches)for(const order of [[0,1],[1,0]])scenario('ordered-innate-'+talent+'-order'+order,()=>{
 const {g,e}=fresh([[7028],[]],[[talent],[]],order),owner=g.players[order.indexOf(0)];
 g.do_plant_start_permanent_buffs();g.players.reverse();g.do_plant_start_permanent_buffs();
 const ev=e.metadata().events;assert.deepEqual(ev.map(x=>x.buff_id),buffs);assert.ok(ev.every(x=>x.player_index===0));
 for(const [buff,field] of Object.entries(fields))assert.equal(owner[field],buffs.includes(Number(buff))?1:0);
 g.do_plant_start_permanent_buffs();g.players.reverse();g.do_plant_start_permanent_buffs();assert.equal(e.metadata().events.length,2);
});
scenario('all-explicit-innates-use-independent-source-order',()=>{
 const {g,e}=fresh([[7028],[]],[[50109,30109,10109,40109,20109],[]]);g.do_plant_start_permanent_buffs();
 assert.deepEqual(e.metadata().events.map(x=>x.buff_id),branches.flatMap(x=>x[1]));
});
scenario('no-innate-no-guessed-character-activation',()=>{
 const {g,e}=fresh([[7028],[]],[[],[]]);g.do_plant_start_permanent_buffs();assert.deepEqual(e.metadata().events,[]);
});
scenario('ordinary-innate-mark-and-season-both-run',()=>{
 const {g,e}=fresh([[7028],[]],[[10109],[]]),p=g.players[0];p.innate_mark_stacks=1;p.innate_metal_stacks=1;
 g.do_innate_mark(0);g.do_plant_start_permanent_buffs();
 assert.equal(p.activate_metal_spirit_stacks,1);assert.equal(p.activate_water_spirit_stacks,1);assert.equal(p.activate_wood_spirit_stacks,1);
 assert.deepEqual(e.metadata().events.map(x=>x.buff_id),[239,238]);
});
scenario('water-recursively-activates-earth-before-return',()=>{
 const {g,e}=fresh([[7084],[]],[[],[]]),p=g.players[0];g.activate_water_spirit();
 assert.equal(p.activate_water_spirit_stacks,1);assert.equal(p.activate_earth_spirit_stacks,1);assert.equal(p.def,8);
 const ev=e.metadata().events;assert.deepEqual(ev.map(x=>x.buff_id),[239,241]);assert.equal(ev[0].before.activate_water_spirit_stacks,1);
 assert.equal(ev[1].before.activate_earth_spirit_stacks,1);assert.equal(ev[0].after.def,8);
});
scenario('repeated-positive-calls-each-trigger',()=>{
 const {g,e}=fresh([[7084],[]],[[],[]]);g.activate_water_spirit();g.activate_water_spirit();g.activate_earth_spirit();
 assert.equal(g.players[0].def,24);assert.equal(g.players[0].activate_earth_spirit_stacks,3);assert.equal(e.metadata().events.length,5);
});
scenario('multi-unit-gain-is-one-call-not-many-activations',()=>{
 const {g,e}=fresh([[7084],[]],[[],[]]);g.increase_idx_x_by_c(0,fields[239],3);
 assert.equal(g.players[0][fields[239]],3);assert.equal(g.players[0][fields[241]],1);assert.equal(g.players[0].def,8);assert.equal(e.metadata().events.length,2);
});
scenario('zero-and-decrement-do-not-trigger',()=>{
 const {g,e}=fresh([[7084],[]],[[],[]]);g.increase_idx_activate(0,fields[239],0);g.players[0][fields[239]]=2;
 g.reduce_idx_x_by_c(0,fields[239],1);assert.equal(g.players[0][fields[239]],1);assert.equal(g.players[0].def,0);assert.equal(e.metadata().events.length,0);
 assert.throws(()=>g.increase_idx_activate(0,fields[239],-1),/invalid_activation_gain/);
});
for(const buff of [237,238,240])scenario('other-element-'+buff+'-no-rain',()=>{
 const {g,e}=fresh([[7084],[]],[[],[]]);g.increase_idx_activate(0,fields[buff],1);assert.equal(g.players[0].def,0);assert.equal(e.metadata().events.length,0);
});
scenario('nested-activation-runs-anima-and-gather-qi',()=>{
 const {g,e}=fresh([[7084],[]],[[],[]]),p=g.players[0];p.five_elements_anima_stacks=1;p.five_elements_gather_qi_stacks=2;
 g.activate_water_spirit();assert.equal(p.force_of_water,2);assert.equal(p.qi,4);assert.equal(p.def,20);
 g.activate_water_spirit();assert.equal(p.force_of_water,2);assert.equal(p.qi,4);assert.equal(p.def,28);
});
scenario('nested-activation-runs-explosion-twice',()=>{
 const {g}=fresh([[7084],[]],[[],[]]);g.players[0].five_elements_explosion_stacks=1;g.activate_water_spirit();
 assert.equal(g.players[1].hp,94);assert.equal(g.players[1].max_hp,94);assert.equal(g.players[0].def,8);
});
scenario('nested-activation-keeps-one-pending-chase',()=>{
 const {g}=fresh([[7084],[]],[[],[]]),p=g.players[0];p.ultimate_world_formation_stacks=2;g.activate_water_spirit();
 assert.equal(p.ultimate_world_formation_stacks,1);assert.equal(p.this_card_chases,1);
});
scenario('def-gain-respects-prevention',()=>{
 const {g,e}=fresh([[7084],[]],[[],[]]);g.players[0].prevent_gain_def_stacks=1;g.activate_water_spirit();
 assert.equal(g.players[0].def,0);assert.equal(g.players[0][fields[241]],1);assert.equal(e.metadata().events.length,2);
});
scenario('def-gain-keeps-native-modifiers',()=>{
 const {g}=fresh([[7084],[]],[[],[]]),p=g.players[0];p.kun_wu_metal_ring_stacks=2;g.activate_water_spirit();assert.equal(p.def,10);assert.equal(p.total_def_gained,10);
});
scenario('season-innate-then-nested-rain-then-second-element',()=>{
 const {g,e}=fresh();g.do_plant_start_permanent_buffs();assert.equal(g.players[0].def,8);
 assert.deepEqual(e.metadata().events.map(x=>[x.strategy_id,x.buff_id]),[[7028,239],[7084,239],[7084,241],[7028,238]]);
});
scenario('opponent-index-and-reverse-retain-owner',()=>{
 const {g,e}=fresh([[7084],[]],[[],[]],[1,0]);g.increase_idx_activate(1,fields[239],1);assert.equal(g.players[1].def,8);
 g.activate_water_spirit();assert.equal(g.players[0].def,0);g.players.reverse();g.activate_water_spirit();assert.equal(g.players[0].def,16);
 assert.ok(e.metadata().events.every(x=>x.player_index===0));
});
scenario('both-owners-have-independent-activation',()=>{
 const {g,e}=fresh([[7028,7084],[7028,7084]],[[10109],[50109]]);g.do_plant_start_permanent_buffs();g.players.reverse();g.do_plant_start_permanent_buffs();
 assert.equal(g.players[0].def,8);assert.equal(g.players[1].def,8);assert.equal(e.metadata().events.filter(x=>x.strategy_id===7084).length,4);
});
scenario('invalid-context-does-not-default',()=>{
 const g=new GameState();assert.throws(()=>createElementActivation(root,g,{players:[[7028],[]]}),/explicit_players/);
 assert.throws(()=>createElementActivation(root,g,{players:[[7084],[]],innate_talents:null}),/innate/);
 assert.throws(()=>createElementActivation(root,g,{players:[[7084,7084],[]],innate_talents:[[],[]]}),/ownership/);
});
scenario('metadata-copy-cannot-change-live-events',()=>{
 const {g,e}=fresh();g.do_plant_start_permanent_buffs();const m=e.metadata();m.events[0].buff_id=999;assert.equal(e.metadata().events[0].buff_id,239);
 assert.throws(()=>e.installOpening(),/duplicate/);assert.equal(e.metadata().training_label_allowed,false);
});
console.log(JSON.stringify({passed:true,scenarios:names.length,names}));
