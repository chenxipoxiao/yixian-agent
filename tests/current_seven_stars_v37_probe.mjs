import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installSevenStars} from '../tools/current_seven_stars_v37.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const entry=n=>({strategy_id:7056,unlocked_slots:n});let scenarios=0;
function fresh(n=3,owned=[true,false],order=[0,1]) {
 const g=new GameState(undefined,undefined,'seven-stars-software');
 for(const p of g.players){p.character='sw3';p.hp=1000;p.max_hp=1000;p.cards=Array(n).fill('121031');}
 const x=installSevenStars(root,g,{players:owned.map(b=>b?entry(n):null)},order);g.start_of_game_setup();return {g,x};
}
//Actual native card bodies: every valid grid, both directions, short/full boards.
for(const n of [3,4,5,6,7,8])for(const dir of [1,-1])for(let slot=0;slot<n;slot++) {
 const {g,x}=fresh(n),p=g.players[0];p.card_play_direction=dir;
 const next=(slot+dir+n)%n,already=p.is_star_point[next],qi=p.qi;
 g.play_card(p.cards[slot],slot);
 const e=x.metadata().events[0];assert.equal(e.next_slot,next);assert.equal(e.already_star,already);
 assert.equal(e.after.remaining,6);assert.equal(p.is_star_point[next],true);assert.equal(p.qi-qi,Number(already));
 scenarios++;
}
{
 const {g,x}=fresh(),p=g.players[0];for(let i=0;i<9;i++)g.play_card(p.cards[0],0);
 assert.equal(x.metadata().events.length,7);assert.equal(x.metadata().remaining[0].charges,0);
 assert.equal(p.qi,6);g.do_plant_start_permanent_buffs();assert.equal(x.metadata().remaining[0].charges,0);scenarios++;
}
{
 const {g,x}=fresh(),p=g.players[0];p.cards[0]='601011';g.play_card(p.cards[0],0);
 assert.equal(x.metadata().remaining[0].charges,7);assert.equal(x.metadata().events.length,0);scenarios++;
}
{
 const {g,x}=fresh(),p=g.players[0];p.strike_twice_stacks=1;g.play_card(p.cards[0],0);
 assert.equal(x.metadata().events.length,2);assert.equal(x.metadata().remaining[0].charges,5);
 assert.equal(p.qi,1);assert.deepEqual(x.metadata().events.map(e=>e.already_star),[false,true]);scenarios++;
}
{
 const {g,x}=fresh(),p=g.players[0];p.is_star_point[1]=true;p.hp=50;p.stillness_citta_dharma_stacks=3;
 g.play_card(p.cards[0],0);assert.equal(p.qi,1);assert.equal(p.hp,53);assert.equal(x.metadata().events[0].after.hp,53);scenarios++;
}
for(const order of [[0,1],[1,0]]) {
 const {g,x}=fresh(3,[true,true],order);g.play_card(g.players[0].cards[0],0);g.swap_players();g.play_card(g.players[0].cards[1],1);
 assert.deepEqual(x.metadata().events.map(e=>e.player_index),order);
 assert.deepEqual(x.metadata().remaining.map(e=>e.charges),[6,6]);scenarios++;
}
{
 const {g,x}=fresh(3,[false,true]);g.play_card(g.players[0].cards[0],0);assert.equal(x.metadata().events.length,0);
 g.swap_players();g.play_card(g.players[0].cards[0],0);assert.equal(x.metadata().events[0].player_index,1);scenarios++;
}
{
 const {g}=fresh();g.players[0].trigger_depth=1;g.players[0].currently_playing_card_idx=0;
 assert.throws(()=>g.trigger_card('121031',0),/temporary_or_unknown_card_identity/);scenarios++;
}
{
 const {g}=fresh();assert.throws(()=>g.do_cloud_sword_softheart_and_friends('unknown'),/unknown_card_classification/);scenarios++;
}
{
 const {g}=fresh();g.players[0].card_play_direction=0;assert.throws(()=>g.play_card('121031',0),/grid_or_direction_changed/);scenarios++;
}
for(const input of [null,{}, {players:[]},{players:[{},null]},
 {players:[{strategy_id:7056,unlocked_slots:0},null]},{players:[entry(1),null]},{players:[entry(2),null]},{players:[{strategy_id:7056,unlocked_slots:3,charges:99},null]}]) {
 const g=new GameState();assert.throws(()=>installSevenStars(root,g,input),/explicit_ownership/);scenarios++;
}
{
 const {g}=fresh();assert.throws(()=>installSevenStars(root,g,{players:[entry(3),null]}),/already_installed/);scenarios++;
}
{
 const g=new GameState();g.players[0].cards=['601011'];
 assert.throws(()=>installSevenStars(root,g,{players:[entry(3),null]}),/unlocked_grid_deck_mismatch/);scenarios++;
}
{
 const {g,x}=fresh(),p=g.players[0],body=g.just_do_the_card_and_nothing_else.bind(g);let observed=false;
 g.just_do_the_card_and_nothing_else=function(card){assert.equal(p.is_star_point[1],true);assert.equal(x.metadata().remaining[0].charges,6);observed=true;return body(card);};
 assert.equal(p.is_star_point[1],false);g.play_card(p.cards[0],0);assert.equal(observed,true);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios}));
