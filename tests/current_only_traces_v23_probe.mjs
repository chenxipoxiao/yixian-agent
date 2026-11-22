import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installCurrentOnlyTraces} from '../tools/current_only_traces_v23.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));
await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const frozenActions=['622011','622012','622013'].map(id=>swogi[id].card_actions);
let scenarios=0;
function fresh(id,patch=true) {
  const game=new GameState(undefined,undefined,'only-traces-software-v23');
  for(const p of game.players) {
    Object.assign(p,{cards:[id,'601011','601011'],hp:100,max_hp:100,qi:0,def:0});
    p.reset_can_play();
  }
  if(patch)installCurrentOnlyTraces(root,swogi,game);
  return game;
}
for(const [tier,id] of ['622011','622012','622013'].entries()) {
  for(const post of [false,true]) {
    const g=fresh(id);g.players[0].can_post_action[0]=post;
    g.play_card(id,0);
    assert.equal(g.players[0].hp,tier===0?100:post?99:98);
    assert.equal(g.players[0].qi,tier===2?4:3);
    assert.equal(g.players[0].this_card_chases,tier>0||post?1:0);
    assert.equal(g.players[0].max_hp,100);
    assert.equal(g.players[1].hp,100);
    assert.equal(g.used_randomness,false);scenarios++;
  }
}
// Post-action becomes available after using the actual card slot once.
{
  const g=fresh('622012');g.play_card('622012',0);g.play_card('622012',0);
  assert.equal(g.players[0].hp,97);assert.equal(g.players[0].qi,6);scenarios++;
}
// Native HP callbacks stay in charge: non-cost self reduction can consume guard.
{
  const g=fresh('622012');g.players[0].guard_up=1;g.play_card('622012',0);
  assert.equal(g.players[0].guard_up,0);assert.equal(g.players[0].hp,100);
  assert.equal(g.players[0].this_card_chases,1);scenarios++;
}
// A later heal can absorb earlier differences; do not add six to a terminal HP.
{
  const g=fresh('622012');g.play_card('622012',0);g.play_card('622012',0);
  g.increase_idx_hp(0,8);assert.equal(g.players[0].hp,100);
  g.play_card('622012',0);assert.equal(g.players[0].hp,99);scenarios++;
}
// Select by actual played identity, including an upgrade/downgrade at the slot.
{
  const g=fresh('622011');g.players[0].cards[0]='622013';g.play_card('622013',0);
  assert.equal(g.players[0].hp,98);assert.equal(g.players[0].qi,4);scenarios++;
}
// Ordinary cards and other games retain their native functions and behaviour.
{
  const patched=fresh('601011'),native=fresh('601011',false);
  patched.play_card('601011',0);native.play_card('601011',0);
  for(const key of ['hp','qi','def','this_card_chases']) {
    for(const seat of [0,1])assert.equal(patched.players[seat][key],native.players[seat][key]);
  }
  const old=fresh('622012',false);old.play_card('622012',0);
  assert.equal(old.players[0].hp,96);
  assert.deepEqual(['622011','622012','622013'].map(id=>swogi[id].card_actions),frozenActions);
  scenarios++;
}
process.stdout.write(JSON.stringify({passed:true,scenarios}));
