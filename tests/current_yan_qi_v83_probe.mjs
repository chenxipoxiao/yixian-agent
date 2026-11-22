import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installYanQi} from '../tools/current_yan_qi_v83.mjs';
import {installSpiritOutburst} from '../tools/current_spirit_outburst_v83.mjs';
import {installCloudsRain} from '../tools/current_clouds_rain_v39.mjs';
import {installDragonQi} from '../tools/current_dragon_qi_v40.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
let scenarios=0;const entry={strategy_id:7053};
function fresh(){const g=new GameState(undefined,undefined,'yan-qi-software');for(const p of g.players){
 p.character='sw3';p.hp=40;p.max_hp=100;p.max_physique=100;p.cards=['601011','601011','601011'];p.hand_count=2;
}return g;}
function bind(g,players=[entry,null],order=[0,1]){const m=installYanQi(root,g,{players},order);const s=installSpiritOutburst(root,g,order);m.attachHealing(s);return {m,s};}
function armed(){const g=fresh(),{m,s}=bind(g);g.start_of_game_setup();return {g,m,s,p:g.players[0]};}
const uses=m=>m.metadata().remaining[0].pending_uses;
for(const order of [[0,1],[1,0]]){
 const g=fresh(),{m}=bind(g,[entry,entry],order);g.increase_idx_hp(0,1);assert.equal(g.players[0].hp,41);
 assert.equal(m.metadata().events.length,0);g.start_of_game_setup();
 g.increase_idx_hp(0,4);assert.equal(g.players[0].hp,65);assert.equal(uses(m),0);
 g.swap_players();g.increase_idx_hp(0,1);assert.equal(g.players[0].hp,61);
 assert.deepEqual(m.metadata().events.filter(e=>e.kind==='positive_actual_healing').map(e=>e.player_index),order);
 g.do_plant_start_permanent_buffs();assert.deepEqual(m.metadata().remaining.map(s=>s.pending_uses),[0,0]);scenarios++;
}
// Full overheal keeps the pending use; a later one-point actual heal consumes it.
{
 const {g,m,p}=armed();p.hp=100;g.increase_idx_hp(0,10);assert.equal(p.hp,100);assert.equal(uses(m),1);
 g.reduce_idx_hp(0,1);g.increase_idx_hp(0,5);assert.equal(p.hp,100);assert.equal(uses(m),0);
 const e=m.metadata().events.at(-1);assert.equal(e.trigger_value,1);assert.equal(e.requested_bonus,20);
 assert.equal(p.hp_gained,35);scenarios++;
}
{
 const {g,m,p}=armed();g.increase_idx_max_hp(0,7);assert.equal(p.max_hp,107);assert.equal(p.hp,61);
 assert.equal(m.metadata().events.at(-1).requested_bonus,21);g.increase_idx_hp(0,1);assert.equal(p.hp,62);scenarios++;
}
{
 const {g,m,p}=armed();g.increase_idx_hp(0,0);g.increase_idx_max_hp(0,0);g.reduce_idx_hp(0,2);
 assert.equal(uses(m),1);assert.equal(p.hp,38);scenarios++;
}
// Rejuvenation's summed maxHP gain triggers before the outer recovery. Nested
// recovery can trigger rejuvenation again, but744 has already been consumed.
{
 const {g,m,p}=armed();p.p2_rejuvenation_stacks=1;p.p3_rejuvenation_stacks=1;
 g.increase_idx_hp(0,1);assert.equal(p.hp,62);assert.equal(p.max_hp,114);
 const e=m.metadata().events.at(-1);assert.equal(e.kind,'positive_max_hp');assert.equal(e.before.max_hp,107);
 assert.equal(e.requested_bonus,21);assert.equal(m.metadata().events.length,2);scenarios++;
}
{
 const {g,m,p}=armed();p.hp=100;p.vitality_blossom_stacks=1;g.increase_idx_hp(0,5);
 assert.equal(p.hp,126);assert.equal(p.max_hp,126);assert.equal(m.metadata().events.at(-1).kind,'positive_max_hp');scenarios++;
}
for(const field of ['prevent_gain_hp_stacks','metal_spirit_chokehold_stacks','m_metal_spirit_seal_stacks']){
 const {g,m,p}=armed();p[field]=1;g.increase_idx_hp(0,5);assert.equal(uses(m),1);assert.equal(p.hp,40);scenarios++;
}
{
 const {g,m,p}=armed();p.hp=0;g.increase_idx_hp(0,10);assert.equal(p.hp,30);assert.equal(uses(m),0);
 g.increase_idx_max_hp(0,5);assert.equal(uses(m),0);assert.equal(p.hp,30);scenarios++;
}
// Source callback order:744 nested heal ->373 ->787, then outer373 ->787.
{
 const {g,m,s,p}=armed();p.hp=90;p.god_opportunity_reversal_stacks=1;
 g.current_spirit_outburst_gain(2,4000106);const damage=[],orig=g.deal_damage_inner.bind(g);
 g.deal_damage_inner=(amount,...rest)=>{damage.push(amount);return orig(amount,...rest);};
 g.players[1].hp=200;g.players[1].max_hp=200;g.increase_idx_hp(0,20);
 assert.deepEqual(damage,[10,20,10,10]);assert.equal(g.players[1].hp,150);assert.equal(uses(m),0);
 assert.equal(s.forPlayer(p).remaining,2);scenarios++;
}
// Both HP and maxHP gain use current40% conform; bonus base is floored first.
{
 const {g,m,p}=armed();p.god_opportunity_conform_stacks=1;g.increase_idx_max_hp(0,3);
 assert.equal(p.max_hp,105);assert.equal(m.metadata().events.at(-1).requested_bonus,21);assert.equal(p.hp,70);scenarios++;
}
// Activation before7069 (whose qi -> mixed-grain heal can consume744) and after3011.
{
 const g=fresh();installCloudsRain(root,g,{players:[{hand:[15,15],board:[0,0,0]},null]});
 const m=installYanQi(root,g,{players:[entry,null]});installDragonQi(root,g,{players:[{strategy_id:3011},null]});
 const s=installSpiritOutburst(root,g);m.attachHealing(s);g.players[0].mixed_grain_zongzi_stacks=1;
 g.start_of_game_setup();assert.equal(g.players[0].qi,4);assert.equal(g.players[0].hp,61);
 assert.equal(m.metadata().events.at(-1).kind,'positive_actual_healing');scenarios++;
}
{
 const {g,m}=armed();for(const n of [-1,0.5,NaN])assert.throws(()=>g.increase_idx_hp(0,n),/int32/);
 assert.equal(uses(m),1);assert.throws(()=>installYanQi(root,g,{players:[entry,null]}),/already_installed/);
 assert.throws(()=>m.attachHealing({forPlayer:()=>({remaining:0})}),/already_attached/);scenarios++;
}
for(const value of [null,{}, {players:[entry]}, {players:[{strategy_id:7053,remaining:20},null]}, {players:[{strategy_id:326},null]}]){
 assert.throws(()=>installYanQi(root,fresh(),value),/ownership/);scenarios++;
}
{
 const g=fresh();installYanQi(root,g,{players:[entry,null]});assert.throws(()=>g.start_of_game_setup(),/not_attached/);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios}));
