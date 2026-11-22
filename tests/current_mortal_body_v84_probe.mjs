// Source-derived conversion boundaries; these are software scenarios.
import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installCurrentFanQi} from '../tools/current_fan_qi_v79r2.mjs';
import {createOpeningQi} from '../tools/current_opening_qi_v79r2.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
let scenarios=0;
function fresh(opening=false){
 const g=new GameState(undefined,undefined,'mortal-body-software');
 for(const p of g.players)Object.assign(p,{character:'dx5',hp:40,max_hp:50,physique:10,max_physique:10,qi:3,mortal_body_stacks:1});
 installCurrentFanQi(root,g);
 if(opening)createOpeningQi(root,g,{players:[[7059],[]]});
 return g;
}
for(const opening of [false,true])for(const idx of [0,1])for(const cap of [10,11,20]){
 const g=fresh(opening),p=g.players[idx];p.max_physique=cap;
 p.spiritstat_tune_stacks=4;p.stillness_citta_dharma_stacks=5;
 g.increase_idx_qi(idx,2);
 assert.equal(p.physique,12);assert.equal(p.max_hp,52);
 assert.equal(p.hp,40+Math.max(0,12-cap));assert.equal(p.qi,3);
 assert.equal(p.total_qi_gained,0);assert.equal(p.def,0);
 g.reduce_idx_qi(idx,2);assert.equal(p.qi,1);assert.equal(p.physique,12);
 scenarios++;
}
for(const opening of [false,true]){
 const g=fresh(opening),p=g.players[0];g.increase_idx_qi(0,0);
 assert.equal(p.physique,10);assert.equal(p.qi,3);assert.equal(p.hp,40);
 p.colorful_spirit_crane_stacks=1;g.increase_idx_qi(0,2);
 assert.equal(p.physique,14);assert.equal(p.qi,3);
 p.mortal_body_stacks=0;g.increase_idx_qi(0,2);
 assert.equal(p.qi,7);assert.equal(p.physique,14);assert.equal(p.total_qi_gained,4);
 scenarios++;
}
process.stdout.write(JSON.stringify({passed:true,scenarios,scope:'software conversion boundaries, not independent replay evidence'}));
