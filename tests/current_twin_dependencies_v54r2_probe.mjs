import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerTwinDependencies,installTwinDependencies} from '../tools/current_twin_dependencies_v54.mjs';
import {installCurrentNormalAttackV54} from '../tools/current_normal_attack_v54.mjs';
import {installCarefreeTwin} from '../tools/current_carefree_twin_v54.mjs';
import {createSoundControl} from '../tools/current_sound_control_v54.mjs';
import {installCurrentEngravings} from '../tools/current_engraving_effects_v54.mjs';
import {installCurrentQiPayment} from '../tools/current_qi_payment_v15.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerTwinDependencies(root,swogi);
const facts=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-twin-dependencies-v54.json')));
const rt=id=>facts.metadata[id].runtime_id,passed=[];
const scenario=(name,fn)=>{fn();passed.push(name);};
function fresh(raw=[[1000001,0,0],[0,0,0]]){
 const g=new GameState(undefined,undefined,'twin-dependencies-software');
 g.players.forEach((p,i)=>{p.hp=100;p.max_hp=100;p.cards=raw[i].map(rt);p.post_deck_setup();});return g;
}
function echo(g,raw,order=[0,1]){
 const result=installTwinDependencies(root,g,swogi,{players:[true,false],raw_boards:raw},order);
 g.do_plant_start_permanent_buffs();return result;
}
for(const source of [1000001,1010001,1020001,1020099,20019])scenario('copy-grade-'+source,()=>{
 const raw=[[source,0,0],[0,0,0]],g=fresh(raw),e=echo(g,raw);
 g.do_continuous_tune(1);assert.equal(g.players[0].cards[1],rt(facts.metadata[source].echo_copy_raw_id));
 assert.equal(e.metadata().remaining_echo[0].pending,0);
 g.do_plant_start_permanent_buffs();g.do_continuous_tune(2);
 assert.equal(g.players[0].cards[2],rt(0));assert.equal(e.metadata().events.length,1);
});
scenario('slot-zero-excluded-both-directions',()=>{
 for(const direction of [1,-1]){
  const raw=[[0,1000001,1000012],[0,0,0]],g=fresh(raw),e=echo(g,raw);g.players[0].card_play_direction=direction;
  g.do_continuous_tune(0);assert.equal(g.players[0].cards[0],rt(0));assert.equal(e.metadata().remaining_echo[0].pending,1);
 }
});
scenario('reverse-physical-neighbor-even-consumed',()=>{
 const raw=[[1000001,0,1020012],[0,0,0]],g=fresh(raw),e=echo(g,raw);
 g.players[0].card_play_direction=-1;g.players[0].can_play[2]=false;g.do_continuous_tune(1);
 assert.equal(g.players[0].cards[1],rt(1010012));assert.equal(e.metadata().events[0].source_slot,2);
});
scenario('raw19-consumes-without-copy-or-rearm',()=>{
 const raw=[[19,0,0],[0,0,0]],g=fresh(raw),e=echo(g,raw);
 g.do_continuous_tune(1);g.do_continuous_tune(2);
 assert.deepEqual(g.players[0].cards,raw[0].map(rt));assert.equal(e.metadata().events.length,1);
 assert.equal(e.metadata().events[0].skipped_raw19,true);assert.equal(e.metadata().remaining_echo[0].pending,0);
});
scenario('copy-normal-grade-still-triggers-shield',()=>{
 const raw=[[20000,0,0],[0,0,0]],g=fresh(raw);echo(g,raw);
 const s=installCurrentNormalAttackV54(root,g,{players:[[5007],[]]},[0,1]);g.do_plant_start_permanent_buffs();
 g.do_continuous_tune(1);g.play_card(g.players[0].cards[1],1);
 assert.equal(g.players[1].hp,94);assert.equal(g.players[0].guard_up,3);assert.equal(s.metadata().events.length,1);
});
scenario('copy-nonnormal-preserves-pending-shield',()=>{
 const raw=[[1000001,0,0],[0,0,0]],g=fresh(raw);echo(g,raw);
 const s=installCurrentNormalAttackV54(root,g,{players:[[5007],[]]},[0,1]);g.do_plant_start_permanent_buffs();
 g.do_continuous_tune(1);g.play_card(g.players[0].cards[1],1);
 assert.equal(g.players[0].guard_up,0);assert.equal(s.metadata().remaining[0].shield_pending,3);
});
for(const bad of ['unknown','ambiguous','temporary','legacy'])scenario('reject-'+bad,()=>{
 const raw=[[1000001,0,0],[0,0,0]],g=fresh(raw),e=echo(g,raw);
 if(bad==='unknown')g.players[0].cards[0]='unimplemented';
 if(bad==='ambiguous')g.players[0].cards[0]=rt(19);
 if(bad==='temporary')g.players[0].trigger_depth=1;
 if(bad==='legacy')g.players[0].continuous_tune_stacks=1;
 assert.throws(()=>g.do_continuous_tune(1),/twin_dependencies_unresolved/);
 assert.equal(g.players[0].cards[1],rt(0));assert.equal(e.metadata().remaining_echo[0].pending,1);
});
scenario('clone-cost-paid-on-later-use-only',()=>{
 const raw=[[1000029,0,0],[0,0,0]],g=fresh(raw);installCurrentQiPayment(g);echo(g,raw);
 // Giant Roc Spirit Sword costs2 Qi. Copy after paying the ordinary attack's0.
 assert.equal(swogi[rt(1000029)].qi_cost,2);
 const p=g.players[0];p.next_card_index=1;p.qi=0;g.sim_turn();
 assert.equal(p.cards[1],rt(1000029));assert.equal(p.qi,0);assert.ok(g.players[1].hp<100);
 p.next_card_index=1;const hp=g.players[1].hp;g.sim_turn();
 assert.equal(p.qi,1);assert.equal(g.players[1].hp,hp);
});
scenario('echo-before-upgrade-and-twin-no-repeat-payment',()=>{
 const raw=[[1020012,0,0],[0,0,0]],g=fresh(raw);
 const sound=createSoundControl(root,g,swogi,{players:[[{strategy_id:1007,enabled:true}],[]],raw_boards:raw},[0,1]);
 for(const id of [1007,1005,1003])sound.installBoundary(id);
 const e=echo(g,raw);const t=installCarefreeTwin(root,g,swogi,{players:[[{strategy_id:5009,slot:1}],[]],raw_boards:raw},[0,1]);
 g.do_continuous_tune(1);g.do_finishing_touch(1);g.play_card(g.players[0].cards[1],1);
 assert.equal(g.players[0].cards[1],rt(1020012));assert.equal(g.players[0].def,12);
 assert.equal(g.players[0].sword_intent,8);assert.equal(g.players[0].finishing_touch_stacks,0);
 assert.equal(e.metadata().events.length,1);assert.equal(t.metadata().events.filter(x=>x.strategy_id===5009).length,1);
 assert.equal(sound.metadata().events.filter(x=>x.phase==='before_card_body_281').length,1);
});
scenario('hidden-extreme-skips-engraving-but-upgrades-with281',()=>{
 const raw=[[1000099,0,0],[0,0,0]],g=fresh(raw);
 const sound=createSoundControl(root,g,swogi,{players:[[{strategy_id:1007,enabled:true}],[]],raw_boards:raw},[0,1]);
 for(const id of [1007,1005,1003])sound.installBoundary(id);
 installCurrentEngravings(root,g,{players:[[{strategy_id:13003,slot:0}],[]]},[0,1],{players:raw},swogi);
 g.do_plant_start_permanent_buffs();g.do_finishing_touch(0);
 assert.equal(g.players[0].cards[0],rt(1010099));assert.equal(g.players[0].finishing_touch_stacks,0);
});
for(const [rawId,multiplier] of [[1000099,1],[1010099,2],[1020099,3]])for(const count of [0,4])scenario('extreme-'+rawId+'-count-'+count,()=>{
 const raw=[[rawId,0,0],[0,0,0]],g=fresh(raw),e=installTwinDependencies(root,g,swogi,undefined,[0,1]);
 g.players[0].unrestrained_sword_count=count;g.play_card(rt(rawId),0);
 assert.equal(g.players[1].hp,100-1-count*multiplier);assert.equal(g.players[0].unrestrained_sword_count,count+1);
 assert.equal(g.players[0].this_card_chases,1);assert.equal(e.metadata().events[0].before.unrestrained_sword_count,count);
 assert.equal(e.metadata().events[0].after.unrestrained_sword_count,count);
});
scenario('extreme-actual-chase-and-limit',()=>{
 const raw=[[1010099,1000001,0],[0,0,0]],g=fresh(raw);installCurrentQiPayment(g);
 installTwinDependencies(root,g,swogi,undefined,[0,1]);g.sim_turn();
 assert.equal(g.players[0].chases,1);assert.equal(g.players[0].unrestrained_sword_count,1);assert.equal(g.players[1].hp,93);
});
scenario('unrelated-observer-output-absent',()=>{
 const g=fresh(),e=installTwinDependencies(root,g,swogi,undefined,[0,1]);g.play_card(rt(1000001),0);assert.equal(e.metadata(),null);
});
for(const id of [0,10000,20000])scenario('shield-grade-'+id,()=>{
 const raw=[[id,id,id],[0,0,0]],g=fresh(raw),s=installCurrentNormalAttackV54(root,g,{players:[[5007],[]]},[0,1]);
 g.do_plant_start_permanent_buffs();g.play_card(rt(id),0);assert.equal(g.players[0].guard_up,3);assert.deepEqual(g.players[0].can_play,[false,true,true]);
 g.players[0].guard_up=0;g.do_plant_start_permanent_buffs();g.play_card(rt(id),1);
 assert.equal(g.players[0].guard_up,0);assert.equal(s.metadata().events.length,1);
});
scenario('all-normal-hooks-client-order',()=>{
 const raw=[[0,0,0],[0,0,0]],g=fresh(raw),s=installCurrentNormalAttackV54(root,g,{players:[[5004,5007,5008,5011],[]]},[0,1]);
 g.do_plant_start_permanent_buffs();g.players[0].strike_twice_stacks=1;g.play_card(rt(0),0);
 assert.deepEqual(s.metadata().events.map(x=>x.effect_id),[5004,5007,5008,5011,5004]);
 assert.equal(g.players[0].guard_up,3);assert.equal(g.players[1].hp,88);assert.equal(g.players[0].agility,28);
});
scenario('shield-temporary-use-fails-before-any-hook',()=>{
 const raw=[[0,0,0],[0,0,0]],g=fresh(raw),s=installCurrentNormalAttackV54(root,g,{players:[[5004,5007,5008,5011],[]]},[0,1]);
 g.do_plant_start_permanent_buffs();g.players[0].trigger_depth=1;
 assert.throws(()=>g.trigger_card(rt(0),0),/normal_attack_actual_card_identity_required/);
 assert.equal(g.players[0].guard_up,0);assert.equal(g.players[0].agility,0);assert.equal(s.metadata().remaining[0].shield_pending,3);
});
scenario('initiative-swap-keeps-ownership',()=>{
 const raw=[[0,0,0],[1000001,0,0]],g=fresh(raw);
 const e=echo(g,[raw[1],raw[0]],[1,0]);g.do_continuous_tune(1);assert.equal(e.metadata().events.length,0);
 g.swap_players();g.do_plant_start_permanent_buffs();g.do_continuous_tune(1);
 assert.equal(e.metadata().events[0].player_index,0);assert.equal(g.players[0].cards[1],rt(1000001));
});
console.log(JSON.stringify({passed:true,scenarios:passed.length,names:passed}));
