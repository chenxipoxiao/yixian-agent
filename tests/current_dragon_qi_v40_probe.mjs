import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installDragonQi} from '../tools/current_dragon_qi_v40.mjs';
import {installHeavenSpirit} from '../tools/current_heaven_spirit_v34.mjs';
import {installCloudsRain} from '../tools/current_clouds_rain_v39.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
let scenarios=0;
const entry={strategy_id:3011};
function fresh(){const g=new GameState(undefined,undefined,'dragon-qi-software');for(const p of g.players){
 p.character='sw3';p.hp=40;p.max_hp=100;p.max_physique=100;p.cards=['601011','601011','601011'];p.hand_count=2;
}return g;}
for(const order of [[0,1],[1,0]]) {
 const g=fresh(),m=installDragonQi(root,g,{players:[entry,entry]},order);
 g.increase_idx_qi(0,1);assert.equal(g.players[0].qi,1);assert.equal(m.metadata().events.length,0);
 g.start_of_game_setup();assert.deepEqual(m.metadata().remaining.map(x=>x.bonus),[2,2]);
 g.increase_idx_qi(0,0);g.reduce_idx_qi(0,1);assert.equal(m.metadata().remaining[0].bonus,2);
 g.increase_idx_qi(0,1);g.increase_idx_qi(0,1);assert.equal(g.players[0].qi,4);
 g.swap_players();g.increase_idx_qi(0,3);assert.equal(g.players[0].qi,5);
 assert.deepEqual(m.metadata().events.filter(e=>e.kind==='first_positive_qi').map(e=>e.player_index),order);
 assert.deepEqual(m.metadata().remaining.map(x=>x.bonus),[0,0]);
 g.do_plant_start_permanent_buffs();assert.deepEqual(m.metadata().remaining.map(x=>x.bonus),[0,0]);
 assert.throws(()=>installDragonQi(root,g,{players:[entry,entry]},order),/already_installed/);scenarios++;
}
//1001 is before this owner's3011; a later opponent1001 can consume the armed bonus.
for(const order of [[0,1],[1,0]])for(const bothSound of [false,true]) {
 const g=fresh(),m=installDragonQi(root,g,{players:[entry,entry]},order);
 const sound={strategy_id:1001,enabled:true};
 installHeavenSpirit(root,g,{players:bothSound?[sound,sound]:order[0]===0?[sound,null]:[null,sound]},order);
 g.start_of_game_setup();assert.deepEqual(g.players.map(p=>p.qi),bothSound?[6,4]:[2,2]);
 assert.deepEqual(m.metadata().remaining.map(s=>s.bonus),bothSound?[0,2]:[2,2]);scenarios++;
}
//7069 is later in the same seasonal opening and consumes the bonus immediately.
{
 const g=fresh();installCloudsRain(root,g,{players:[{hand:[15,15],board:[0,0,0]},null]});
 const m=installDragonQi(root,g,{players:[entry,null]});g.start_of_game_setup();
 assert.equal(g.players[0].qi,3);assert.equal(g.players[1].qi,0);assert.equal(m.metadata().remaining[0].bonus,0);scenarios++;
}
//Bonus precedes mixed-grain addition, crane multiplier and shared post-gain healing.
{
 const g=fresh(),m=installDragonQi(root,g,{players:[entry,null]});g.start_of_game_setup();
 Object.assign(g.players[0],{mixed_grain_zongzi_stacks:2,colorful_spirit_crane_stacks:1,stillness_citta_dharma_stacks:1});
 g.increase_idx_qi(0,1);assert.equal(g.players[0].qi,8);assert.equal(g.players[0].hp,50);
 assert.equal(g.players[0].total_qi_gained,8);assert.equal(m.metadata().remaining[0].bonus,0);scenarios++;
}
//Physique conversion and integer halving still consume543 even without gained qi.
for(const field of ['mortal_body_stacks','dream_nine_evil_ruptsprite_stacks']) {
 const g=fresh(),m=installDragonQi(root,g,{players:[entry,null]});g.start_of_game_setup();g.players[0][field]=1;
 g.increase_idx_qi(0,1);assert.equal(m.metadata().remaining[0].bonus,0);
 if(field==='mortal_body_stacks'){assert.equal(g.players[0].qi,0);assert.equal(g.players[0].physique,3);}
 else assert.equal(g.players[0].qi,1);scenarios++;
}
//A reentrant shared callback cannot consume the one-shot bonus again.
{
 const g=fresh();let nested=false;const heal=g.increase_idx_hp.bind(g);
 g.increase_idx_hp=(idx,amount)=>{if(!nested){nested=true;g.increase_idx_qi(idx,1);}return heal(idx,amount);};
 const m=installDragonQi(root,g,{players:[entry,null]});g.start_of_game_setup();g.players[0].mixed_grain_zongzi_stacks=1;
 g.increase_idx_qi(0,1);assert.equal(g.players[0].qi,6);
 assert.equal(m.metadata().events.filter(e=>e.kind==='first_positive_qi').length,1);scenarios++;
}
{
 const g=fresh(),m=installDragonQi(root,g,{players:[entry,null]});g.start_of_game_setup();
 for(const amount of [-1,0.5,NaN,2147483647])assert.throws(()=>g.increase_idx_qi(0,amount),/int32|overflow/);
 assert.equal(m.metadata().remaining[0].bonus,2);assert.equal(g.players[0].qi,0);scenarios++;
}
for(const value of [null,{}, {players:[entry]}, {players:[{strategy_id:3011,enabled:true},null]}, {players:[{strategy_id:3012},null]}]) {
 assert.throws(()=>installDragonQi(root,fresh(),value),/ownership/);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios}));
