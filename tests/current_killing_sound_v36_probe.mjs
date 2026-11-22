import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installKillingSound} from '../tools/current_killing_sound_v36.mjs';
import {installHeavenSpirit} from '../tools/current_heaven_spirit_v34.mjs';
import {installCurrentSeasonContext} from '../tools/current_season_context_v27.mjs';
import {installCloudsRain} from '../tools/current_clouds_rain_v35.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
let scenarios=0;const entry=enabled=>({strategy_id:1006,enabled});
function fresh(){const g=new GameState(undefined,undefined,'killing-sound-boundaries');
 for(const p of g.players){p.character='sw3';p.hp=50;p.max_hp=100;p.cards=['601011','601011','601011'];}return g;}
for(const a of [null,false,true])for(const b of [null,false,true])for(const order of [[0,1],[1,0]]) {
 const g=fresh(),x=installKillingSound(root,g,{players:[a===null?null:entry(a),b===null?null:entry(b)]},order);
 g.start_of_game_setup();let hp=50,max=100;
 for(let n=0;n<Number(a===true)+Number(b===true);n++){const d=Math.floor(hp*15/100);hp-=d;max-=d;}
 assert.deepEqual(g.players.map(p=>[p.hp,p.max_hp]),[[hp,max],[hp,max]]);
 assert.deepEqual(x?.metadata().events.map(e=>e.player_index)??[],order.filter(i=>[a,b][i]!==null));
 const count=x?.metadata().events.length??0;g.do_plant_start_permanent_buffs();g.swap_players();g.do_plant_start_permanent_buffs();
 assert.equal(x?.metadata().events.length??0,count);assert.equal(g.used_randomness,false);scenarios++;
}
for(const hp of [1,6,7,20,67,100]) {
 const g=fresh();g.players[0].hp=hp;g.players[1].hp=hp;
 const x=installKillingSound(root,g,{players:[entry(true),null]});g.start_of_game_setup();
 const d=Math.floor(hp*15/100);assert.deepEqual(x.metadata().events[0].requested_reductions,[d,d]);
 assert.equal(g.players[0].hp,hp-d);assert.equal(g.players[0].max_hp,100-d);scenarios++;
}
// Explicit software callback changes the other HP between calls. Both amounts
// still derive from the pre-effect snapshot, as the client locals require.
{
 const g=fresh(),calls=[],hp=g.reduce_idx_hp.bind(g),max=g.reduce_idx_max_hp.bind(g);
 g.reduce_idx_hp=(i,d,c)=>{calls.push(['hp',i,d,c]);if(i===0)g.players[1].hp+=10;return hp(i,d,c);};
 g.reduce_idx_max_hp=(i,d)=>{calls.push(['max',i,d]);return max(i,d);};
 installKillingSound(root,g,{players:[entry(true),null]});g.start_of_game_setup();
 assert.deepEqual(calls,[['hp',0,7,false],['max',0,7],['hp',1,7,false],['max',1,7]]);
 assert.equal(g.players[1].hp,53);scenarios++;
}
{
 const g=fresh();g.players[0].hp=100;g.players[0].guard_up=1;
 installKillingSound(root,g,{players:[entry(true),null]});g.start_of_game_setup();
 assert.equal(g.players[0].guard_up,0);assert.equal(g.players[0].hp_lost,0);
 assert.equal(g.players[0].hp,85);assert.equal(g.players[0].max_hp,85);scenarios++;
}
{
 const g=fresh();g.players[0].covert_shift_stacks=1;
 installKillingSound(root,g,{players:[entry(true),null]});g.start_of_game_setup();
 assert.equal(g.players[0].hp,57);assert.equal(g.players[0].max_hp,93);assert.equal(g.players[0].covert_shift_stacks,0);scenarios++;
}
{
 const g=fresh();g.players[0].leaf_shield_flower_stacks=1;g.players[0].def=100;
 installKillingSound(root,g,{players:[entry(true),null]});g.start_of_game_setup();
 assert.equal(g.players[0].hp,46);assert.equal(g.players[0].def,97);assert.equal(g.players[0].max_hp,93);scenarios++;
}
{
 const g=fresh();g.players[1].kun_wu_molten_ring_stacks=3;
 installKillingSound(root,g,{players:[entry(true),null]});g.start_of_game_setup();
 assert.equal(g.players[0].hp,43);assert.equal(g.players[0].max_hp,90);scenarios++;
}
{
 const g=fresh(),points=[],plants=g.do_plant_start_permanent_buffs.bind(g),debuff=g.increase_idx_debuff.bind(g);
 g.players[0].zen_mind_forging_body_stacks=5;g.players[0].max_physique=0;
 g.players[0].stillness_citta_dharma_stacks=2;g.players[0].hand_count=2;
 g.do_plant_start_permanent_buffs=(...a)=>{points.push(['plants',g.players[0].hp]);return plants(...a);};
 g.increase_idx_debuff=(...a)=>{points.push(['3001',g.players[0].hp]);return debuff(...a);};
 installCloudsRain(root,g,{players:[{hand:[15,15],board:[0,0,0]},null]});
 installCurrentSeasonContext(root,g,swogi,{players:[[3001],[]]},[0,1]);
 const x=installKillingSound(root,g,{players:[entry(true),null]});
 installHeavenSpirit(root,g,{players:[{strategy_id:1001,enabled:true},null]},[0,1]);g.start_of_game_setup();
 assert.deepEqual(x.metadata().events[0].before,[{hp:59,max_hp:105},{hp:50,max_hp:100}]);
 assert.deepEqual(points,[['3001',51],['plants',53],['plants',43]]);scenarios++;
}
for(const hp of [0,-1,143165577]) {
 const g=fresh();g.players[0].hp=hp;
 installKillingSound(root,g,{players:[entry(true),null]});assert.throws(()=>g.start_of_game_setup(),/int32_start_hp/);scenarios++;
}
{
 const g=fresh();installKillingSound(root,g,{players:[entry(true),null]});
 assert.throws(()=>installKillingSound(root,g,{players:[entry(true),null]}),/already_installed/);scenarios++;
}
for(const v of [null,{}, {players:[entry(true)]},{players:[{strategy_id:1001,enabled:true},null]},
 {players:[{strategy_id:1006,enabled:1},null]},{players:[entry(true),null],outcome:1}]) {
 assert.throws(()=>installKillingSound(root,fresh(),v),/ownership/);scenarios++;
}
process.stdout.write(JSON.stringify({passed:true,scenarios}));
