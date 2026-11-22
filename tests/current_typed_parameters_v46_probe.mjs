import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installTypedParameters} from '../tools/current_typed_parameters_v46.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const canonical=v=>Array.isArray(v)?'['+v.map(canonical).join(',')+']':v!==null&&typeof v==='object'?'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}':JSON.stringify(v);
let scenarios=0;
function fresh(){const g=new GameState(undefined,undefined,'typed-software');for(const p of g.players){p.character='he1';p.hp=30;p.max_hp=100;p.cards=['601011','601011','601011'];}return g;}
function setup(g,stream,owners=[true,false],order=[0,1]) {
 const battle={first_player:order[0],players:g.players.map(p=>({hp:p.hp,max_hp:p.max_hp,cards:p.cards}))};
 const value={owners,stream,battle_sha256:crypto.createHash('sha256').update(canonical(battle)).digest('hex')};
 return {battle,value,m:installTypedParameters(root,swogi,g,value,order,battle)};
}
for(const order of [[0,1],[1,0]])for(const [id,lo,hi] of [['123081',8,18],['123082',12,22],['123083',16,26]])for(const forced of [false,true]){
 const g=fresh();g.players[0].hexagram=forced?2:0;const heal=forced?hi:lo+1;
 const {m}=setup(g,[3,heal],[true,false],order);g.start_of_game_setup();
 g.just_do_the_card_and_nothing_else(swogi[id]);m.verifyTerminal();
 assert.equal(g.players[0].hp,30+heal);assert.equal(g.players[0].max_hp,100+lo);
 assert.equal(g.players[0].hexagram,forced?1:0);assert.equal(g.players[0].triggered_hexagram_count,forced?1:0);
 const events=m.metadata().events;assert.deepEqual(events.map(x=>x.kind),['falling_paper','qi_therapy']);
 assert.deepEqual(events.map(x=>x.player_index),[0,order[0]]);assert.deepEqual(events.map(x=>x.queue_index),[0,1]);
 assert.equal(events[1].forced_by_hexagram,forced);assert.equal(m.metadata().training_label_allowed,false);scenarios++;
}
// Sequential users share one FIFO even after the active player swaps.
for(const order of [[0,1],[1,0]]){
 const g=fresh(),{m}=setup(g,[1,2,9,25],[true,true],order);g.start_of_game_setup();
 g.just_do_the_card_and_nothing_else(swogi['123081']);g.players.reverse();g.just_do_the_card_and_nothing_else(swogi['123083']);m.verifyTerminal();
 assert.deepEqual(m.metadata().events.map(e=>e.player_index),[order[0],order[1],order[0],order[1]]);
 assert.equal(m.metadata().pending_match_rewards.length,1);scenarios++;
}
// Hexagram consumption and queue access precede both maxHP and HP callbacks.
{
 const g=fresh();g.players[0].hexagram=1;const {m}=setup(g,[2,18]);g.start_of_game_setup();
 const max=g.increase_idx_max_hp.bind(g),hp=g.increase_idx_hp.bind(g),calls=[];
 g.increase_idx_max_hp=(i,n)=>{calls.push(['max',n,g.players[i].hexagram,m.metadata().consumed]);max(i,n);g.players[i].hp+=2;};
 g.increase_idx_hp=(i,n)=>{calls.push(['hp',n,g.players[i].hexagram,m.metadata().consumed]);return hp(i,n);};
 g.just_do_the_card_and_nothing_else(swogi['123081']);m.verifyTerminal();assert.deepEqual(calls,[['max',8,0,2],['hp',18,0,2]]);assert.equal(g.players[0].hp,50);scenarios++;
}
for(const kind of ['missing_card_value','unused_value','invalid_branch','out_of_range','wrong_forced','before_start','different_initiative','changed_battle','repeated_install']){
 const g=fresh(),stream=kind==='invalid_branch'?[5,16]:kind==='out_of_range'?[3,7]:kind==='unused_value'?[3,16,16]:[3,16];
 if(kind==='wrong_forced')g.players[0].hexagram=1;
 const {m,battle,value}=setup(g,stream);
 if(kind==='before_start')assert.throws(()=>g.just_do_the_card_and_nothing_else(swogi['123081']),/card_before_openings/);
 else if(kind==='different_initiative')assert.throws(()=>installTypedParameters(root,swogi,fresh(),value,[1,0],battle),/exclusive_bound_initiative_required/);
 else if(kind==='changed_battle'){battle.players[0].hp++;assert.throws(()=>installTypedParameters(root,swogi,fresh(),value,[0,1],battle),/compiled_battle_binding_mismatch/);}
 else if(kind==='repeated_install')assert.throws(()=>installTypedParameters(root,swogi,g,value,[0,1],battle),/already_installed/);
 else if(kind==='invalid_branch')assert.throws(()=>g.start_of_game_setup(),/parameter_out_of_range:falling_paper/);
 else {
  g.start_of_game_setup();
  if(kind==='out_of_range')assert.throws(()=>g.just_do_the_card_and_nothing_else(swogi['123081']),/parameter_out_of_range:qi_therapy/);
  else if(kind==='wrong_forced')assert.throws(()=>g.just_do_the_card_and_nothing_else(swogi['123081']),/forced_hexagram_result_mismatch/);
  else {g.just_do_the_card_and_nothing_else(swogi['123081']);if(kind==='missing_card_value')assert.throws(()=>g.just_do_the_card_and_nothing_else(swogi['123081']),/parameter_underflow/);else assert.throws(()=>m.verifyTerminal(),/unused_parameters/);}
 }
 scenarios++;
}
// Unsupported random methods must reject even if a hexagram would avoid rng().
for(const method of ['rand_range','if_c_pct','random_int','trigger_hexagram','trigger_replay_card_from_next_random_outcome','reduce_idx_random_debuff_by_c_n_times','rng']){
 const g=fresh();g.players[0].hexagram=10;setup(g,[3,16]);g.start_of_game_setup();
 assert.throws(()=>g[method](0,1,1),/typed_parameters_unresolved/);scenarios++;
}
for(const when of ['before','after']){const g=fresh(),{m}=setup(g,[3,16]);if(when==='before'){g.used_randomness=true;assert.throws(()=>g.start_of_game_setup(),/other_random_consumer/);}else{g.start_of_game_setup();g.just_do_the_card_and_nothing_else(swogi['123081']);g.used_randomness=true;assert.throws(()=>m.verifyTerminal(),/other_random_consumer/);}scenarios++;}
console.log(JSON.stringify({passed:true,scenarios}));
