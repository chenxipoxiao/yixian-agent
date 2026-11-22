import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installHeavenSpirit} from '../tools/current_heaven_spirit_v34.mjs';
import {installCurrentSeasonContext} from '../tools/current_season_context_v27.mjs';
import {installCurrentStartStates} from '../tools/current_start_states_v7.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
let scenarios=0;
const entry=enabled=>({strategy_id:1001,enabled});
function fresh(){const g=new GameState(undefined,undefined,'heaven-spirit-boundaries');
  for(const p of g.players){p.hp=50;p.max_hp=100;p.cards=['601011','601011','601011'];}return g;}
// Includes both holders, disabled holders and initiative reversal; ownership
// is independent of the game's rotating active-player array.
for(const a of [null,false,true])for(const b of [null,false,true])for(const order of [[0,1],[1,0]]){
  const g=fresh(),x=installHeavenSpirit(root,g,{players:[a===null?null:entry(a),b===null?null:entry(b)]},order);
  g.start_of_game_setup();const expected=2*(Number(a===true)+Number(b===true));
  assert.deepEqual(g.players.map(p=>p.qi),[expected,expected]);
  assert.deepEqual(x?.metadata().events.map(e=>e.player_index)??[],order.filter(i=>[a,b][i]!==null));
  const counts=x?.metadata().events.length??0;g.do_plant_start_permanent_buffs();g.swap_players();g.do_plant_start_permanent_buffs();
  assert.equal(x?.metadata().events.length??0,counts);assert.equal(g.used_randomness,false);scenarios++;
}
// Observe actual setup boundaries: a blanket pre-battle+4 would fail this.
{
  const g=fresh(),points=[],ids=[...g.players];
  const f=g.apply_p1_fates_setup.bind(g),o=g.do_opening.bind(g);
  g.apply_p1_fates_setup=i=>{points.push(['fate',ids.indexOf(g.players[i]),...ids.map(p=>p.qi)]);return f(i);};
  g.do_opening=i=>{if(i===0)points.push(['opening',ids.indexOf(g.players[0]),...ids.map(p=>p.qi)]);return o(i);};
  installHeavenSpirit(root,g,{players:[entry(true),entry(true)]},[0,1]);g.start_of_game_setup();
  assert.deepEqual(points,[['fate',0,0,0],['opening',0,2,2],['fate',1,2,2],['opening',1,4,4]]);scenarios++;
}
// Existing3001 and plant hooks must occur after1001; native qi callbacks remain.
{
  const g=fresh();installCurrentStartStates(root,g);
  g.players[0].wind_spirit_forging_stacks=1;g.players[0].max_physique=20;
  const x=installCurrentSeasonContext(root,g,swogi,{players:[[3001],[]]},[0,1]);
  const points=[],deb=g.increase_idx_debuff.bind(g);
  g.increase_idx_debuff=(...args)=>{points.push(g.players.map(p=>p.qi));return deb(...args);};
  installHeavenSpirit(root,g,{players:[entry(true),entry(true)]},[0,1]);g.start_of_game_setup();
  assert.deepEqual(points,[[2,2]]);assert.equal(x.metadata().events.length,1);
  assert.equal(g.players[0].qi,4);assert.equal(g.players[0].physique,3);scenarios++;
}
// Real healing/defense reaction proves the gain did not bypass the shared path.
{
  const g=fresh();g.players[1].stillness_citta_dharma_stacks=2;g.players[1].spiritstat_tune_stacks=3;
  installHeavenSpirit(root,g,{players:[entry(true),null]},[0,1]);g.start_of_game_setup();
  assert.equal(g.players[1].hp,54);assert.equal(g.players[1].def,6);scenarios++;
}
for(const value of [null,{}, {players:[entry(true)]},{players:[{strategy_id:1002,enabled:true},null]},
 {players:[{strategy_id:1001,enabled:1},null]},{players:[entry(true),null],outcome:1}]){
 assert.throws(()=>installHeavenSpirit(root,fresh(),value,[0,1]),/ownership/);scenarios++;
}
{
 const g=fresh();installHeavenSpirit(root,g,{players:[entry(true),null]},[0,1]);
 assert.throws(()=>installHeavenSpirit(root,g,{players:[entry(true),null]},[0,1]),/already installed/);scenarios++;
}
process.stdout.write(JSON.stringify({passed:true,scenarios}));
