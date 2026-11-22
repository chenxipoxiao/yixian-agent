import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installUpgradeSound,planUpgradeSound} from '../tools/current_upgrade_sound_v41.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const facts=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-upgrade-sound-v41.json')));
const entry={strategy_id:1009,enabled:true},disabled={strategy_id:1009,enabled:false};let scenarios=0;
const boards=[[1000001,1000002,1000003,1000004],[0,1010001,1020002,0]];
function fresh(raw=boards,order=[0,1]) {
 const g=new GameState(undefined,undefined,'upgrade-sound-software');
 g.players.forEach((p,i)=>Object.assign(p,{character:'sw3',hp:100,max_hp:100,max_physique:100,
  cards:raw[order[i]].map(id=>facts.metadata[id].runtime_id),hand_count:0}));return g;
}
for(const order of [[0,1],[1,0]])for(const owners of [[entry,null],[null,entry],[entry,entry]]) {
 const g=fresh(boards,order),value={players:owners,raw_boards:boards},saved=structuredClone(value);
 const ordinary=g.apply_p1_fates_setup.bind(g),seen=[];
 g.apply_p1_fates_setup=idx=>{seen.push([...g.players[idx].cards]);return ordinary(idx);};
 const m=installUpgradeSound(root,g,swogi,value,order);assert.deepEqual(value,saved);
 assert.deepEqual(g.players[0].cards,boards[order[0]].map(id=>facts.metadata[id].runtime_id));
 g.start_of_game_setup();
 const expected=[[1000001,1020002,1020003,1020004],[0,1020001,1020002,0]];
 assert.deepEqual(g.players.map(p=>p.cards),order.map(i=>expected[i].map(id=>facts.metadata[id].runtime_id)));
 assert.deepEqual(seen,g.players.map(p=>p.cards));
 assert.deepEqual(m.metadata().events.map(e=>e.player_index),order);
 assert.equal(m.metadata().events.flatMap(e=>e.upgrades).length,7);
 g.start_of_game_setup();assert.equal(m.metadata().events.length,2);
 assert.deepEqual(value,saved);assert.throws(()=>installUpgradeSound(root,g,swogi,value,order),/already_installed/);scenarios++;
}
for(const owners of [[disabled,null],[null,disabled],[disabled,disabled]]) {
 const g=fresh(),before=g.players.map(p=>[...p.cards]),m=installUpgradeSound(root,g,swogi,{players:owners,raw_boards:boards});
 g.start_of_game_setup();assert.deepEqual(g.players.map(p=>p.cards),before);assert.equal(m.metadata().enabled,false);scenarios++;
}
for(let n=1;n<=8;n++) {
 const board=Array(n).fill(1000001),plan=planUpgradeSound(board,facts.metadata,swogi);
 assert.deepEqual(plan.after,Array(Math.max(0,n-3)).fill(1000001).concat(Array(Math.min(n,3)).fill(1020001)));
 assert.deepEqual(board,Array(n).fill(1000001));scenarios++;
}
// A synthetic noUpgrade intermediate checks the actual client branch, not an
// observed current card. Production cannot receive this metadata override.
{
 const synthetic={1:{rarity:0,hidden:false,no_upgrade:false,runtime_id:'a',upgrade_raw_id:10001},
  10001:{rarity:1,hidden:false,no_upgrade:true,runtime_id:'b',upgrade_raw_id:20001}};
 const p=planUpgradeSound([1],synthetic,{b:{card_actions(){}}});assert.deepEqual(p.after,[10001]);assert.equal(p.events.length,1);scenarios++;
}
// A hidden or non-upgradeable card is skipped without replacing its slot.
{
 const synthetic={1:{rarity:0,hidden:false,no_upgrade:true},2:{rarity:0,hidden:true,no_upgrade:false}};
 assert.deepEqual(planUpgradeSound([1,2],synthetic,{}).after,[1,2]);scenarios++;
}
{
 const g=fresh(),before=g.players.map(p=>[...p.cards]);
 const withoutTarget={...swogi};delete withoutTarget[facts.metadata[1020004].runtime_id];
 assert.throws(()=>installUpgradeSound(root,g,withoutTarget,{players:[entry,null],raw_boards:boards}),/missing_upgrade_implementation/);
 assert.deepEqual(g.players.map(p=>p.cards),before);scenarios++;
}
{
 const g=fresh();installUpgradeSound(root,g,swogi,{players:[entry,null],raw_boards:boards});
 g.players[0].cards[0]='111013';assert.throws(()=>g.start_of_game_setup(),/earlier_deck_transform_pending/);scenarios++;
}
for(const value of [null,{}, {players:[entry],raw_boards:boards},{players:[{strategy_id:1009},null],raw_boards:boards},
 {players:[entry,null],raw_boards:[[999],boards[1]]}]) {
 assert.throws(()=>installUpgradeSound(root,fresh(),swogi,value),/upgrade_sound_unresolved/);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios}));
