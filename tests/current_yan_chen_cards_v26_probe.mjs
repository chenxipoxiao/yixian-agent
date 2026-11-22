import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installCurrentYanChen} from '../tools/current_yan_chen_cards_v26.mjs';
import {installCurrentQiPayment} from '../tools/current_qi_payment_v15.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));
await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const bases=['623011','623012','623013'],furies=['625021','625022','625023'];
const frozen=[...bases,...furies].map(id=>swogi[id].card_actions);
const scenarios=[];
function fresh(cards,patch=true) {
  const g=new GameState(undefined,undefined,'yan-chen-software-v26');
  for(const p of g.players) {
    Object.assign(p,{cards:[...cards],hp:1000,max_hp:1000,qi:0,def:0});
    p.reset_can_play();
  }
  installCurrentQiPayment(g);
  if(patch)installCurrentYanChen(root,swogi,g);
  return g;
}
for(const [tier,id] of furies.entries()) {
  for(const thunder of [false,true]) {
    const g=fresh([id,thunder?'125042':'601011','601011']);
    const events=[];
    const gain=g.increase_idx_qi.bind(g),flaw=g.add_enemy_c_of_x.bind(g),chase=g.chase.bind(g);
    g.increase_idx_qi=(idx,n)=>{events.push('qi');assert.equal(g.players[1].flaw,0);return gain(idx,n);};
    g.add_enemy_c_of_x=(n,key)=>{if(key==='flaw'){events.push('flaw');assert.equal(g.players[0].qi,[1,1,2][tier]);}return flaw(n,key);};
    g.chase=()=>{events.push('chase');assert.equal(g.players[1].flaw,tier+1);return chase();};
    g.play_card(id,0);
    assert.equal(g.players[0].qi,[1,1,2][tier]);assert.equal(g.players[1].flaw,tier+1);
    assert.equal(g.players[0].this_card_chases,thunder?1:0);
    assert.deepEqual(events,thunder?['qi','flaw','chase']:['qi','flaw']);
    assert.equal(g.players[0].hp,1000);assert.equal(g.players[1].hp,1000);
    assert.equal(g.used_randomness,false);scenarios.push(`fury-${tier}-${thunder}`);
  }
}
for(const [tier,id] of bases.entries()) {
  for(const initial of [0,2]) {
    const g=fresh([id,'601011','601011']);g.players[0].hexagram=initial;
    g.play_card(id,0);
    assert.equal(g.players[0].hexagram,initial+[1,3,5][tier]);
    assert.equal(g.players[0].ultimate_hexagram_base_stacks,1);
    assert.equal(g.players[0].can_play[0],false);
    g.do_ultimate_hexagram_base();assert.equal(g.players[0].hexagram,initial+[1,3,5][tier]+1);
    g.do_ultimate_hexagram_base();assert.equal(g.players[0].hexagram,initial+[1,3,5][tier]+2);
    assert.equal(g.players[0].qi,0);assert.equal(g.used_randomness,false);
    scenarios.push(`base-${tier}-${initial}`);
  }
}
// Qi from Fury pays the immediately requested next card, without a gathering action.
{
  const g=fresh(['625021','125042','601011']);g.players[0].hexagram=5;g.sim_turn();
  assert.equal(g.players[0].qi,0);assert.equal(g.players[0].hexagram,0);
  assert.equal(g.players[1].hp,930);assert.equal(g.players[0].next_card_index,2);
  assert.equal(g.used_randomness,false);scenarios.push('qi-pays-chased-five-thunders');
}
// A blocked chase keeps its qi gain; the scheduler, not the card body, consumes entangle.
{
  const g=fresh(['625021','125042','601011']);g.players[0].hexagram=5;g.players[0].entangle=1;g.sim_turn();
  assert.equal(g.players[0].qi,1);assert.equal(g.players[1].hp,1000);
  assert.equal(g.players[0].hexagram,5);assert.equal(g.players[0].next_card_index,1);
  assert.equal(g.players[0].entangle,0);scenarios.push('entangle-retains-qi');
}
{
  const g=fresh(['625021','125042','601011']);g.players[0].max_chases=0;g.sim_turn();
  assert.equal(g.players[0].qi,1);assert.equal(g.players[1].hp,1000);
  assert.equal(g.players[0].next_card_index,1);scenarios.push('chase-limit-retains-qi');
}
{
  const g=fresh(['625021','601011','601011']);g.play_card('625021',0);g.play_card('625021',0);
  assert.equal(g.players[0].qi,2);assert.equal(g.players[1].flaw,2);scenarios.push('repeat-fury');
}
{
  const g=fresh(['625021','601011','601011']);g.players[0].cards[0]='625023';g.play_card('625023',0);
  assert.equal(g.players[0].qi,2);assert.equal(g.players[1].flaw,3);scenarios.push('actual-played-level');
}
{
  const g=fresh(['623011','623012','601011']);g.play_card('623011',0);g.play_card('623012',1);
  assert.equal(g.players[0].hexagram,4);assert.equal(g.players[0].ultimate_hexagram_base_stacks,2);
  g.do_ultimate_hexagram_base();assert.equal(g.players[0].hexagram,6);scenarios.push('two-base-copies');
}
{
  const g=fresh(['625021','625022','601011']);g.play_card('625021',0);
  assert.equal(g.players[0].this_card_chases,1);scenarios.push('another-fury-counts-as-thunder');
}
// Per-instance wrapper does not replace the pinned global functions or contaminate other games.
{
  const g=fresh(['625021','601011','601011'],false);g.play_card('625021',0);
  assert.equal(g.players[0].qi,0);
  const b=fresh(['623011','601011','601011'],false);b.play_card('623011',0);
  assert.equal(b.players[0].hexagram,0);
  assert.deepEqual([...bases,...furies].map(id=>swogi[id].card_actions),frozen);
  const plain=fresh(['601011','601011','601011']),native=fresh(['601011','601011','601011'],false);
  plain.play_card('601011',0);native.play_card('601011',0);
  for(const key of ['hp','qi','def','hexagram','this_card_chases'])for(const seat of [0,1])assert.equal(plain.players[seat][key],native.players[seat][key]);
  scenarios.push('global-and-other-game-isolation');
}
process.stdout.write(JSON.stringify({passed:true,scenarios}));
