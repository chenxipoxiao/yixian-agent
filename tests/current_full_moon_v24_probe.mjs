import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installCurrentFullMoon} from '../tools/current_full_moon_v24.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));
await ready;
let scenarios=0;
function fresh(ownership=[[7065],[]],order=[0,1]) {
  const game=new GameState(undefined,undefined,'full-moon-software-v24');
  installCurrentFullMoon(root,game,{players:ownership},order);
  return game;
}
// Priority, limit, and entangle are checked against explicit client boundaries.
for(const agility of [8,9,10,18,19])for(const requested of [0,1])
for(const atLimit of [false,true])for(const entangled of [false,true]) {
  const g=fresh(),p=g.players[0];
  Object.assign(p,{agility,this_card_chases:requested,max_chases:1,
    chases:atLimit?1:0,entangle:entangled?1:0});
  g.process_this_card_chases();
  const paid=!requested && !atLimit && agility>=9;
  const attempt=!atLimit && (requested>0||paid);
  assert.equal(p.agility,agility-(paid?9:0));
  assert.equal(p.chases,atLimit?1:attempt&&!entangled?1:0);
  assert.equal(p.entangle,entangled&&!attempt?1:0);
  assert.equal(g.used_randomness,false);scenarios++;
}
// Explicit chase sources retain priority, even at agility9; no charge is spent.
{
  const g=fresh(),p=g.players[0];
  Object.assign(p,{agility:9,dream_craze_dance_tune_stacks:1,max_chases:1});
  g.process_this_card_chases();
  assert.equal(p.agility,9);assert.equal(p.chases,1);
  assert.equal(p.dream_craze_dance_tune_stacks,0);scenarios++;
}
// Anti-entangle consumes its native charge after the9 agility payment.
{
  const g=fresh(),p=g.players[0];
  Object.assign(p,{agility:9,entangle:1,prevent_anti_chase:1,max_chases:1});
  g.process_this_card_chases();
  assert.equal(p.agility,0);assert.equal(p.chases,1);
  assert.equal(p.entangle,1);assert.equal(p.prevent_anti_chase,0);scenarios++;
}
// Identity, rather than the currently active array index, owns this passive.
{
  const g=fresh([[7065],[]],[1,0]);
  g.players[0].agility=9;g.players[0].max_chases=1;
  g.players[1].agility=9;g.players[1].max_chases=1;
  g.process_this_card_chases();assert.equal(g.players[0].chases,0);
  g.players.reverse();g.process_this_card_chases();
  assert.equal(g.players[0].chases,1);assert.equal(g.players[0].agility,0);scenarios++;
}
// Consecutive actions still pay separately and respect the allowed chase count.
{
  const g=fresh(),p=g.players[0];Object.assign(p,{agility:27,max_chases:2});
  for(let i=0;i<3;i++){p.this_card_chases=0;g.process_this_card_chases();}
  assert.equal(p.chases,2);assert.equal(p.agility,9);scenarios++;
}
// Neither unrelated players nor another game has its native method changed.
for(const agility of [9,10,19]) {
  const g=fresh([[],[]]),native=new GameState(undefined,undefined,'full-moon-software-v24');
  for(const s of [g,native])Object.assign(s.players[0],{agility,max_chases:1});
  assert.equal(g.process_this_card_chases(),native.process_this_card_chases());
  assert.deepEqual(g.players,native.players);assert.deepEqual(g.output,native.output);scenarios++;
}
for(const value of [null,{}, {players:[[]]}, {players:[[7065,7065],[]]},
    {players:[[348],[]]}, {players:[['7065'],[]]}, {players:[[7065],[]],winner:0}]) {
  assert.throws(()=>installCurrentFullMoon(root,new GameState(),value,[0,1]),/ownership/);
  scenarios++;
}
process.stdout.write(JSON.stringify({passed:true,scenarios}));
