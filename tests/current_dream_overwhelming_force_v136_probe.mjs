import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerDreamForce,installDreamForce} from '../tools/current_dream_overwhelming_force_v136.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerDreamForce(root,swogi);
const cases=[],scenario=(name,fn)=>{fn();cases.push(name);};
function fresh(realm,qi=0,force=0){
  const id='D1418'+realm,g=new GameState(undefined,undefined,'dream-force-software');
  for(const p of g.players)Object.assign(p,{character:'he1',hp:50,max_hp:100,max_physique:1000,qi:0,cards:[id,'111011','111011']});
  const obs=installDreamForce(root,g,swogi);g.start_of_game_setup();
  const p=g.players[0];Object.assign(p,{hp:50,max_hp:100,physique:0,qi,force});
  return {g,p,id,obs};
}
// Expectations are the fixed client table, with real game mutation/callback methods.
for(const [realm,body,hp] of [[1,2,6],[2,3,8],[3,4,10]]){
  scenario('realm'+realm+'-no-positive-resource',()=>{
    const {g,p,id,obs}=fresh(realm);g.play_card(id,0);
    assert.equal(p.physique,0);assert.equal(p.hp,50);assert.equal(obs.metadata().events[0].condition_met,false);
  });
  for(const [qi,force] of [[1,0],[0,3],[1,3]])scenario('realm'+realm+'-resource-'+qi+'-'+force,()=>{
    const {g,p,id}=fresh(realm,qi,force);g.play_card(id,0);
    assert.equal(p.physique,body);assert.equal(p.max_hp,100+body);assert.equal(p.hp,50+hp);
    assert.equal(p.qi,qi);assert.equal(p.force,force);
  });
}
for(const [realm,body] of [[4,3],[5,6]]){
  scenario('realm'+realm+'-no-force-still-agility',()=>{
    const {g,p,id}=fresh(realm,7,0);g.play_card(id,0);
    assert.equal(p.agility,5);assert.equal(p.physique,0);assert.equal(p.hp,50);assert.equal(p.qi,7);
  });
  scenario('realm'+realm+'-consume-three-force',()=>{
    const {g,p,id}=fresh(realm,0,3);g.play_card(id,0);
    assert.equal(p.agility,5);assert.equal(p.force,0);assert.equal(p.physique,body);assert.equal(p.hp,59);
  });
}
scenario('cached-force-survives-agility-and-consumption-callbacks',()=>{
  const {g,p,id,obs}=fresh(5,0,3);p.currently_triggering_card_id=id;
  const add=g.add_c_of_x.bind(g),reduce=g.reduce_c_of_x.bind(g),calls=[];
  g.add_c_of_x=(n,key)=>{calls.push(['add',key,n]);add(n,key);if(key==='agility')p.force+=2;};
  g.reduce_c_of_x=(n,key)=>{calls.push(['reduce',key,n]);reduce(n,key);if(key==='force')p.force+=1;};
  g.executeCurrentDreamForce(id);
  assert.deepEqual(calls,[['add','agility',5],['reduce','force',3]]);
  assert.equal(p.force,3);assert.equal(p.physique,6);assert.equal(p.hp,59);
  assert.equal(obs.metadata().events[0].captured_force,3);
});
scenario('physique-callback-healing-occurs-before-card-heal',()=>{
  const {g,p,id}=fresh(2,1,0);p.max_physique=0;p.hp=99;
  g.play_card(id,0);assert.equal(p.physique,3);assert.equal(p.max_hp,103);assert.equal(p.hp,103);
});
scenario('unknown-state-and-overflow-refused',()=>{
  const {g,p,id}=fresh(5,0,3);p.currently_triggering_card_id=id;p.force=undefined;
  assert.throws(()=>g.executeCurrentDreamForce(id),/unknown_force_or_qi/);
  p.force=2147483647;assert.throws(()=>g.executeCurrentDreamForce(id),/conversion_overflow/);
  assert.equal(p.agility,0);assert.equal(p.physique,0);
});
console.log(JSON.stringify({passed:cases.length,cases,scope:'software callback and five-realm body checks; not replay calibration'}));
