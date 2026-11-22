import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createDragonSeason} from '../tools/current_dragon_season_v65.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
let scenarios=0;
function fresh(ids=[[],[3004]],order=[0,1]){
 const g=new GameState(undefined,undefined,'dragon-season-software');
 for(const p of g.players){p.character='sw1';p.hp=200;p.max_hp=200;p.max_physique=100;p.cards=['601011','601011','601011'];p.currently_triggering_card_id='601011';p.currently_triggering_card_idx=0;p.currently_playing_card_idx=0;}
 const ext=createDragonSeason(root,g,{players:ids},order);ext.installOpening();return {g,ext,p:g.players[0],q:g.players[1]};
}
{
 const {g,ext,p,q}=fresh();g.deal_damage_inner(10,true,0);assert.equal(q.hp,190);assert.equal(ext.metadata().events.length,0);
 g.start_of_game_setup();const hp=q.hp;g.deal_damage_inner(10,false,0);assert.equal(q.hp,hp-10);assert.equal(ext.metadata().pending[1].buff784,1);
 g.atk(10);assert.equal(q.hp,hp-16);g.atk(10);assert.equal(q.hp,hp-22);assert.equal(q.water_spirit_dive_stacks,1);
 assert.equal(ext.metadata().events.filter(e=>e.kind==='first_received_attack_784_to_12').length,1);scenarios++;
}
//The owner's end of turn consumes dive, not each incoming attack or opponent turn.
{
 const {g,ext,p,q}=fresh();g.start_of_game_setup();g.atk(10);g.sim_turn();assert.equal(q.water_spirit_dive_stacks,1);
 g.players=[q,p];g.sim_turn();assert.equal(q.water_spirit_dive_stacks,0);const hp=q.hp;g.players=[p,q];g.atk(10);assert.equal(q.hp,hp-10);scenarios++;
}
//Both owners and external input-seat identities remain attached to player objects.
for(const order of [[0,1],[1,0]]){
 const {g,ext,p,q}=fresh([[3004],[3004]],order);g.start_of_game_setup();g.deal_damage_inner(10,true,0);g.deal_damage_inner(10,true,1);
 assert.equal(p.hp,194);assert.equal(q.hp,194);assert.deepEqual(ext.metadata().events.filter(e=>e.kind==='first_received_attack_784_to_12').map(e=>e.player_index),[order[1],order[0]]);scenarios++;
}
//Guard/defense do not prevent first-attack conversion; additive percentages.
for(const extra of [{guard_up:1},{def:50},{water_spirit_dive_stacks:2},{flaw:1}]){
 const {g,ext,p,q}=fresh();g.start_of_game_setup();Object.assign(q,extra);g.atk(10);
 assert.equal(ext.metadata().pending[1].buff784,0);assert.equal(q.water_spirit_dive_stacks,(extra.water_spirit_dive_stacks??0)+1);
 if(extra.flaw)assert.equal(q.hp,190);if(extra.guard_up||extra.def)assert.equal(q.hp,200);scenarios++;
}
{
 const {g,p,q}=fresh();g.start_of_game_setup();p.weaken=1;g.atk(10);assert.equal(q.hp,198);scenarios++;
}
//Zero raw attack still follows attack preparation; no HP-loss trigger substitute.
{
 const {g,ext,q}=fresh();g.start_of_game_setup();g.atk(0);assert.equal(ext.metadata().pending[1].buff784,0);assert.equal(q.water_spirit_dive_stacks,1);scenarios++;
}
const fields=['internal_injury','weaken','flaw','decrease_atk','entangle','wound','styx','indigestion'];
for(const total of [0,1,2,9,10,11,21])for(const field of fields){
 const {g,ext,p,q}=fresh([[7121],[]]);g.start_of_game_setup();p[field]=total;const before={hp:p.hp,max_hp:p.max_hp,physique:p.physique};
 const r=ext.postBattle(true)[0];assert.equal(r.requested_physique,Math.floor(total/2));assert.equal(r.requested_permanent_max_hp,total>=10?1:0);
 assert.equal(r.total_debuff_layers,total);assert.equal(r.applied,false);assert.equal(r.next_battle_allowed,false);
 assert.deepEqual({hp:p.hp,max_hp:p.max_hp,physique:p.physique},before);assert.deepEqual(ext.postBattle(true)[0],r);scenarios++;
}
{
 const {g,ext,p}=fresh([[7121],[]]);g.start_of_game_setup();p.styx=99;
 assert.equal(ext.postBattle(false)[0].status,'combat_not_terminal');assert.equal(ext.postBattle(false)[0].requested_physique,undefined);scenarios++;
}
for(const players of [[[3013],[]],[[3004,3004],[]],[[7121],null],[[],[]]]){
 const g=new GameState();assert.throws(()=>createDragonSeason(root,g,{players}),/dragon_season_unresolved/);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios}));
