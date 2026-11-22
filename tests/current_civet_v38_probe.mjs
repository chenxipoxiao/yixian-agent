import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerCivet,installCivet} from '../tools/current_civet_v38.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));registerCivet(root,swogi);
let scenarios=0;
function fresh(id='806141',mirrors=[false,false],order=[0,1],install=true) {
 const g=new GameState(undefined,undefined,'civet-software');
 for(const p of g.players){p.character='sw3';p.hp=100;p.max_hp=100;p.destiny=40;p.cards=[id,'601011','601011'];}
 const x=install?installCivet(root,g,mirrors===undefined?undefined:{is_mirror:mirrors},order):null;
 g.start_of_game_setup();return {g,x};
}
for(const [id,hp,gain] of [['806141',7,3],['806142',11,6],['806143',15,9]])
 for(const mirror of [false,true])for(const start of [40,98,100])for(const order of [[0,1],[1,0]]) {
  const {g,x}=fresh(id,[mirror,mirror],order),p=g.players[0];p.hp=start;
  g.play_card(p.cards[0],0);x.verifyTerminal();
  assert.equal(p.hp,Math.min(100,start+hp));assert.equal(p.destiny,40);assert.equal(p.direct_destiny_lost,0);
  assert.equal(p.can_play[0],false);
  const m=x.metadata();assert.equal(m.events.length,1);assert.equal(m.events[0].player_index,order[0]);
  assert.equal(m.events[0].requested_destiny_gain,mirror?0:gain);assert.equal(m.authoritative_destiny_gain_resolved,false);
  scenarios++;
 }
{
 const {g,x}=fresh();g.players[0].strike_twice_stacks=1;g.play_card(g.players[0].cards[0],0);
 assert.equal(x.metadata().events.length,2);assert.deepEqual(x.metadata().requested_destiny_gains,[6,0]);scenarios++;
}
{
 const {g,x}=fresh('806142',[true,false],[1,0]);g.play_card(g.players[0].cards[0],0);g.swap_players();g.play_card(g.players[0].cards[0],0);
 assert.deepEqual(x.metadata().requested_destiny_gains,[0,6]);scenarios++;
}
{
 const {g,x}=fresh();g.players[0].hp=40;g.players[0].internal_injury=3;
 g.play_card(g.players[0].cards[0],0);assert.equal(x.metadata().events[0].hp_after,47);scenarios++;
}
{
 const {g,x}=fresh();g.play_card(g.players[0].cards[0],0);g.players[1].direct_destiny_lost=1;
 assert.throws(()=>x.verifyTerminal(),/direct_destiny_interaction_required/);scenarios++;
}
{
 const {g,x}=fresh('806141',[true,true]);g.play_card(g.players[0].cards[0],0);g.players[1].direct_destiny_lost=1;
 x.verifyTerminal();assert.deepEqual(x.metadata().requested_destiny_gains,[0,0]);scenarios++;
}
{
 const {g}=fresh('806141',[false,false],[0,1],false);installCivet(root,g,undefined);
 assert.throws(()=>g.play_card(g.players[0].cards[0],0),/explicit_mirror_context_required/);scenarios++;
}
for(const context of [null,{}, {is_mirror:[false]}, {is_mirror:[0,false]}, {is_mirror:[false,null]}]) {
 const {g}=fresh('806141',[false,false],[0,1],false);
 assert.throws(()=>installCivet(root,g,context),/explicit_mirror_context_required/);scenarios++;
}
{
 const {g,x}=fresh();assert.equal(x.metadata(),null);assert.throws(()=>installCivet(root,g,{is_mirror:[false,false]}),/already_installed/);scenarios++;
}
process.stdout.write(JSON.stringify({passed:true,scenarios}));
