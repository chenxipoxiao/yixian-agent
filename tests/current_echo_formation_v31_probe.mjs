import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installCurrentEcho} from '../tools/current_echo_formation_v31.mjs';
import {registerCurrentStillness} from '../tools/current_stillness_v29.mjs';
import {registerSpiritOutburst,installSpiritOutburst} from '../tools/current_spirit_outburst_v30.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerCurrentStillness(root,swogi);registerSpiritOutburst(root,swogi);
let scenarios=0;
function fresh(grade=1,first='601011') {
  const g=new GameState(undefined,undefined,'echo-prefix-boundaries');
  const id='35502'+grade;
  for(const p of g.players){p.hp=50;p.max_hp=100;p.max_physique=100;p.cards=[first,id,'601011'];p.post_deck_setup();}
  g.players[1].hp=200;g.players[1].max_hp=200;
  const spirit=installSpiritOutburst(root,g),echo=installCurrentEcho(root,g);
  return {g,p:g.players[0],e:g.players[1],id,spirit,echo};
}
for(let grade=1;grade<=3;grade++) {
  const amount=[2,5,8][grade-1];
  {
    const {g,p,id,echo}=fresh(grade);g.play_card(id,1);
    assert.equal(p.hp,50+amount);assert.equal(p.max_hp,100+amount);
    assert.equal(p.can_play[1],true);assert.equal(p.this_card_chases,0);
    assert.deepEqual(echo.metadata().events[0].before_repeat,{hp:50+amount,max_hp:100+amount});scenarios++;
  }
  {
    const {g,p,id,echo}=fresh(grade,'125961');g.play_card(id,1);
    assert.equal(p.hp,50+amount);assert.equal(p.max_hp,120+amount);
    assert.equal(p.stillness_citta_dharma_stacks,grade);assert.equal(p.can_play[1],true);
    assert.deepEqual(echo.metadata().events[0].before_repeat,{hp:50+amount,max_hp:100+amount});scenarios++;
  }
  {
    const {g,p,id}=fresh(grade,'125963');g.play_card(id,1);
    assert.equal(p.stillness_citta_dharma_stacks,3);assert.equal(p.max_hp,120+amount);scenarios++;
  }
  {
    const {g,p,id}=fresh(grade,'125961');p.prevent_gain_hp_stacks=1;g.play_card(id,1);
    assert.equal(p.hp,50);assert.equal(p.max_hp,120+amount);assert.equal(p.stillness_citta_dharma_stacks,grade);scenarios++;
  }
  {
    const {g,p,id}=fresh(grade);p.appetite=4;p.indigestion=1;p.birdie_wind_stacks=1;g.play_card(id,1);
    assert.equal(p.hp,53+amount);assert.equal(p.max_hp,100+amount);assert.equal(p.def,1);scenarios++;
  }
  {
    const {g,p,id,echo}=fresh(grade);p.strike_twice_stacks=1;g.play_card(id,1);
    assert.equal(p.hp,50+2*amount);assert.equal(p.max_hp,100+2*amount);assert.equal(echo.metadata().events.length,2);scenarios++;
  }
  {
    const {g,p,id}=fresh(grade);p.indigestion=100;g.play_card(id,1);
    assert.equal(p.hp,51);assert.equal(p.max_hp,100+amount);scenarios++;
  }
  {
    const {g,p,e,id,spirit}=fresh(grade);p.hp=100;
    g.current_spirit_outburst_gain(5,4020106);g.play_card(id,1);
    assert.equal(p.hp,100+amount);assert.equal(p.max_hp,100+amount);assert.equal(e.hp,200);
    assert.equal(spirit.metadata().events.filter(e=>e.kind==='overflow_damage').length,0);
    p.appetite=3;g.play_card(id,1);
    assert.equal(p.hp,100+2*amount);assert.equal(e.hp,197);scenarios++;
  }
}
{
  const {g,p,id}=fresh(3);p.hp=100;p.p2_rejuvenation_stacks=1;g.play_card(id,1);
  assert.equal(p.max_hp,111);assert.equal(p.hp,108);scenarios++;
}
{
  const {g,echo}=fresh(2);g.players.reverse();g.play_card('355022',1);
  assert.equal(echo.metadata().events[0].player_index,1);scenarios++;
}
{
  const {g,p,echo}=fresh(1);const before={hp:p.hp,max_hp:p.max_hp};
  for(const v of [-1,3,1.5,NaN,'1'])assert.throws(()=>g.do_echo_formation_thing(v),/invalid_grade/);
  assert.deepEqual({hp:p.hp,max_hp:p.max_hp},before);assert.equal(echo.metadata(),null);scenarios++;
}
{
  const {g,p,id}=fresh(3);assert.throws(()=>installCurrentEcho(root,g),/already installed/);
  g.play_card(id,1);assert.equal(p.hp,58);assert.equal(p.max_hp,108);scenarios++;
}
console.log(JSON.stringify({passed:true,scenarios}));
