import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installCurrentNormalAttack} from '../tools/current_normal_attack_v28.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
let scenarios=0;
function fresh(ids=[[5011],[]],order=[0,1],cards=['601011','601011','601011']) {
  const g=new GameState(undefined,undefined,'normal-attack-v28');
  for(const p of g.players){p.hp=100;p.max_hp=100;p.cards=[...cards];p.post_deck_setup();}
  const extra=installCurrentNormalAttack(root,g,{players:ids},order);
  g.do_plant_start_permanent_buffs();
  return [g,extra];
}
// Client ordinary predicate includes base0 and all286 grades. Native aliases
// share these three attack bodies; ward consumes incoming layers in order.
for(const [card,damage] of [['601011',3],['601012',6],['601013',9]])for(let ward=0;ward<=4;ward++) {
  const [g,e]=fresh([[5011],[]],[0,1],[card,card,card]),me=g.players[0],enemy=g.players[1];
  enemy.hexproof=ward;g.play_card(card,0);
  assert.equal(enemy.weaken,Math.max(0,3-ward));assert.equal(enemy.decrease_atk,ward<4?1:0);
  assert.equal(enemy.hexproof,0);assert.equal(enemy.hp,100-damage);
  assert.deepEqual(me.can_play,[false,true,true]);
  assert.equal(me.get_next_playable_idx(2),1);assert.equal(e.metadata().events.length,1);
  g.play_card(card,1);assert.deepEqual(me.can_play,[false,true,true]);
  assert.equal(e.metadata().events.length,1);assert.equal(enemy.hp,100-2*damage);
  // Re-entering the boundary cannot rearm a consumed once-per-battle marker.
  g.do_plant_start_permanent_buffs();g.play_card(card,1);assert.equal(e.metadata().events.length,1);
  assert.equal(g.used_randomness,false);scenarios++;
}
// Footwork repeats, gives14 rather than a guessed15, and never consumes cards.
for(const card of ['601011','601012','601013']) {
  const [g,e]=fresh([[5004],[]],[0,1],[card,card,card]);
  g.play_card(card,0);g.play_card(card,0);
  assert.equal(g.players[0].agility,28);assert.deepEqual(g.players[0].can_play,[true,true,true]);
  assert.equal(e.metadata().events.length,2);assert.equal(e.metadata().remaining[0].footwork_active,true);scenarios++;
}
// Ordinary identity, rather than attack damage, selects the hook.
{
  const [g,e]=fresh([[5004,5011],[]],[0,1],['111011','601011','601011']);
  g.play_card('111011',0);assert.equal(e.metadata().events.length,0);
  g.play_card('601011',1);
  assert.deepEqual(e.metadata().events.map(x=>x.effect_id),[5004,5011]);
  assert.equal(g.players[0].agility,14);assert.deepEqual(g.players[0].can_play,[true,false,true]);scenarios++;
}
// Marking a card consumed does not cancel its repeat execution in this play.
{
  const [g,e]=fresh();g.players[0].strike_twice_stacks=1;g.play_card('601011',0);
  assert.equal(g.players[1].hp,94);assert.equal(e.metadata().events.length,1);scenarios++;
}
// All cards consumed uses the native normal-attack fallback; marker stays spent.
{
  const [g,e]=fresh();g.players[0].can_play[1]=false;g.players[0].can_play[2]=false;
  g.play_card('601011',0);
  assert.deepEqual(g.players[0].can_play,[false,false,false]);assert.equal(g.players[0].get_next_playable_idx(0),0);
  g.play_card('601011',0);assert.equal(e.metadata().events.length,1);assert.equal(g.players[1].hp,94);scenarios++;
}
// Owner follows stable identity through initiative swaps.
{
  const [g,e]=fresh([[5011],[]],[1,0]);g.play_card('601011',0);assert.equal(e.metadata().events.length,0);
  g.swap_players();g.do_plant_start_permanent_buffs();g.play_card('601011',0);
  assert.equal(e.metadata().events[0].player_index,0);assert.equal(g.players[1].weaken,3);scenarios++;
}
// Unknown temporary identity rejects before consuming a parent or adding buffs.
{
  const [g,e]=fresh([[5004,5011],[]]);g.players[0].trigger_depth=1;
  assert.throws(()=>g.trigger_card('601011',0),/normal_attack_card_identity_unresolved:5011/);
  assert.equal(g.players[0].agility,0);assert.equal(g.players[1].weaken,0);
  assert.deepEqual(g.players[0].can_play,[true,true,true]);assert.equal(e.metadata().events.length,0);scenarios++;
}
// Footwork has no card-removal identity requirement and also runs on a
// temporary ordinary execution; no falsely consumed reference slot.
{
  const [g,e]=fresh([[5004],[]]);g.players[0].trigger_depth=1;g.trigger_card('601011',0);
  assert.equal(g.players[0].agility,14);assert.deepEqual(g.players[0].can_play,[true,true,true]);
  assert.equal(e.metadata().events[0].trigger_depth,2);scenarios++;
}
// Exact no-owner state/log regression.
{
  const [g]=fresh([[],[]]);const h=new GameState(undefined,undefined,'normal-attack-v28');
  for(const p of h.players){p.hp=100;p.max_hp=100;p.cards=['601011','601011','601011'];p.post_deck_setup();}
  h.do_plant_start_permanent_buffs();g.play_card('601011',0);h.play_card('601011',0);
  assert.deepEqual(g.players,h.players);assert.deepEqual(g.output,h.output);scenarios++;
}
for(const value of [null,{}, {players:[[]]}, {players:[[5011,5011],[]]}, {players:[[5001],[]]},
  {players:[['5011'],[]]}, {players:[[5011],[]],winner:0}]) {
  assert.throws(()=>installCurrentNormalAttack(root,new GameState(),value,[0,1]),/ownership/);scenarios++;
}
process.stdout.write(JSON.stringify({passed:true,scenarios}));
