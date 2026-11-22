import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installCurrentSeasonContext} from '../tools/current_season_context_v27.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));
await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
let scenarios=0;
const hookNames=['wood','wood_forceage','fire','earth','metal','water'];
function group(g,id){for(const n of hookNames)g[n==='wood_forceage'?'do_wood_spirit_forceage_formation':'do_'+n+'_spirit_formation'](id);}
function fresh(ids=[[23080],[]],order=[0,1]) {
  const g=new GameState(undefined,undefined,'season-context-v27');
  for(const p of g.players){p.hp=50;p.max_hp=100;p.cards=['601011','601011','601011'];}
  const extra=installCurrentSeasonContext(root,g,swogi,{players:ids},order);
  return [g,extra];
}
const base={wood:'131011',fire:'131031',earth:'131051',metal:'131071',water:'131091'};
const successor={wood:'fire',fire:'earth',earth:'metal',metal:'water',water:'wood'};
// Exhaustive element-pair trigger matrix, including unrelated ordinary attack.
for(const form of Object.keys(base))for(const [played,id] of Object.entries({...base,none:'601011'})) {
  const [g,e]=fresh();g.players[0][form+'_spirit_formation_stacks']=3;
  const before=g.players.map(p=>({hp:p.hp,max_hp:p.max_hp,def:p.def,qi:p.qi,penetrate:p.penetrate}));
  group(g,id);
  const should=played===form||played===successor[form];
  assert.equal(e.metadata().events.length,should?1:0);
  assert.equal(g.players[0].hp,50+(should&&form==='wood'?3:0));
  assert.equal(g.players[1].hp,50-(should&&form==='fire'?3:0));
  assert.equal(g.players[1].max_hp,100-(should&&form==='fire'?3:0));
  assert.equal(g.players[0].def,should&&form==='earth'?3:0);
  assert.equal(g.players[0].qi,should&&form==='water'?3:0);
  assert.equal(g.players[0].penetrate,should&&form==='metal'?3:0);
  assert.equal(g.used_randomness,false);scenarios++;
}
// Two eligible conditions cannot double an effect; inspect actual hook order.
{
  const testCards={...swogi,[base.wood]:{...swogi[base.wood],is_wood_spirit:true,is_fire_spirit:true,is_earth_spirit:true,is_metal_spirit:true,is_water_spirit:true}};
  const h=new GameState();for(const p of h.players){p.hp=50;p.max_hp=100;}
  const x=installCurrentSeasonContext(root,h,testCards,{players:[[23080],[]]},[0,1]);
  for(const n of Object.keys(base))h.players[0][n+'_spirit_formation_stacks']=2;
  // Local test metadata exercises overlapping predicates without editing swogi.
  group(h,base.wood);
  assert.deepEqual(x.metadata().events.map(v=>v.formation),['earth','water','fire','wood','metal']);
  assert.equal(h.players[0].hp,52);assert.equal(h.players[1].hp,48);
  assert.equal(h.players[0].def,2);assert.equal(h.players[0].qi,2);
  assert.equal(h.players[0].penetrate,2);scenarios++;
}
// Full trigger path executes formations before the card body, exactly once.
{
  const [g,e]=fresh();const p=g.players[0];p.cards=[base.fire,'601011','601011'];
  p.post_deck_setup();p.wood_spirit_formation_stacks=2;p.fire_spirit_formation_stacks=3;
  g.trigger_card(base.fire,0);
  assert.deepEqual(e.metadata().events.map(x=>x.formation),['fire','wood']);
  assert.equal(p.hp,52);scenarios++;
}
// Do not expand forceage healing to fire cards just because23080 is present.
{
  const [g,e]=fresh();g.players[0].wood_spirit_forceage_formation_stacks=1;g.players[0].increase_atk=7;
  group(g,base.fire);assert.equal(g.players[0].hp,50);
  group(g,base.wood);assert.equal(g.players[0].hp,57);scenarios++;
}
// Dragon Awe uses normal negative-effect callbacks, before plant starts.
for(const ward of [0,1]) {
  const [g,e]=fresh([[3001],[]]);const target=g.players[1];target.hexproof=ward;
  g.players[0].divine_power_grass_stacks=2;
  g.do_plant_start_permanent_buffs();
  assert.equal(target.decrease_atk,ward?0:1);assert.equal(target.hexproof,0);
  assert.equal(g.players[0].increase_atk,2);assert.equal(e.metadata().events.length,1);
  g.do_plant_start_permanent_buffs();assert.equal(e.metadata().events.length,1);scenarios++;
}
// Ownership follows identity across initiative swap and later active swaps.
{
  const [g,e]=fresh([[3001,23080],[]],[1,0]);
  g.do_plant_start_permanent_buffs();assert.equal(e.metadata().events.length,0);
  g.swap_players();g.do_plant_start_permanent_buffs();assert.equal(g.players[1].decrease_atk,1);
  g.players[0].water_spirit_formation_stacks=2;group(g,base.wood);
  assert.equal(g.players[0].qi,2);assert.equal(e.metadata().events[1].player_index,0);scenarios++;
}
// No owners: complete native state and event logs remain identical.
for(const id of Object.values(base)) {
  const [g]=fresh([[],[]]);const h=new GameState(undefined,undefined,'season-context-v27');
  for(const p of h.players){p.hp=50;p.max_hp=100;p.cards=['601011','601011','601011'];}
  for(const s of [g,h])for(const n of Object.keys(base))s.players[0][n+'_spirit_formation_stacks']=2;
  group(g,id);group(h,id);assert.deepEqual(g.players,h.players);assert.deepEqual(g.output,h.output);scenarios++;
}
for(const value of [null,{}, {players:[[]]}, {players:[[3001,3001],[]]}, {players:[[16024],[]]},
    {players:[['23080'],[]]}, {players:[[3001],[]],winner:0}]) {
  assert.throws(()=>installCurrentSeasonContext(root,new GameState(),swogi,value,[0,1]),/ownership/);scenarios++;
}
process.stdout.write(JSON.stringify({passed:true,scenarios}));
