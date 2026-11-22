import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerCurrentSeasonCards} from '../tools/current_season_cards_v16.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const original={...swogi};registerCurrentSeasonCards(root,swogi);
for(const id of Object.keys(original))assert.strictEqual(swogi[id],original[id]);
let checked=0;
function fresh(id,fields={},enemy={}) {
  const g=new GameState(undefined,undefined,'software-boundaries-only');
  Object.assign(g.players[0],{cards:[id,id,id],hp:100,max_hp:100,qi:0,def:0,
    currently_playing_card_idx:0,currently_triggering_card_idx:0,currently_triggering_card_id:id},fields);
  Object.assign(g.players[1],{cards:['601011'],hp:1000,max_hp:1000,qi:0,def:0},enemy);
  return g;
}
for(let grade=0;grade<3;grade++) {
  const snake=String(124941+grade);
  for(const oldSnake of [0,2])for(const protection of [0,2]) {
    const g=fresh(snake,{}, {snake_shadow:oldSnake,hexproof:protection});swogi[snake].card_actions(g);
    assert.equal(g.players[1].internal_injury,grade?Math.max(0,grade+oldSnake-protection):0);
    assert.equal(g.players[1].snake_shadow,oldSnake+1);assert.equal(g.players[0].this_card_chases,1);checked++;
  }
  const tip=String(125941+grade);
  for(const slot of [0,1,2])for(const stars of [0,1,4]) {
    const g=fresh(tip,{currently_triggering_card_idx:slot,star_power:stars});
    // Direct body probe keeps star-point bonus disabled to isolate body ordering.
    const starsAtAttack=[],atk=g.atk.bind(g);g.atk=n=>{starsAtAttack.push(g.players[0].star_power);return atk(n);};
    swogi[tip].card_actions(g);
    assert.deepEqual(starsAtAttack,Array(2+grade).fill(stars));
    assert.equal(g.players[0].star_power,slot%2===0?stars+3:Math.max(0,stars-2));
    assert.equal(g.players[0].guard_up,slot%2===0?0:Math.min(stars,2));checked++;
  }
  const soul=String(125951+grade);
  for(const slot of [0,1])for(const injury of [0,1]) {
    const g=fresh(soul,{currently_triggering_card_idx:slot},{internal_injury:injury});swogi[soul].card_actions(g);
    assert.equal(g.players[0].hexagram,2+grade+(injury?2:0));
    assert.equal(g.players[1].internal_injury,injury+(slot===0?grade+1:0));
    assert.equal(g.players[1].wound,slot===1?(grade===2?2:1):0);checked++;
  }
  const twin=String(133941+grade);
  for(const direction of [1,-1]) {
    const g=fresh(twin,{cards:direction===1?[twin,'131071','131091']:['131091','131071',twin],
      currently_triggering_card_idx:direction===1?0:2,card_play_direction:direction});
    swogi[twin].card_actions(g);
    assert.equal(g.players[0].activate_metal_spirit_stacks,1);assert.equal(g.players[0].activate_water_spirit_stacks,1);
    assert.equal(g.players[0].def,3+grade*3);assert.equal(g.players[1].hp,1000-(4+grade)*2);checked++;
  }
  for(const generation of [0,1]) {
    const g=fresh(twin,{cards:[twin,'131031','131011'],fire_spirit_generation_stacks:generation});swogi[twin].card_actions(g);
    assert.equal(g.players[0].def,generation?3+grade*3:0);checked++;
  }
  const fire=String(135941+grade);
  for(let mask=0;mask<8;mask++) {
    const g=fresh(fire,{increase_atk:2,def:8,penetrate:5,activate_fire_spirit_stacks:mask&1,
      activate_earth_spirit_stacks:mask&2,activate_metal_spirit_stacks:mask&4},{def:900});
    swogi[fire].card_actions(g);
    const loss=9+3*grade+((mask&1)?2*(2+grade):0)+((mask&2)?2:0)+((mask&4)?2:0);
    assert.equal(g.players[1].hp,1000-loss);assert.equal(g.players[1].max_hp,1000-loss);
    assert.equal(g.players[1].def,900);assert.equal(g.players[0].penetrate,5);checked++;
  }
  const rain=String(135951+grade);
  for(let mask=0;mask<4;mask++) {
    const g=fresh(rain,{force_of_water:2,qi:4,activate_water_spirit_stacks:mask&1,activate_wood_spirit_stacks:mask&2});
    const hits=[],atk=g.atk.bind(g);g.atk=n=>{hits.push(n);return atk(n);};swogi[rain].card_actions(g);
    assert.equal(g.players[0].hp,110+3*grade);assert.equal(g.players[0].max_hp,110+3*grade);
    assert.deepEqual(hits,[...(mask&1?[4+grade]:[]),...(mask&2?[5]:[])]);checked++;
  }
  const sand=String(135961+grade);
  for(let mask=0;mask<4;mask++) {
    const g=fresh(sand,{activate_metal_spirit_stacks:mask&1,activate_water_spirit_stacks:mask&2});swogi[sand].card_actions(g);
    assert.equal(g.players[0].qi,1+grade);assert.equal(g.players[0].penetrate,2+2*grade);
    assert.equal(g.players[0].this_card_chases,mask?1:0);checked++;
  }
  const extreme=String(135971+grade);
  for(const active of [0,1]) {
    const g=fresh(extreme,{increase_atk:3,activate_fire_spirit_stacks:active});swogi[extreme].card_actions(g);
    assert.equal(g.players[0].qi,2);assert.equal(g.players[0].increase_atk,4+grade);
    assert.equal(g.players[1].hp,1000-(active?8+grade:0));checked++;
  }
}
assert.throws(()=>registerCurrentSeasonCards(root,swogi),/alias collision/);
console.log(JSON.stringify({passed:true,checked,old_entries_unchanged:Object.keys(original).length}));
