import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerCloudDefense,installCloudDefense} from '../tools/current_cloud_defense_v71.mjs';
import {installCurrentDelayedEffects} from '../tools/current_delayed_effects_v70.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));registerCloudDefense(root,swogi);
let scenarios=0;
function fresh(id){
 const g=new GameState(undefined,undefined,'cloud-defense-boundaries');
 for(const p of g.players){p.character='sw3';p.hp=900;p.max_hp=1000;p.cards=['601011','601011','601011'];}
 g.players[0].cards[0]=id;installCurrentDelayedEffects(root,g,swogi);
 const ext=installCloudDefense(root,g,swogi,[0,1]);g.start_of_game_setup();return {g,p:g.players[0],q:g.players[1],ext};
}
function body(g,slot=0){const p=g.players[0];p.currently_playing_card_idx=slot;p.currently_triggering_card_idx=slot;p.currently_triggering_card_id=p.cards[slot];p.trigger_depth=1;swogi[p.cards[slot]].card_actions(g);}
// Softheart creates a future heal, not an immediate heal or a max-HP refill.
for(let grade=1;grade<=3;grade++){
 const {g,p}=fresh('78000'+grade);g.play_card(p.cards[0],0);
 assert.equal(p.hp,900);assert.equal(p.max_hp,1010+10*grade);assert.equal(p.cloud_sword_softheart_stacks,grade);
 assert.equal(p.can_play[0],false);assert.equal(p.has_played_continuous_card,true);assert.equal(p.this_card_chases,1);
 p.cards[1]='780011';g.play_card(p.cards[1],1);assert.equal(p.hp,900+grade);scenarios++;
}
// The second softheart uses the first one's stacks before adding its own.
{const {g,p}=fresh('780001');p.cards[1]='780003';g.play_card(p.cards[0],0);g.play_card(p.cards[1],1);assert.equal(p.hp,901);assert.equal(p.cloud_sword_softheart_stacks,4);scenarios++;}
// Earth distinguishes304 chain from720 total; the current card is not counted early.
for(let grade=1;grade<=5;grade++)for(const chain of [0,3]){
 const {g,p,ext}=fresh('78001'+grade);p.cloud_sword_chain_count=chain;p.cloud_sword_used_count=7;
 body(g);const mult=[1,1,2,3,3][grade-1],base=[6,9,9,9,12][grade-1];
 assert.equal(p.def,base+mult*(grade===5?7:chain));assert.equal(p.cloud_sword_chain_count,chain);assert.equal(p.cloud_sword_used_count,7);
 assert.equal(p.cloud_sea,[1,1,2,3,3][grade-1]);assert.equal(p.moon_water_sword_formation_stacks,[0,0,0,1,3][grade-1]);
 assert.equal(ext.metadata().events[0].count_source,grade===5?'720_cumulative':'304_chain');scenarios++;
}
{const {g,p}=fresh('780015');p.cloud_sword_chain_count=1;p.cloud_sword_used_count=6;g.play_card(p.cards[0],0);
 assert.equal(p.def,30);assert.equal(p.cloud_sword_used_count,7);assert.equal(p.cloud_sword_chain_count,2);
 for(let i=0;i<3;i++){g.do_def_decay();assert.equal(p.def,30);}assert.equal(p.moon_water_sword_formation_stacks,0);g.do_def_decay();assert.equal(p.def,15);scenarios++;}
// High-tier opening and explicit re-triggers share the normal dispatcher.
for(let grade=1;grade<=5;grade++){
 const {g,p,ext}=fresh('78002'+grade);assert.equal(p.cloud_sea,grade>=4?2:0);
 g.do_opening(0);assert.equal(p.cloud_sea,grade>=4?4:0);
 assert.equal(ext.metadata()?.events.filter(e=>e.kind==='opening').length??0,grade>=4?2:0);scenarios++;
}
// Snapshot qi once, no spending; linkage does not use other if_cloud_hit exemptions.
for(let grade=1;grade<=5;grade++)for(const qi of [0,1,5,6])for(const linked of [false,true]){
 const {g,p,q,ext}=fresh('78002'+grade);p.qi=qi;p.cloud_sword_chain_count=linked?2:0;p.endurance_as_cloud_sea_stacks=1;
 body(g);const attack=[4,5,6,4,5][grade-1],extra=grade<=3?Number(qi>0):Math.floor(qi/(linked?2:3));
 assert.equal(q.hp,900-attack*(1+extra));assert.equal(p.qi,qi);assert.equal(ext.metadata().events.at(-1).repeats,1+extra);scenarios++;
}
{const {g,p,q,ext}=fresh('780024');p.qi=6;p.cloud_sword_chain_count=1;const atk=g.atk.bind(g);g.atk=function(n){const out=atk(n);this.increase_idx_qi(0,3);return out;};body(g);
 assert.equal(q.hp,884);assert.equal(p.qi,18);assert.equal(ext.metadata().events.at(-1).repeats,4);scenarios++;}
// Per-hit shield handling remains live; a single shield does not block all repeats.
{const {g,p,q}=fresh('780021');p.qi=1;q.guard_up=1;body(g);assert.equal(q.hp,896);assert.equal(q.guard_up,0);scenarios++;}
console.log(JSON.stringify({passed:true,scenarios}));
