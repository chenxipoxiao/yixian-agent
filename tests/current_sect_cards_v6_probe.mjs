import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerCurrentSectCards} from '../tools/current_sect_cards_v6.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const originals={...swogi};registerCurrentSectCards(root,swogi);
for(const id of Object.keys(originals))assert.strictEqual(swogi[id],originals[id]);
let checked=0;
function fresh(id,fields={}) {
  const g=new GameState(undefined,undefined,'fixed-component-only');
  Object.assign(g.players[0],{cards:[id,id,id],hp:40,max_hp:40,qi:0,def:0,physique:0,max_physique:6,
    currently_playing_card_idx:0,currently_triggering_card_idx:0,currently_triggering_card_id:id},fields);
  Object.assign(g.players[1],{cards:['601011'],hp:10000,max_hp:10000});return g;
}
function bases(g) {
  const captured=[],orig=g.atk.bind(g);
  g.atk=n=>{captured.push(n);return orig(n);};return captured;
}
for(let grade=0;grade<3;grade++) {
  const red=String(113921+grade),ele=String(114921+grade),moon=String(115921+grade),flash=String(115931+grade);
  for(const prior of [0,1,12]) {
    const g=fresh(red,{unrestrained_sword_count:prior});swogi[red].card_actions(g);
    assert.equal(g.players[0].increase_atk,Math.min(prior,grade+1));
    assert.equal(g.players[1].hp,10000-6-Math.min(prior,grade+1));checked++;
  }
  const elephant=fresh(ele);swogi[ele].card_actions(elephant);
  assert.equal(elephant.players[1].hp,9991);assert.equal(elephant.players[0].increase_atk,2+grade);checked++;
  for(const chain of [0,1]) for(const bonus of [0,7,1000]) {
    const g=fresh(moon,{cloud_sword_chain_count:chain,increase_atk:bonus}),hits=bases(g);
    swogi[moon].card_actions(g);
    const heal=8+5*grade+Math.min(bonus*2,100*(grade+1));
    assert.equal(g.players[0].max_hp,40+heal);assert.equal(g.players[0].hp,40+heal);
    assert.equal(hits.length,chain?3+grade:0);checked++;
  }
  const f=fresh(flash,{qi:100});swogi[flash].card_actions(f);
  assert.equal(f.players[0].def,[8,16,18][grade]);assert.equal(f.players[0].this_card_chases,1);checked++;
  const high=String(143921+grade),h=fresh(high,{qi:2,force:6});const highHits=bases(h);
  swogi[high].card_actions(h);assert.equal(h.players[0].max_force,7);
  assert.equal(highHits[0],8+3*grade+Math.min(9,4+grade*2));assert.equal(h.players[0].force,6);checked++;
  for(const slot of [0,1]) {
    const id=String(144921+grade),g=fresh(id,{physique:8,currently_triggering_card_idx:slot}),hits=bases(g);
    swogi[id].card_actions(g);
    assert.equal(g.players[0].physique,slot===0?12:8);assert.equal(hits[0],6+5*grade+(slot===0?1:0));checked++;
  }
  for(const qi of [0,1,2,4]) {
    const id=String(144931+grade),g=fresh(id,{qi,force:2});swogi[id].card_actions(g);
    // First attack consumes 1 force before substitution, leaving only 1.
    assert.equal(g.players[0].qi,Math.max(0,qi-2));
    assert.equal(g.players[0].agility,5*Math.min(2,qi+1));checked++;
  }
  const healing=String(145921+grade),heal=fresh(healing,{hp:20,increase_atk:2,force:3,hp_gained:14}),hits=bases(heal);
  swogi[healing].card_actions(heal);
  const amount=Math.trunc((8+grade*2)*13/10);
  assert.equal(heal.players[0].hp,20+amount);assert.equal(hits[0],2+Math.trunc((14+amount)/15));checked++;
  const blood=String(145931+grade),b=fresh(blood,{hp:30,wound:2});swogi[blood].card_actions(b);
  assert.equal(b.players[0].hp,35);assert.equal(b.players[0].internal_injury,grade+1);
  assert.equal(b.players[0].agility,5+grade*2);checked++;
  const asura=String(145941+grade),a=fresh(asura,{hp:20,qi:3,wound:2}),aHits=bases(a);
  swogi[asura].card_actions(a);assert.deepEqual(aHits,[8+grade*3,7+grade*3]);
  assert.equal(a.players[0].hp,20+Math.trunc((15+grade*6)/3));checked++;
}
assert.throws(()=>registerCurrentSectCards(root,swogi),/alias collision/);
console.log(JSON.stringify({passed:true,checked,original_entries_unchanged:Object.keys(originals).length}));
