import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerHexagramThunder} from '../tools/current_hexagram_thunder_v67.mjs';
import {installReplayParameters} from '../tools/current_season_random_inputs_v125r3.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const fixtures=JSON.parse(fs.readFileSync(path.join(root,'runs/stages/20261116T074100Z-s2-season-random-inputs/binding-fixtures-v125.json')));
const facts=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-season-random-inputs-v125r3.json')));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerHexagramThunder(root,swogi);
let scenarios=0;
for(const [rid,fixture] of Object.entries(fixtures)){
 const expected=facts.admitted_records[rid];
 function make(){
  const battle=structuredClone(fixture.compiled.battle);
  const value={battle_sha256:expected.compiled_battle_sha256,record_binding:structuredClone(expected.binding),stream:[...fixture.context.battle_params]};
  battle.replay_parameters=value;
  return {battle,value,order:[battle.first_player,1-battle.first_player],game:new GameState(undefined,undefined,'binding-software')};
 }
 {
  const {game,battle,value,order}=make();
  const q=installReplayParameters(root,swogi,game,value,order,battle);
  assert.equal(q.version,125);assert.equal(q.metadata().reader_mode,expected.mode);
  assert.equal(q.metadata().total_parameters,value.stream.length);
  assert.equal(q.metadata().counterfactual_reuse_allowed,false);
  assert.throws(()=>q.verifyTerminal(),/unused_parameters/);scenarios++;
  assert.throws(()=>installReplayParameters(root,swogi,game,value,order,battle),/already_installed/);scenarios++;
 }
 for(const mode of ['stream','identity','start','initiative','duplicate','extra']){
  const {game,battle,value,order}=make();let error;
  if(mode==='stream'){value.stream[0]++;error=/recorded_stream_mismatch/;}
  if(mode==='identity'){value.record_binding.game_id='different-game';error=/unaudited_record_binding/;}
  if(mode==='start'){battle.seed='counterfactual';error=/compiled_battle_binding_mismatch/;}
  if(mode==='initiative'){order.reverse();error=/exclusive_bound_initiative_required/;}
  if(mode==='duplicate'){battle.typed_parameters={};error=/exclusive_bound_initiative_required/;}
  if(mode==='extra'){value.synthetic_fallback=0;error=/explicit_bound_stream_required/;}
  assert.throws(()=>installReplayParameters(root,swogi,game,value,order,battle),error);scenarios++;
 }
}
console.log(JSON.stringify({scenarios,passed:true,real_replay_simulations:0}));
