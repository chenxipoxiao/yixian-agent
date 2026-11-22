import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installCurrentEngravings} from '../tools/current_engraving_effects_v21.mjs';
import {installCurrentQiPayment} from '../tools/current_qi_payment_v15.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const facts=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-engraving-effects-v21.json')));
let checked=0;
function fresh(raw=[1000004,1000004,1000004],effects=[[{strategy_id:13003,slot:0}],[]],configure=()=>{}) {
 const g=new GameState(undefined,undefined,'boundary-v21');
 const decks=[raw,[0,0,0]];
 for(let i=0;i<2;i++)Object.assign(g.players[i],{cards:decks[i].map(id=>facts.transform_cards[id].runtime_id),hp:1000,max_hp:1000,qi:20,def:0});
 for(const p of g.players)p.reset_can_play();
 installCurrentQiPayment(g);configure(g);
 const l=installCurrentEngravings(root,g,{players:effects},[0,1],{players:decks},swogi);
 return [g,l];
}
function cursed(raw,effects=[],configure=()=>{}) {
 const [g,l]=fresh(raw,[effects,[{strategy_id:13007,slot:0}]],configure);
 g.players.reverse();g.play_card_inner('601011',0);g.players.reverse();
 assert.equal(l.pendingFor(g.players[0])[560],1);
 return [g,l];
}
function executeSlot(g,idx) {
 g.do_finishing_touch(idx);g.do_spirit_fusion_pot(idx);g.play_card_inner(g.players[0].cards[idx],idx);
}
// The slot engraving upgrades the first played card before its effect runs.
{
 const [g,l]=fresh();const start=g.players[0].qi;executeSlot(g,0);
 assert.equal(g.players[0].cards[0],'111042');assert.equal(g.players[0].qi,start+2);
 assert.equal(l.forPlayer(g.players[0])[0].used,true);executeSlot(g,0);
 assert.equal(g.players[0].cards[0],'111042');checked++;
}
// Off-slot, already-used, hidden and noUpgrade cards do not activate13003.
for(const [raw,slot,used] of [[1000004,1,false],[1000004,0,true],[0,0,false],[1020004,0,false]]) {
 const [g,l]=fresh([raw,0,0],[[{strategy_id:13003,slot}],[]]);
 g.players[0].can_post_action[0]=used;g.do_finishing_touch(0);
 assert.equal(g.players[0].cards[0],facts.transform_cards[raw].runtime_id);
 assert.equal(l.forPlayer(g.players[0])[0].used,false);checked++;
}
// Full native turn: payment stays at the original tier, then the current
// card effect uses the upgraded tier. Chord In Tune costs2->1.
{
 const [g]=fresh([5000012,0,0]);g.sim_turn();
 assert.equal(g.players[0].cards[0],'334032');assert.equal(g.players[0].qi,18);checked++;
}
// Native doubleplay executes the transformed effect twice, not two upgrades.
{
 const [g]=fresh();g.players[0].strike_twice_stacks=1;g.sim_turn();
 assert.equal(g.players[0].cards[0],'111042');assert.equal(g.players[0].qi,24);checked++;
}
// 13003 precedes the independent281 Finishing Touch global counter.
{
 const [g]=fresh();g.players[0].finishing_touch_stacks=1;g.do_finishing_touch(0);
 assert.equal(g.players[0].cards[0],'111043');assert.equal(g.players[0].finishing_touch_stacks,0);checked++;
}
// Player ownership survives seat changes. First-tier card keeps560;
// the next eligible card consumes exactly one downgrade.
{
 const [g,l]=cursed([1000004,1010004,1020004]);g.do_spirit_fusion_pot(0);
 assert.equal(l.pendingFor(g.players[0])[560],1);g.do_spirit_fusion_pot(1);
 assert.equal(g.players[0].cards[1],'111041');assert.equal(l.pendingFor(g.players[0])[560],0);
 g.do_spirit_fusion_pot(2);assert.equal(g.players[0].cards[2],'111043');checked++;
}
// Incoming560 follows the engraving upgrade. A level1 card returns to1.
{
 const [g,l]=cursed([1000004,0,0],[{strategy_id:13003,slot:0}]);executeSlot(g,0);
 assert.equal(g.players[0].cards[0],'111041');assert.equal(l.pendingFor(g.players[0])[560],0);
 assert.equal(l.forPlayer(g.players[0])[0].used,true);checked++;
}
// User-confirmed: max-level13003 does nothing on first use, is downgraded,
// and does NOT activate on the next use of that same slot.
{
 const [g,l]=cursed([1020004,0,0],[{strategy_id:13003,slot:0}]);executeSlot(g,0);
 assert.equal(g.players[0].cards[0],'111042');assert.equal(l.forPlayer(g.players[0])[0].used,false);
 executeSlot(g,0);assert.equal(g.players[0].cards[0],'111042');checked++;
}
// User-confirmed:281 belongs to the player, not a grid. Full tier skips281
// without spending it, then560 downgrades. The next eligible DIFFERENT
// slot is upgraded and spends281. No native Finishing Touch rewrite needed.
{
 const [g,l]=cursed([1020004,1000004,0]);g.players[0].finishing_touch_stacks=1;executeSlot(g,0);
 assert.equal(g.players[0].cards[0],'111042');assert.equal(g.players[0].finishing_touch_stacks,1);
 assert.equal(l.pendingFor(g.players[0])[560],0);executeSlot(g,1);
 assert.equal(g.players[0].cards[1],'111042');assert.equal(g.players[0].finishing_touch_stacks,0);checked++;
}
// Both281 and560 spend on an initially upgradeable card, upgrade first.
{
 const [g,l]=cursed([1000004,0,0]);g.players[0].finishing_touch_stacks=1;executeSlot(g,0);
 assert.equal(g.players[0].cards[0],'111041');assert.equal(g.players[0].finishing_touch_stacks,0);
 assert.equal(l.pendingFor(g.players[0])[560],0);checked++;
}
// Native432 pot happens before560; a level2->1 pot downgrade leaves560.
{
 const [g,l]=cursed([1010004,0,0]);g.players[0].spirit_fusion_pot_stacks=1;
 g.do_spirit_fusion_pot(0);assert.equal(g.players[0].cards[0],'111041');
 assert.equal(l.pendingFor(g.players[0])[560],1);assert.equal(g.players[0].hp,997);checked++;
}
// Raw19 is specifically exempt, although it shares its runtime alias with
// raw20019. Unmapped10019 is rejected, never guessed or treated as19.
{
 const [g,l]=cursed([19,0,0]);g.do_spirit_fusion_pot(0);
 assert.equal(g.players[0].cards[0],'611033');assert.equal(l.pendingFor(g.players[0])[560],1);checked++;
}
{
 const [g,l]=cursed([20019,0,0]);assert.throws(()=>g.do_spirit_fusion_pot(0),/unmapped_target:10019/);
 assert.equal(l.pendingFor(g.players[0])[560],1);checked++;
}
{
 const [g]=cursed([19,0,0]);g.players[0].spirit_fusion_pot_stacks=1;
 assert.throws(()=>g.do_spirit_fusion_pot(0),/unverified_native_pot_raw19/);checked++;
}
{
 const [g]=cursed([1010004,0,0]);g.players[0].cards[0]='611033';
 assert.throws(()=>g.do_spirit_fusion_pot(0),/ambiguous_or_unknown_runtime/);checked++;
}
// Temporary execution neither arms13007 nor consumes incoming560.
{
 const [g,l]=fresh([1010004,0,0],[[{strategy_id:13007,slot:0}],[]]);
 g.players[0].trigger_depth=1;g.trigger_card('111042',0);
 assert.equal(l.pendingFor(g.players[1])[560],0);g.players[0].trigger_depth=0;
 g.play_card_inner('111042',0);assert.equal(l.pendingFor(g.players[1])[560],1);
 g.play_card_inner('111042',0);assert.equal(l.pendingFor(g.players[1])[560],1);checked++;
}
{
 const [g,l]=cursed([1010004,0,0]);g.players[0].trigger_depth=1;g.trigger_card('111042',0);
 assert.equal(g.players[0].cards[0],'111042');assert.equal(l.pendingFor(g.players[0])[560],1);checked++;
}
// Raw identity and ownership must be explicit; frozen alias ambiguity is
// not resolved by deck results or arbitrary input metadata.
for(const input of [undefined,{players:[[19,0,0],[0,0,0]]},{players:[[1000004,0],[0,0,0]]}]) {
 const g=new GameState();g.players[0].cards=['111041','601011','601011'];g.players[1].cards=['601011','601011','601011'];
 assert.throws(()=>installCurrentEngravings(root,g,{players:[[{strategy_id:13003,slot:0}],[]]},[0,1],input,swogi));checked++;
}
assert.throws(()=>installCurrentEngravings(root,new GameState(),undefined,[0,1],{players:[[],[]]},swogi));checked++;
console.log(JSON.stringify({passed:true,checked}));
