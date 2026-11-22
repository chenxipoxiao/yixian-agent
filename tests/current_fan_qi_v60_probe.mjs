import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installCurrentFanQi} from '../tools/current_fan_qi_v60.mjs';
import {createOpeningQi} from '../tools/current_opening_qi_v60.mjs';
import {installCurrentStartStates} from '../tools/current_start_states_v7.mjs';
import {installDragonQi} from '../tools/current_dragon_qi_v40.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const passed=[];const scenario=(name,fn)=>{fn();passed.push(name);};
function fresh(season=false,order=[0,1]){
 const g=new GameState(undefined,undefined,'fan-qi-software');
 g.players.forEach(p=>{p.hp=100;p.max_hp=100;p.cards=['925021','601011','601011'];p.post_deck_setup();});
 const fan=installCurrentFanQi(root,g,order);
 const opening=season?createOpeningQi(root,g,{players:[[7059,7109],[7059,7109]]},order):null;
 installCurrentStartStates(root,g);
 if(opening){for(const id of [7109,7059,7005])opening.installBoundary(id);g.do_plant_start_permanent_buffs();}
 return {g,fan,opening};
}
for(const season of [false,true]){
 for(const rank of [1,2,3])scenario(`rank-${rank}-season-${season}`,()=>{
  const {g,fan}=fresh(season);g.play_card('92502'+rank,0);
  assert.equal(g.players[0].star_moon_hexagram_fan_stacks,3);
  assert.equal(g.players[1].hp,100);g.increase_idx_qi(0,2);
  assert.equal(g.players[1].hp,94);assert.equal(fan.metadata().events.length,1);assert.equal(fan.metadata().events[0].damage,6);
 });
 scenario(`zero-and-spending-${season}`,()=>{
  const {g,fan}=fresh(season);g.play_card('925021',0);g.players[0].qi=6;g.increase_idx_qi(0,0);g.reduce_idx_qi(0,3);
  assert.equal(g.players[1].hp,100);assert.equal(fan.metadata(),null);
 });
 scenario(`adjusted-amount-and-stacking-${season}`,()=>{
  const {g,fan}=fresh(season);g.play_card('925021',0);g.play_card('925021',1);g.players[0].colorful_spirit_crane_stacks=1;
  g.increase_idx_qi(0,2);assert.equal(g.players[1].hp,76);assert.equal(fan.metadata().events[0].damage,24);
 });
 scenario(`halved-zero-and-conversion-${season}`,()=>{
  const {g,fan}=fresh(season);g.play_card('925021',0);const p=g.players[0];p.dream_nine_evil_ruptsprite_stacks=1;
  g.increase_idx_qi(0,1);assert.equal(fan.metadata(),null);p.dream_nine_evil_ruptsprite_stacks=0;p.mortal_body_stacks=1;
  g.increase_idx_qi(0,2);assert.equal(fan.metadata(),null);assert.equal(g.players[1].hp,100);
 });
 scenario(`nested-hexagram-before-qi-before-later-${season}`,()=>{
  const {g,fan}=fresh(season);g.play_card('925021',0);g.players[0].spiritual_divination_stacks=2;g.players[0].wild_crossing_seal_stacks=1;
  const calls=[],damage=g.deal_damage_inner.bind(g);g.deal_damage_inner=(n,...args)=>{calls.push(n);return damage(n,...args);};
  g.do_wild_crossing_seal_chase=()=>calls.push('later');g.increase_idx_qi(0,1);
  assert.deepEqual(calls,[6,3,'later']);assert.equal(g.players[1].hp,91);assert.equal(fan.metadata().events[0].before.hp,94);
 });
 scenario(`guard-single-packet-${season}`,()=>{
  const {g,fan}=fresh(season);g.play_card('925021',0);g.players[1].guard_up=1;g.increase_idx_qi(0,3);
  assert.equal(g.players[1].hp,100);assert.equal(g.players[1].guard_up,0);assert.equal(fan.metadata().events.length,1);
 });
 scenario(`defense-and-nonattack-${season}`,()=>{
  const {g}=fresh(season);g.play_card('925021',0);g.players[1].def=4;g.players[0].increase_atk=50;g.players[0].sword_intent=30;
  g.increase_idx_qi(0,2);assert.equal(g.players[1].def,0);assert.equal(g.players[1].hp,98);assert.equal(g.players[0].sword_intent,30);
 });
 scenario(`lethal-boundary-${season}`,()=>{
  const {g,fan}=fresh(season);g.play_card('925021',0);g.players[1].hp=5;g.increase_idx_qi(0,2);
  assert.equal(g.players[1].hp,-1);assert.equal(fan.metadata().events[0].after.hp,-1);
 });
}
scenario('unowned-keeps-native-gain-and-no-metadata',()=>{
 const {g,fan}=fresh();g.increase_idx_qi(0,3);assert.equal(g.players[0].qi,3);assert.equal(g.players[1].hp,100);assert.equal(fan.metadata(),null);
});
scenario('both-targets-and-seat-reversal',()=>{
 const {g,fan}=fresh(false,[1,0]);g.players.forEach(p=>p.star_moon_hexagram_fan_stacks=3);
 g.increase_idx_qi(0,1);g.increase_idx_qi(1,2);g.players.reverse();g.increase_idx_qi(0,1);
 assert.deepEqual(fan.metadata().events.map(e=>[e.player_index,e.target_index,e.damage]),[[1,0,3],[0,1,6],[0,1,3]]);
});
scenario('existing-hexagram-and-star-damage-retained',()=>{
 const {g,fan}=fresh();g.play_card('925021',0);g.increase_idx_hexagram(0,2);g.increase_idx_star_power(0,2);
 assert.equal(g.players[1].hp,88);assert.equal(fan.metadata(),null);
});
scenario('live-stacks-after-nested-callback',()=>{
 const {g,fan}=fresh();g.play_card('925021',0);g.players[0].spiritual_divination_stacks=1;
 const hex=g.increase_idx_hexagram.bind(g);g.increase_idx_hexagram=(i,n)=>{hex(i,n);g.players[i].star_moon_hexagram_fan_stacks=6;};
 g.increase_idx_qi(0,1);assert.equal(g.players[1].hp,91);assert.equal(fan.metadata().events[0].stacks,6);
});
scenario('echo-copy-and-rank-transform-use-live-fan',()=>{
 const {g,fan}=fresh();g.do_echo_formation_thing(2);assert.equal(g.players[0].star_moon_hexagram_fan_stacks,3);
 g.increase_idx_qi(0,1);assert.equal(g.players[1].hp,97);assert.equal(fan.metadata().events.length,1);
});
scenario('dragon-bonus-consumed-before-fan-and-season-rewards',()=>{
 const {g,fan}=fresh(true);g.play_card('925021',0);
 installDragonQi(root,g,{players:[{strategy_id:3011},null]});g.do_plant_start_permanent_buffs();g.increase_idx_qi(0,1);
 assert.equal(fan.metadata().events.length,1);assert.equal(fan.metadata().events[0].qi_delta,3);assert.equal(g.players[1].hp,91);
 assert.equal(g.players[0].agility,5);assert.equal(g.players[0].max_hp,104);
});
scenario('invalid-installation-rejected',()=>{
 const {g}=fresh();assert.throws(()=>installCurrentFanQi(root,g),/already_installed/);
 assert.throws(()=>installCurrentFanQi(root,new GameState(),[0,0]),/invalid_order/);
});
console.log(JSON.stringify({passed:true,scenarios:passed.length,names:passed}));
