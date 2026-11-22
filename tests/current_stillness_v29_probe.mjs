import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerCurrentStillness,installStillnessObserver} from '../tools/current_stillness_v29.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerCurrentStillness(root,swogi);
let scenarios=0;
function fresh(id='125961',observe=true) {
  const g=new GameState(undefined,undefined,'stillness-v29');
  for(const p of g.players){p.hp=40;p.max_hp=100;p.max_physique=100;p.cards=[id,'122091','601011'];p.post_deck_setup();}
  return [g,observe?installStillnessObserver(g,swogi,[0,1]):null];
}
for(let grade=1;grade<=3;grade++) {
  const id='12596'+grade;
  {
    const [g,o]=fresh(id),p=g.players[0];p.qi=9;
    g.play_card(id,0);
    assert.equal(p.hp,40);assert.equal(p.max_hp,120);assert.equal(p.qi,9);
    assert.equal(p.stillness_citta_dharma_stacks,grade);assert.equal(p.this_card_chases,1);
    assert.deepEqual(p.can_play,[false,true,true]);assert.equal(p.get_next_playable_idx(2),1);
    g.increase_idx_qi(0,0);g.reduce_idx_x_by_c(0,'qi',1);assert.equal(p.hp,40);
    g.increase_idx_qi(0,2);assert.equal(p.hp,40+2*grade);
    assert.equal(o.metadata().events.filter(x=>x.kind==='qi_gain_after_card').length,1);scenarios++;
  }
  {
    const [g]=fresh(id),p=g.players[0];g.play_card('122091',1);g.play_card(id,0);
    assert.equal(p.stillness_citta_dharma_stacks,2+grade);
    g.increase_idx_qi(0,3);assert.equal(p.hp,40+3*(2+grade));scenarios++;
  }
  {
    const [g]=fresh(id),p=g.players[0];g.play_card(id,0);p.hp=119;
    g.increase_idx_qi(0,3);assert.equal(p.hp,120);scenarios++;
  }
  {
    const [g]=fresh(id),p=g.players[0];g.play_card(id,0);p.indigestion=2;
    g.increase_idx_qi(0,3);assert.equal(p.hp,40+Math.max(1,3*grade-2));scenarios++;
  }
  {
    const [g]=fresh(id),p=g.players[0];g.play_card(id,0);p.prevent_gain_hp_stacks=1;
    g.increase_idx_qi(0,3);assert.equal(p.hp,40);assert.equal(p.qi,3);scenarios++;
  }
  {
    const [g]=fresh(id),p=g.players[0];g.play_card(id,0);p.colorful_spirit_crane_stacks=1;
    g.increase_idx_qi(0,3);assert.equal(p.qi,6);assert.equal(p.hp,40+6*grade);scenarios++;
  }
  {
    const [g,o]=fresh(id),p=g.players[0];g.play_card(id,0);p.mortal_body_stacks=1;
    g.increase_idx_qi(0,3);assert.equal(p.qi,0);assert.equal(p.physique,3);assert.equal(p.hp,40);
    assert.equal(o.metadata().events.filter(x=>x.kind==='qi_gain_after_card').length,0);scenarios++;
  }
  {
    const [g,o]=fresh(id),p=g.players[0];p.strike_twice_stacks=1;g.play_card(id,0);
    assert.equal(p.max_hp,140);assert.equal(p.stillness_citta_dharma_stacks,2*grade);
    assert.equal(o.metadata().events.filter(x=>x.kind==='card_body').length,2);scenarios++;
  }
}
// Observer must not alter execution, including the output log.
{
  const [a]=fresh('125963',false),[b]=fresh('125963',true);
  for(const g of [a,b]){g.play_card('125963',0);g.increase_idx_qi(0,4);}
  assert.deepEqual(a.players,b.players);assert.deepEqual(a.output,b.output);scenarios++;
}
// Native nested continuous effects do not consume the parent reference slot.
{
  const [g,o]=fresh();g.players[0].trigger_depth=1;g.trigger_card('125961',0);
  assert.equal(g.players[0].max_hp,120);assert.deepEqual(g.players[0].can_play,[true,true,true]);
  assert.equal(o.metadata().events[0].trigger_depth,2);scenarios++;
}
assert.throws(()=>registerCurrentStillness(root,swogi),/alias collision/);scenarios++;
process.stdout.write(JSON.stringify({passed:true,scenarios}));
