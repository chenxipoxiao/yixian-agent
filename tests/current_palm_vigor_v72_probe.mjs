import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createPalmVigor} from '../tools/current_palm_vigor_v72.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const facts=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-palm-vigor-v72.json')));
const rt=id=>Object.entries(facts.runtime_classification).find(([k,v])=>v.identities.some(c=>c.raw_id===id))?.[0];
const names=[],scenario=(name,fn)=>{fn();names.push(name);};
function fresh(ids=[[7089,15018],[]],order=[0,1],hand=[1,0]){
 const g=new GameState(undefined,undefined,'palm-vigor-software');
 g.players.forEach((p,i)=>{p.hp=100;p.max_hp=100;p.hand_count=hand[order[i]];p.cards=[rt(10010028),'601011','601011'];p.post_deck_setup();});
 const e=createPalmVigor(root,g,swogi,{players:ids},order);e.installOpening();e.installPlayBoundary();return {g,e};
}
scenario('agility-added-before-palm-body-through-callback',()=>{
 const {g,e}=fresh([[7089],[]]);let seen;
 const body=g.just_do_the_card_and_nothing_else.bind(g);g.just_do_the_card_and_nothing_else=function(card){seen=this.players[0].agility;return body(card);};
 g.play_card(rt(10010028),0);assert.equal(seen,2);assert.equal(e.metadata().events[0].requested,2);
});
for(const id of ['601011','601012','601013',rt(1000001)])scenario('nonpalm-'+id,()=>{
 const {g,e}=fresh([[7089],[]]);g.play_card(id,1);assert.equal(e.metadata().events.length,0);assert.equal(g.players[0].agility,0);
});
scenario('repeated-execution-gains-each-time',()=>{
 const {g,e}=fresh([[7089],[]]);for(let i=0;i<2;i++)g.play_card(rt(10010028),0);
 assert.equal(e.metadata().events.length,2);assert.deepEqual(e.metadata().events.map(e=>e.before),[0,2]);
});
scenario('nested-actual-palm-identity',()=>{
 const {g,e}=fresh([[7089],[]]);const body=g.just_do_the_card_and_nothing_else.bind(g);let once=false;
 g.just_do_the_card_and_nothing_else=function(card){if(!once){once=true;this.trigger_card(rt(10010028),0);}else return body(card);};
 g.play_card('601011',1);assert.equal(e.metadata().events.length,1);assert.equal(e.metadata().events[0].trigger_depth,2);
});
scenario('nested-normal-does-not-inherit-parent-palm',()=>{
 const {g,e}=fresh([[7089],[]]);const body=g.just_do_the_card_and_nothing_else.bind(g);let once=false;
 g.just_do_the_card_and_nothing_else=function(card){if(!once){once=true;this.trigger_card('601011',1);}else return body(card);};
 g.play_card(rt(10010028),0);assert.equal(e.metadata().events.length,1);assert.equal(e.metadata().events[0].trigger_depth,1);
});
scenario('swapped-initiative-and-turn-owner',()=>{
 const {g,e}=fresh([[7089],[]],[1,0]);g.play_card(rt(10010028),0);assert.equal(e.metadata().events.length,0);
 g.players.reverse();g.play_card(rt(10010028),0);assert.equal(e.metadata().events[0].player_index,0);
});
scenario('unknown-actual-identity-refused',()=>{
 const {g}=fresh([[7089],[]]);g.players[0].currently_triggering_card_id='unknown';
 assert.throws(()=>g.do_cloud_sword_softheart_and_friends('unknown'),/unknown_card/);assert.equal(g.players[0].agility,0);
});
scenario('mismatched-actual-identity-refused',()=>{
 const {g}=fresh([[7089],[]]);g.players[0].currently_triggering_card_id='601011';
 assert.throws(()=>g.do_cloud_sword_softheart_and_friends(rt(10010028)),/actual_card_identity/);assert.equal(g.players[0].agility,0);
});
for(const hand of [0,1,15])scenario('opening-explicit-hand-'+hand,()=>{
 const {g,e}=fresh([[15018],[]],[0,1],[hand,0]);g.do_plant_start_permanent_buffs();
 assert.equal(g.players[0].hp,hand?112:100);assert.equal(g.players[0].max_hp,hand?112:100);
 assert.equal(g.players[0].hand_count,hand);assert.equal(e.metadata().events[0].eligible,hand>0);
});
for(const hp of [1,8,9,49,100,101])scenario('opening-floor-current-hp-'+hp,()=>{
 const {g,e}=fresh([[15018],[]]);const p=g.players[0];p.hp=hp;p.max_hp=hp+100;g.do_plant_start_permanent_buffs();
 const amount=Math.trunc(hp*12/100);assert.equal(p.hp,hp+amount);assert.equal(p.max_hp,hp+100+amount);assert.equal(e.metadata().events[0].requested,amount);
});
scenario('opening-healing-prevention-does-not-prevent-max-gain',()=>{
 const {g}=fresh([[15018],[]]);g.players[0].prevent_gain_hp_stacks=1;g.do_plant_start_permanent_buffs();
 assert.equal(g.players[0].hp,100);assert.equal(g.players[0].max_hp,112);
});
scenario('opening-normal-heal-modifiers-and-max-first',()=>{
 const {g}=fresh([[15018],[]]);g.players[0].appetite=3;g.players[0].hp=90;
 g.do_plant_start_permanent_buffs();assert.equal(g.players[0].max_hp,110);assert.equal(g.players[0].hp,103);
});
scenario('opening-after-earlier-hook-before-permanent-plant',()=>{
 const {g,e}=fresh([[15018],[]]);g.players[0].origin_herb_stacks=10;
 const earlier=g.do_plant_start_permanent_buffs.bind(g);g.do_plant_start_permanent_buffs=function(){this.increase_idx_max_hp(0,9);this.increase_idx_hp(0,9);return earlier();};
 g.do_plant_start_permanent_buffs();assert.equal(e.metadata().events[0].before.hp,109);assert.equal(e.metadata().events[0].after.hp,122);assert.equal(g.players[0].hp,132);
});
scenario('opening-before-card-opening',()=>{
 const {g,e}=fresh([[15018],[]]);let observed=[];const opening=g.do_opening.bind(g);
 g.do_opening=function(...args){observed.push(this.players[0].hp);return opening(...args);};g.start_of_game_setup();
 assert.equal(e.metadata().events[0].before.hp,100);assert.ok(observed.includes(112));
});
scenario('both-opening-owners-and-initiative',()=>{
 const {g,e}=fresh([[15018],[15018]],[1,0],[1,0]);g.do_plant_start_permanent_buffs();g.players.reverse();g.do_plant_start_permanent_buffs();
 assert.deepEqual(e.metadata().events.map(x=>[x.player_index,x.requested]),[[1,0],[0,12]]);
});
scenario('duplicate-opening-blocked-no-extra-gain',()=>{
 const {g}=fresh([[15018],[]]);g.do_plant_start_permanent_buffs();assert.throws(()=>g.do_plant_start_permanent_buffs(),/opening_repeated/);assert.equal(g.players[0].hp,112);
});
for(const hp of [0,-1,0.5,178956971])scenario('unsupported-opening-hp-'+hp,()=>{
 const {g}=fresh([[15018],[]]);g.players[0].hp=hp;const old=g.players[0].max_hp;
 assert.throws(()=>g.do_plant_start_permanent_buffs(),/opening_hp_outside/);assert.equal(g.players[0].max_hp,old);
});
scenario('absent-hand-refused',()=>{
 const g=new GameState();delete g.players[0].hand_count;
 assert.throws(()=>createPalmVigor(root,g,swogi,{players:[[15018],[]]}),/hand_count/);
});
scenario('ownership-and-boundary-validation',()=>{
 for(const players of [[],[[],[]],[[7089,7089],[]],[[true],[]],[[7135],[]]])assert.throws(()=>createPalmVigor(root,new GameState(),swogi,{players}),/palm_vigor_unresolved/);
 const {g,e}=fresh();assert.throws(()=>e.installOpening(),/duplicate/);assert.throws(()=>e.installPlayBoundary(),/duplicate/);
 assert.throws(()=>createPalmVigor(root,g,swogi,{players:[[7089],[]]}),/already_installed/);
});
scenario('no-ownership-preserves-methods',()=>{
 const g=new GameState(),a=g.do_plant_start_permanent_buffs,b=g.do_cloud_sword_softheart_and_friends;
 assert.equal(createPalmVigor(root,g,swogi,undefined),null);assert.equal(g.do_plant_start_permanent_buffs,a);assert.equal(g.do_cloud_sword_softheart_and_friends,b);
});
console.log(JSON.stringify({passed:true,scenarios:names.length,names}));
