import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installScrollOpening,scrollOpeningFacts} from '../tools/current_scroll_opening_v82.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const facts=scrollOpeningFacts(root),names=[];
const scenario=(name,fn)=>{fn();names.push(name);};
function fresh(raw,order=[0,1],direction=1){
 const g=new GameState(undefined,undefined,'scroll-source-scenario');
 const entries=[{fate_ids:[198],starting_raw_cards:raw,unlocked_slots:raw.length},
  {fate_ids:[],starting_raw_cards:Array(raw.length).fill(0),unlocked_slots:raw.length}];
 g.players.forEach((p,i)=>{p.hp=p.max_hp=100;p.cards=entries[order[i]].starting_raw_cards.map(x=>facts.raw_to_runtime[x]);if(raw.length>1)p.post_deck_setup();});
 const e=installScrollOpening(root,g,swogi,{players:entries},order),owner=order.indexOf(0),p=g.players[owner];
 p.card_play_direction=direction;
 return {g,e,p,q:g.players[1-owner],owner};
}
const occupied=1000001;
scenario('both-occupied-upgrade-twice-and-cap',()=>{
 for(const raw of [215,10215,20215]){const {g,p,owner}=fresh([occupied,raw,occupied]);g.apply_p5_fates_setup(owner);assert.equal(p.cards[1],'625033');}
});
scenario('two-empty-place-both-without-upgrading',()=>{
 const {g,p,owner}=fresh([0,215,0]);g.apply_p5_fates_setup(owner);assert.deepEqual(p.cards,['625041','625031','625051']);
});
scenario('one-empty-place-then-upgrade-once',()=>{
 for(const raw of [[0,215,occupied],[occupied,215,0]]){const {g,p,owner}=fresh(raw);g.apply_p5_fates_setup(owner);assert.equal(p.cards[1],'625032');}
});
scenario('wrap-direction-and-seat-permutation',()=>{
 for(const order of [[0,1],[1,0]])for(const direction of [1,-1]){
  const {g,p,owner,e}=fresh([215,0,occupied,0],order,direction);g.apply_p5_fates_setup(owner);
  assert.equal(p.cards[direction===1?3:1],'625041');assert.equal(p.cards[direction===1?1:3],'625051');assert.equal(e.metadata().events[0].player_index,0);
 }
});
scenario('shared-empty-is-consumed-by-earlier-scroll',()=>{
 const {g,p,owner}=fresh([215,0,215,occupied]);g.apply_p5_fates_setup(owner);
 assert.deepEqual(p.cards,['625032','625051','625033',facts.raw_to_runtime[occupied]]);
});
scenario('two-grid-shared-neighbor-and-direct-one-grid-opening-only',()=>{
 let {g,p,owner}=fresh([215,0]);g.apply_p5_fates_setup(owner);assert.deepEqual(p.cards,['625032','625041']);
 ({g,p,owner}=fresh([215]));g.apply_p5_fates_setup(owner);assert.deepEqual(p.cards,['625033']);
});
scenario('reads-current-empty-after-earlier-opening',()=>{
 const {g,p,owner}=fresh([0,215,0]);p.cards[0]=facts.raw_to_runtime[occupied];g.apply_p5_fates_setup(owner);
 assert.equal(p.cards[0],facts.raw_to_runtime[occupied]);assert.equal(p.cards[1],'625032');assert.equal(p.cards[2],'625051');
});
scenario('no-scroll-no-acquisition-and-no-reentry',()=>{
 const {g,p,owner}=fresh([occupied,occupied,occupied]);const before=[...p.cards];g.apply_p5_fates_setup(owner);assert.deepEqual(p.cards,before);
 assert.throws(()=>g.apply_p5_fates_setup(owner),/opening_reentered/);
});
scenario('generated-cards-never-upgrade',()=>{
 const {g,p,owner}=fresh([0,215,0]);g.apply_p5_fates_setup(owner);
 for(const slot of [0,2]){const before=p.cards[slot];assert.equal(g.try_upgrade_card(owner,slot),false);assert.equal(p.cards[slot],before);}
});
scenario('face-isolation-waits-for-incoming-attack-and-chases',()=>{
 const {g,p,q}=fresh([0,215,0]);g.apply_p5_fates_setup(0);swogi['625041'].card_actions(g);
 assert.equal(p.this_card_chases,1);assert.equal(q.face_isolation_stacks,1);
 // Own attack must not spend the defense marker.
 g.atk(10);assert.equal(q.face_isolation_stacks,1);assert.equal(p.weaken,0);
 g.swap_players();g.atk(10);assert.equal(q.face_isolation_stacks,0);assert.equal(q.weaken,1);assert.equal(p.hp,94);
});
scenario('strike-vacuity-waits-for-own-attack-and-chases',()=>{
 const {g,p,q}=fresh([0,215,0]);g.apply_p5_fates_setup(0);swogi['625051'].card_actions(g);
 assert.equal(p.this_card_chases,1);assert.equal(q.strike_vacuity_stacks,1);
 g.swap_players();g.atk(10);assert.equal(q.strike_vacuity_stacks,1);assert.equal(p.flaw,0);
 g.swap_players();g.atk(10);assert.equal(q.strike_vacuity_stacks,0);assert.equal(q.flaw,1);assert.equal(q.hp,86);
});
scenario('missing-context-keeps-native-path',()=>{
 const g=new GameState(undefined,undefined,'no-fate');const before=g.apply_p5_fates_setup;
 assert.equal(installScrollOpening(root,g,swogi,undefined),null);assert.equal(g.apply_p5_fates_setup,before);
});
console.log(JSON.stringify({passed:true,scenarios:names.length,names,source_based_software_only:true}));
