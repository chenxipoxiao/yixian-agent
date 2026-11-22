import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerCurrentChainCards,installCurrentChainMethods} from '../tools/current_chain_cards_v11.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const originals={...swogi};registerCurrentChainCards(root,swogi);
for(const id of Object.keys(originals))assert.strictEqual(swogi[id],originals[id]);
function fresh(card) {
  const g=new GameState(undefined,undefined,'fixed-software-chain');
  for(const p of g.players)Object.assign(p,{cards:[card,'601011','601011'],hp:10000,max_hp:10000,qi:0,def:0});
  installCurrentChainMethods(g,swogi);g.start_of_game_setup();return g;
}
let checked=0;
for(let grade=0;grade<3;grade++)for(const prior of [0,1]) {
  const id=String(612921+grade),g=fresh(id),p=g.players[0];
  p.cloud_sword_chain_count=prior;
  g.play_card(id,0);
  assert.equal(p.unrestrained_sword_count,1);
  const n=prior?grade+2:1;
  assert.equal(p.m_light_sword_stacks,n);
  for(let j=0;j<n;j++)g.play_card('601011',1);
  assert.equal(p.m_light_sword_stacks,0);assert.equal(p.unrestrained_sword_count,1+n);
  assert.equal(p.cloud_sword_chain_count,prior+1+n);
  g.play_card('601011',2);assert.equal(p.cloud_sword_chain_count,0);checked++;
}
for(let grade=0;grade<3;grade++) {
  const id=String(144941+grade),g=fresh(id);
  g.play_card(id,0);assert.equal(g.players[1].flaw,0);
  assert.equal(g.players[0].agility,5+grade);
  g.play_card('601011',1);assert.equal(g.players[1].flaw,0);
  // Continue consumes neither the pending next-crash effect nor its old charges.
  g.do_pre_crash_fist('144031');
  assert.equal(g.players[1].flaw,1);
  g.do_pre_crash_fist('141011');assert.equal(g.players[1].flaw,2);
  g.do_pre_crash_fist('141011');assert.equal(g.players[1].flaw,2);checked++;
}
console.log(JSON.stringify({passed:true,checked,original_entries_unchanged:Object.keys(originals).length}));
