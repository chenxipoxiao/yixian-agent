import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const source=JSON.parse(fs.readFileSync(path.join(root,'runs/stages/20261117T203800Z-s2-third-training-cohort/diagnostic/compiled.json'),'utf8'))[264].battle;
const {execute}=await import('../tools/full_battle_bridge_web_v177.mjs');
const checks=[];
execute(source,({game,swogi,order})=>{
 const p=game.players[0];
 for(const [id,divisor] of [['744011',24],['744012',18],['744013',14]]){
  assert.equal(swogi[id].hp_cost,2);
  for(const [total,expected] of [[0,2],[divisor-1,2],[divisor,3],[2*divisor-1,3],[2*divisor,4],[4*divisor,6]]){
   p.currently_triggering_card_id=id;p.hp_gained=total;const hits=[];
   game.atk=n=>{hits.push(n);p.hp_gained+=divisor;};
   swogi[id].card_actions(game);
   assert.deepEqual(hits,Array(expected).fill(6));
   checks.push({card:id,total,expected,hit_healing_does_not_recompute_count:true});
  }
 }
 p.currently_triggering_card_id='744011';game.atk=()=>assert.fail('invalid counter must fail before attacking');
 for(const value of [undefined,null,NaN,-1,0.5,2147483648]){
  p.hp_gained=value;assert.throws(()=>swogi['744011'].card_actions(game),/healing_counter_unknown_or_invalid/);
 }
 p.hp_gained=0;p.currently_triggering_card_id='744012';
 assert.throws(()=>swogi['744011'].card_actions(game),/actual_card_identity_required/);
});
const healing=execute(source,({game})=>{
 const p=game.players[0];p.hp=p.max_hp-3;const before=p.hp_gained;
 game.increase_idx_hp(0,40);
 assert.equal(p.hp,p.max_hp);assert.equal(p.hp_gained-before,40);
 p.prevent_gain_hp_stacks=1;game.increase_idx_hp(0,10);assert.equal(p.hp_gained-before,40);
 return {requested:40,actual_hp_increase:3,counter_increment:40,blocked_healing_increment:0};
});
// The observer follows player objects when the engine swaps acting seats.
execute(source,({game,swogi})=>{
 game.players.reverse();const p=game.players[0];p.currently_triggering_card_id='744013';p.hp_gained=42;
 let hits=0;game.atk=n=>{assert.equal(n,6);hits++;};swogi['744013'].card_actions(game);assert.equal(hits,5);
});
process.stdout.write(JSON.stringify({status:'passed',card_threshold_checks:checks,healing,
 invalid_counter_cases:6,identity_guard:true,swapped_actor:true,
 warning:'Software checks are not replay calibration or independent acceptance.'}));
