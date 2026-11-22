// Real reference trigger/scheduler paths; explicit software fixtures, not replay evidence.
import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerNativeCardValues,nativeCardValuesFacts} from '../tools/current_native_card_values_v85.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const facts=nativeCardValuesFacts(root),before=new Map(facts.cards.map(c=>[c.runtime_id,{...swogi[c.runtime_id]}]));
registerNativeCardValues(root,swogi);
for(const c of facts.cards){
 const {card_actions:a,...old}=before.get(c.runtime_id),{card_actions:b,...now}=swogi[c.runtime_id];
 assert.deepEqual(old,now);assert.notEqual(a,b);
}
assert.throws(()=>registerNativeCardValues(root,swogi),/already_registered/);
let scenarios=0;
function fresh(card){
 const g=new GameState(undefined,undefined,'current-card-values-software');
 for(const p of g.players)Object.assign(p,{character:'sw3',hp:1000,max_hp:1000,qi:20,cards:[card,'111011','601011']});
 g.start_of_game_setup();g.players[0].currently_playing_card_idx=0;return g;
}
for(const [def,guard,hpLoss,pangu] of [[0,0,40,20],[30,0,10,20],[40,0,0,0],[0,1,0,0]]){
 const g=fresh('946011'),p=g.players[1];Object.assign(p,{def,guard_up:guard});const hp=p.hp;
 g.trigger_card('946011',0);
 assert.equal(hp-p.hp,hpLoss);assert.equal(p.pangu_axe_stacks,pangu);
 assert.equal(p.metal_spirit_chokehold_stacks,1);scenarios++;
}
for(let grade=1;grade<=3;grade++){
 const id='32403'+grade,g=fresh(id),p=g.players[1];g.trigger_card(id,0);
 assert.equal(p.weaken,grade+2);assert.equal(g.players[0].can_play[0],false);
 g.swap_players();
 for(let n=grade+1;n>=0;n--){g.sim_turn();assert.equal(p.weaken,n);}
 scenarios++;
}
for(let grade=1;grade<=3;grade++){
 const id='71501'+grade,g=fresh(id),p=g.players[0],events=[];
 const inc=g.increase_idx_x_by_c.bind(g);
 g.increase_idx_x_by_c=function(idx,field,amount){
  if(['dragon_devours_clouds_stacks','unrestrained_sword_count'].includes(field))events.push([idx,field,amount]);
  return inc(idx,field,amount);
 };
 g.trigger_card(id,0);
 assert.equal(p.unrestrained_sword_count,grade);assert.equal(p.dragon_devours_clouds_stacks,1);
 assert.equal(p.can_play[0],false);assert.equal(p.cloud_sword_chain_count,0);
 assert.deepEqual(events.slice(0,2),[[0,'dragon_devours_clouds_stacks',1],[0,'unrestrained_sword_count',grade]]);
 g.trigger_card('111011',1);assert.equal(p.unrestrained_sword_count,grade+1);
 g.trigger_card('601011',2);assert.equal(p.unrestrained_sword_count,grade+1);scenarios++;
}
// A transform resolves the downgraded identity's body, independent of original metadata.
{
 const g=fresh('715012'),p=g.players[0];p.cards[0]='715011';g.trigger_card(p.cards[0],0);
 assert.equal(p.unrestrained_sword_count,1);assert.equal(p.can_play[0],false);scenarios++;
}
process.stdout.write(JSON.stringify({passed:true,scenarios,metadata_preserved:7,
 scope:'software card-body/order/consumption checks, not independent server calibration'}));
