import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerCurrentSwordCards,installCurrentSwordMethods} from '../tools/current_sword_cards.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));
await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const originals={...swogi};
registerCurrentSwordCards(root,swogi);
for(const id of Object.keys(originals)) assert.strictEqual(swogi[id],originals[id]);
assert.equal(swogi['112901'].is_spirit_sword,true);
assert.equal(swogi['112901'].is_sword_formation,false);
assert.equal(swogi['115901'].is_sword_formation,true);
assert.equal(swogi['115901'].is_spirit_sword,false);
assert.equal(swogi['112901'].marking,'sw');
assert.equal(swogi['112901'].qi_cost,1);
const game=new GameState(undefined,undefined,'boundary');
installCurrentSwordMethods(game);
game.players[0].cards=['112901','112902','601011'];
game.players[0].qi=0;
game.do_opening(0);assert.equal(game.players[0].qi,1);
game.do_opening(1);assert.equal(game.players[0].qi,1);
game.players[0].qi=0;game.do_opening(1);assert.equal(game.players[0].qi,1);
game.players[0].qi=-1;game.do_opening(0);assert.equal(game.players[0].qi,-1);
const trials=[];
for(const defense of [0,4,5,9,10,19]) {
  const hits=[];
  const fake={players:[{def:defense}],atk_replay_count_or_default:(attack,count)=>{
    for(let i=0;i<count;i++){hits.push(attack);fake.players[0].def+=100;}
  }};
  swogi['115901'].card_actions(fake);
  assert.deepEqual(hits,Array(4).fill(1+Math.trunc(defense/5)));
  trials.push({defense,hits});
}
assert.throws(()=>registerCurrentSwordCards(root,swogi),/alias collision/);
console.log(JSON.stringify({old_entries_unchanged:Object.keys(originals).length,
    opening_zero_retrigger_passed:true,defense_snapshot_trials:trials}));
