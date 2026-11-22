import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerCurrentCloudCards} from '../tools/current_cloud_cards_v5.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));
await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const originals={...swogi};
registerCurrentCloudCards(root,swogi);
for(const id of Object.keys(originals)) assert.strictEqual(swogi[id],originals[id]);
const checked=[];
function fresh(fields={}) {
  const game=new GameState(undefined,undefined,'software-current-cards');
  Object.assign(game.players[0],{cards:['601011','601011','601011'],hp:40,max_hp:40,qi:0,def:0,
    physique:0,max_physique:6,currently_playing_card_idx:0,currently_triggering_card_idx:0},fields);
  Object.assign(game.players[1],{cards:['601011','601011','601011'],hp:100,max_hp:100});
  return game;
}
for(let grade=0;grade<3;grade++) {
  const sea=String(114911+grade),float=String(115911+grade),body=String(142911+grade);
  assert.equal(swogi[sea].is_cloud_sword,true);assert.equal(swogi[sea].is_sword,true);
  assert.equal(swogi[float].is_cloud_sword,false);assert.equal(swogi[float].is_sword,false);
  assert.equal(swogi[body].is_add_physique,true);assert.equal(swogi[body].marking,'dx');
  assert.equal(swogi[sea].is_add_qi,true);assert.equal(swogi[float].is_add_qi,true);
  for(const [chain,endurance] of [[0,0],[2,0],[0,1]]) {
    const g=fresh({cloud_sword_chain_count:chain,endurance_as_cloud_sea_stacks:endurance,currently_triggering_card_id:sea});
    swogi[sea].card_actions(g);g.do_cloud_sword_chain_count(sea);
    const increment=(chain>0 || endurance>0 ? grade+1 : 0)+1;
    assert.equal(g.players[0].cloud_sword_chain_count,chain+increment);
    assert.equal(g.players[0].cloud_sword_used_count,increment);
    assert.equal(g.players[0].cloud_sea,2);assert.equal(g.players[0].qi,3+grade);
    checked.push({test:'cloud_and_cumulative',grade,chain,endurance});
  }
  const odd=fresh({hp:35,qi:4});swogi[float].card_actions(odd);
  assert.equal(odd.players[0].hp,40);
  assert.equal(odd.players[0].def,12+5*(grade+1)-5);
  odd.do_cloud_sword_chain_count(float);
  assert.equal(odd.players[0].cloud_sea,2+grade);
  assert.equal(odd.players[0].cloud_sword_chain_count,1);
  assert.equal(odd.players[0].cloud_sword_used_count,1);
  const even=fresh({hp:35,currently_playing_card_idx:0,currently_triggering_card_idx:1});
  swogi[float].card_actions(even);
  assert.equal(even.players[0].hp,35);assert.equal(even.players[0].def,0);
  assert.equal(even.players[0].agility,10+3*grade);
  for(const physique of [0,5,9]) {
    const g=fresh({hp:30,physique});swogi[body].card_actions(g);
    assert.equal(g.players[0].physique,physique+2+grade);
    assert.equal(g.players[0].max_hp,42+grade);
    assert.equal(g.players[0].hp,30+Math.min(2+grade,Math.max(0,physique+2+grade-6)));
    assert.equal(g.players[0].qi,1+grade);assert.equal(g.players[0].increase_atk,1);
  }
  checked.push({test:'parity_and_physique',grade});
}
// Missing health 3, nominal heal 22. Modifiers act on 3, not on 22.
for(const extra of [{indigestion:2},{prevent_gain_hp_stacks:1},{p2_rejuvenation_stacks:1}]) {
  const g=fresh({hp:37,qi:4,...extra});swogi['115912'].card_actions(g);
  assert.equal(g.players[0].def,19);
  assert.equal(g.players[0].hp,extra.indigestion?38:extra.prevent_gain_hp_stacks?37:40);
  checked.push({test:'pre_heal_split',extra});
}
const full=fresh({qi:4,appetite:10});swogi['115912'].card_actions(full);
assert.equal(full.players[0].hp,40);assert.equal(full.players[0].def,22);
const malformed=fresh({currently_triggering_card_idx:undefined});
assert.throws(()=>swogi['115911'].card_actions(malformed),/triggered card slot/);
assert.equal(malformed.players[0].qi,0);
assert.throws(()=>registerCurrentCloudCards(root,swogi),/alias collision/);
console.log(JSON.stringify({checked,old_entries_unchanged:Object.keys(originals).length,passed:true}));
