import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerElementFlag,installElementFlag} from '../tools/current_element_flag_v62r2.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerElementFlag(root,swogi);assert.throws(()=>registerElementFlag(root,swogi),/alias_collision/);
let scenarios=0;
function fresh(hand,grade=1,slot=0) {
 const g=new GameState(undefined,undefined,'flag-boundaries');
 for(const p of g.players){p.character='sw1';p.hp=400;p.max_hp=400;p.max_physique=100;p.cards=['601011','601011','601011'];p.hand_count=0;}
 const id='76200'+grade;g.players[0].cards[slot]=id;g.players[0].hand_count=hand.length;
 const o=installElementFlag(root,g,swogi,{hands:[null,hand]},[1,0]);g.start_of_game_setup();return {g,p:g.players[0],q:g.players[1],o,id,slot};
}
for(const base of [7000036,7000031,7000023,7000016,7000029])for(let flag=1;flag<=3;flag++)for(let rank=1;rank<=3;rank++){
 const raw=base+10000*(rank-1),hand=[0,raw,7020023];const {g,p,o,id}=fresh(hand,flag);
 g.play_card(id,0);const e=o.metadata().events[0];assert.equal(e.formation.source_raw,raw);assert.equal(e.formation.raw,base+10000*(Math.min(rank,flag)-1));
 assert.equal(p.hp,390);assert.equal(p.this_card_chases,1);assert.equal(e.restored_runtime,id);assert.equal(p.cards[0],id);assert.equal(p.can_play[0],true);assert.equal(e.player_index,1);assert.deepEqual(hand,[0,raw,7020023]);scenarios++;
}
for(const base of [7000003,7000009,7000011,7000001,7000006])for(let rank=1;rank<=3;rank++){
 const raw=base+10000*(rank-1),{g,p,o,id}=fresh([7020023,raw,7000006],1,1);
 g.play_card(id,1);const e=o.metadata().events[0];assert.equal(e.formation.raw,7000023);assert.equal(e.seal.raw,raw);assert.equal(p.hp,400);assert.equal(p.this_card_chases,0);assert.equal(p.can_play[1],true);scenarios++;
}
// No candidate is a known empty hand, not unknown. Odd cost/chase still happens.
for(const slot of [0,1]){const {g,p,o,id}=fresh([],1,slot);g.play_card(id,slot);assert.equal(p.hp,slot===0?390:400);assert.equal(o.metadata().events[0].formation,null);scenarios++;}
// Repeated uses stack the formation but do not consume the borrowed continuous card or flag.
{const {g,p,id,o}=fresh([7000023]);g.play_card(id,0);g.play_card(id,0);assert.equal(p.earth_spirit_formation_stacks,4);assert.equal(p.can_play[0],true);assert.equal(o.metadata().events.length,2);scenarios++;}
// User-confirmed dream target is first; never silently switch to the later ordinary formation.
{const {g,p,id}=fresh([7040090,7000031]);assert.throws(()=>g.play_card(id,0),/unmapped_first_formation:7040090/);assert.equal(p.hp,400);assert.equal(p.fire_spirit_formation_stacks,0);scenarios++;}
// A third-level seal has no flag-grade cap; an unrelated unmapped hand card does not block selection.
{const {g,o,id}=fresh([2000015,7000023,7020009],1,1);g.play_card(id,1);assert.equal(o.metadata().events[0].seal.raw,7020009);scenarios++;}
// A flag nested through another card lacks proven grid identity and stops.
{const {g,p,id}=fresh([7000023]);p.trigger_depth=1;assert.throws(()=>g.trigger_card(id,0),/nested_slot_identity/);scenarios++;}
// Temporary formations use ordinary hooks: existing earth formation triggers before its new layers.
{const {g,p,id}=fresh([7000023]);p.earth_spirit_formation_stacks=2;g.play_card(id,0);assert.equal(p.def,6);assert.equal(p.earth_spirit_formation_stacks,4);scenarios++;}
console.log(JSON.stringify({passed:true,scenarios}));
