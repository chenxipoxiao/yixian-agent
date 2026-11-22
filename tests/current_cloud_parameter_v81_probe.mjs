import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installCloudParameter} from '../tools/current_cloud_parameter_v81.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const battle=JSON.parse(fs.readFileSync(0,'utf8'));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const facts=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-cloud-parameter-v81.json')));
let scenarios=0;
function setup(){
 const g=new GameState(undefined,undefined,'software-cloud-boundary');
 for(let i=0;i<2;i++){Object.assign(g.players[i],{hp:100,max_hp:100,cards:[...battle.players[i].cards]});}
 Object.assign(g.players[0],{currently_triggering_card_idx:3,currently_triggering_card_id:'216011'});
 const m=installCloudParameter(root,swogi,g,battle.cloud_sword_parameters,[0,1],battle);
 return {g,m};
}
{
 const {g,m}=setup(), attacks=[];g.atk=n=>attacks.push([n,m.metadata().consumed]);
 g.just_do_the_card_and_nothing_else(swogi['216011']);m.verifyTerminal();
 assert.deepEqual(attacks,[[64,1]]);assert.equal(g.players[0].cloud_sword_hand_count,null);
 assert.equal(m.metadata().hand_count_default_used,false);assert.equal(m.metadata().training_label_allowed,false);
 assert.equal(m.metadata().events[0].value,56);scenarios++;
 assert.throws(()=>g.just_do_the_card_and_nothing_else(swogi['216011']),/parameter_underflow/);scenarios++;
}
for(const kind of ['slot','player','grade','card','unused','already_random','again']){
 const {g,m}=setup();
 if(kind==='slot')g.players[0].currently_triggering_card_idx=2;
 if(kind==='player')g.players.reverse();
 if(kind==='grade')g.players[0].currently_triggering_card_id='216012';
 if(kind==='card')g.players[0].currently_triggering_card_id='601011';
 if(kind==='already_random')g.used_randomness=true;
 assert.throws(()=>{
  if(kind==='unused')m.verifyTerminal();
  else if(kind==='again')installCloudParameter(root,swogi,g,battle.cloud_sword_parameters,[0,1],battle);
  else g.remnant_cloud_sky_sealing_sword_extra_atk(9999);
 },/cloud_parameter_unresolved:/);scenarios++;
}
for(const method of [...facts.blocked_random_entrypoints,'rng']){
 const {g}=setup();assert.throws(()=>g[method](1,2,3),/cloud_parameter_unresolved:/);scenarios++;
}
for(const kind of ['stream','consumer','binding']){
 const {g}=setup(),v=structuredClone(battle.cloud_sword_parameters);
 if(kind==='stream')v.stream=[55];
 if(kind==='consumer')v.consumers[0].slot=2;
 if(kind==='binding')v.record_binding.scope='counterfactual';
 const fresh=new GameState(undefined,undefined,'software-cloud-tamper');
 assert.throws(()=>installCloudParameter(root,swogi,fresh,v,[0,1],battle),/cloud_parameter_unresolved:/);scenarios++;
}
console.log(JSON.stringify({software_boundary_scenarios:scenarios,real_replay_battles:0}));
