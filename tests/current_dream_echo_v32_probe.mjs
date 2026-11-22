import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerDreamEcho,installDreamEcho} from '../tools/current_dream_echo_v32.mjs';
import {registerCurrentAnimalCards,installCurrentAnimalLedger} from '../tools/current_animal_cards_v14.mjs';
import {registerSpiritOutburst,installSpiritOutburst} from '../tools/current_spirit_outburst_v30.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerCurrentAnimalCards(root,swogi);registerSpiritOutburst(root,swogi);registerDreamEcho(root,swogi);
let scenarios=0;
function fresh(grade=5,hands=[[10434],null],order=[0,1],install=true) {
 const g=new GameState(undefined,undefined,'dream-echo-boundaries'),id='D2502'+grade;
 for(const p of g.players){p.hp=50;p.max_hp=100;p.max_physique=100;p.cards=['132053',id,'601011'];p.post_deck_setup();}
 g.players[1].cards=['601011','601011','601011'];g.players[1].post_deck_setup();
 const ledger=installCurrentAnimalLedger(g),spirit=installSpiritOutburst(root,g,order);
 const echo=install?installDreamEcho(root,g,swogi,{hands},order):null;
 return {g,p:g.players[0],e:g.players[1],id,echo,ledger,spirit};
}
for(const grade of [4,5]) {
 const amount=grade===4?4:10;
 {
  const {g,p,id,echo,ledger}=fresh(grade);g.play_card(id,1);
  assert.equal(p.hp,62+amount);assert.equal(p.max_hp,100+amount);assert.equal(p.can_play[1],true);
  assert.equal(echo.metadata().events[0].selected_raw,10434);assert.equal(ledger.forPlayer(p).length,1);scenarios++;
 }
 {
  const {g,p,id,echo}=fresh(grade,[[7020023],null]);g.play_card(id,1);
  assert.equal(p.hp,50+amount);assert.equal(p.def,8);assert.equal(p.earth_spirit_formation_stacks,4);
  assert.equal(p.can_play[1],true);assert.equal(echo.metadata().events[0].selected_raw,7020023);scenarios++;
 }
 {
  const {g,p,id,echo}=fresh(grade,[[],null]);g.play_card(id,1);
  assert.equal(p.hp,50+amount);assert.equal(p.max_hp,100+amount);assert.equal(p.earth_spirit_formation_stacks,0);
  assert.equal(echo.metadata().events[0].selected_raw,null);scenarios++;
 }
 {
  const {g,p,id,echo}=fresh(grade,[[10434,10434,4000044],null]);g.play_card(id,1);g.play_card(id,1);
  assert.equal(echo.metadata().events.length,2);assert.equal(p.max_hp,100+2*amount);
  assert.equal(p.can_play[1],true);scenarios++;
 }
 {
  const {g,p,id,ledger}=fresh(grade);p.prevent_gain_hp_stacks=1;g.play_card(id,1);
  assert.equal(p.hp,50);assert.equal(p.max_hp,100+amount);assert.equal(ledger.forPlayer(p).length,1);scenarios++;
 }
 {
  const {g,p,id,echo}=fresh(grade);p.strike_twice_stacks=1;g.play_card(id,1);
  assert.equal(p.hp,50+2*(amount+12));assert.equal(p.max_hp,100+2*amount);assert.equal(echo.metadata().events.length,2);scenarios++;
 }
 {
  const {g,p,e,id,spirit}=fresh(grade,[[],null]);p.hp=100;g.current_spirit_outburst_gain(5,4020106);g.play_card(id,1);
  assert.equal(p.hp,100+amount);assert.equal(e.hp,50);assert.equal(spirit.metadata().events.filter(e=>e.kind==='overflow_damage').length,0);scenarios++;
 }
}
{
 const hands=[null,[10434]],before=structuredClone(hands),{g,id,echo}=fresh(5,hands,[1,0]);
 g.play_card(id,1);assert.equal(echo.metadata().events[0].player_index,1);assert.deepEqual(hands,before);scenarios++;
}
{
 const {g,p}=fresh(5,undefined,undefined,false);const before={hp:p.hp,max_hp:p.max_hp};
 for(const hands of [[[10434,7020023],null],[[9999999],null],[null,null],[[433],null]])
  assert.throws(()=>installDreamEcho(root,g,swogi,{hands}),/dream_echo_unresolved:/);
 assert.deepEqual({hp:p.hp,max_hp:p.max_hp},before);scenarios++;
}
{
 const {g}=fresh();assert.throws(()=>installDreamEcho(root,g,swogi,{hands:[[10434],null]}),/already_installed/);scenarios++;
}
{
 const {g,p}=fresh();const before={hp:p.hp,max_hp:p.max_hp};
 for(const pair of [[349,10],[10349,4],[999,4]])assert.throws(()=>g.current_dream_echo(...pair),/invalid_grade/);
 assert.deepEqual({hp:p.hp,max_hp:p.max_hp},before);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios}));
