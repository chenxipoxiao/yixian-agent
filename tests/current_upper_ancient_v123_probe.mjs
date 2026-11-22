import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createUpperAncient} from '../tools/current_upper_ancient_v123.mjs';
import {installCurrentDelayedEffects} from '../tools/current_delayed_effects_v123.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const cases=[],scenario=(name,fn)=>{fn();cases.push(name);};
function fresh(owners=[true,false],order=[0,1],setup=true){
 const g=new GameState(undefined,undefined,'upper-ancient-software');
 for(const p of g.players)Object.assign(p,{character:'he1',hp:10000,max_hp:10000,cards:['645021','111011','111011']});
 installCurrentDelayedEffects(root,g,swogi);
 const obs=createUpperAncient(root,g,swogi,{players:owners},order);obs.installOpening();
 if(setup)g.start_of_game_setup();
 const p=g.players[0],q=g.players[1];p.currently_triggering_card_id='645021';q.currently_triggering_card_id='645021';
 return {g,p,q,obs};
}
scenario('opening-only-increases-capacity-once',()=>{
 const {g,p,q,obs}=fresh();assert.equal(p.max_force,12);assert.equal(p.force,0);assert.equal(q.max_force,6);assert.equal(p.hp,10000);
 assert.equal(obs.metadata().events.filter(e=>e.phase.startsWith('season_opening')).length,1);
 assert.throws(()=>g.do_plant_start_permanent_buffs(),/opening_repeated/);
});
scenario('opening-preserves-prior-cap-and-force',()=>{
 const {g,p}=fresh([true,false],[0,1],false);p.max_force=8;p.force=4;g.do_plant_start_permanent_buffs();assert.equal(p.max_force,14);assert.equal(p.force,4);
});
scenario('palm-multiple-hits-retain-force-and-amplification',()=>{
 const {g,p,q}=fresh();p.force=3;g.atk(10);g.atk(10);assert.equal(p.force,3);assert.equal(q.hp,9974);assert.equal(p.total_force_lost,0);
});
scenario('nonpalm-consumes-per-hit',()=>{
 const {g,p,q}=fresh();p.force=3;p.currently_triggering_card_id='111011';g.atk(10);g.atk(10);assert.equal(p.force,1);assert.equal(q.hp,9975);
});
scenario('extra-palm-attack-keeps-force',()=>{
 const {g,p,q,obs}=fresh();p.force=3;g.atk(10,true);assert.equal(p.force,3);assert.equal(q.hp,9987);assert.equal(obs.metadata().events.at(-1).is_extra,true);
});
scenario('nonattack-damage-does-not-consume',()=>{
 const {g,p}=fresh();p.force=3;g.deal_damage_inner(10,false,0);assert.equal(p.force,3);
});
scenario('unowned-player-keeps-original-consumption',()=>{
 const {g,p,q}=fresh();g.players.reverse();q.force=3;g.atk(10);assert.equal(q.force,2);assert.equal(p.force,0);
});
scenario('owners-follow-objects-across-seat-reversal',()=>{
 const {g,p,q,obs}=fresh([true,false],[1,0]);assert.equal(p.max_force,6);assert.equal(q.max_force,12);g.players.reverse();q.force=3;g.atk(10);assert.equal(q.force,3);assert.equal(obs.metadata().events.at(-1).player_index,0);
});
scenario('both-owners-have-separate-force',()=>{
 const {g,p,q}=fresh([true,true]);p.force=2;q.force=4;g.atk(10);g.players.reverse();g.atk(10);assert.equal(p.force,2);assert.equal(q.force,4);
});
scenario('force-loss-hooks-are-not-fired-and-refunded',()=>{
 const {g,p}=fresh();p.force=1;p.endless_force_stacks=4;g.atk(10);assert.equal(p.force,1);assert.equal(p.total_force_lost,0);
});
scenario('additive-branch-retains-palm-force',()=>{
 const {g,p,q}=fresh();p.force=3;p.cards[2]='D14161';g.atk(10);assert.equal(p.force,3);assert.equal(q.hp,9987);
});
scenario('additive-branch-nonpalm-still-consumes',()=>{
 const {g,p,q}=fresh();p.force=3;p.cards[2]='D14161';p.currently_triggering_card_id='111011';g.atk(10);assert.equal(p.force,2);assert.equal(q.hp,9987);
});
scenario('inch-force-multiplier-does-not-consume-palm',()=>{
 const {g,p,q}=fresh();p.force=3;p.this_card_crash_fist_inch_force_stacks=1;g.atk(10);assert.equal(p.force,3);assert.equal(q.hp,9984);
});
scenario('unknown-actual-card-refuses-force-consumption',()=>{
 const {g,p}=fresh();p.force=3;p.currently_triggering_card_id='unknown';assert.throws(()=>g.currentUpperAncientConsumeForce(0,false),/unknown_actual_card/);assert.equal(p.force,3);
});
scenario('invalid-or-duplicate-ownership-refused',()=>{
 const {g}=fresh();assert.throws(()=>createUpperAncient(root,g,swogi,{players:[true,false]}),/already_installed/);
 assert.throws(()=>createUpperAncient(root,new GameState(),swogi,{players:[1,0]}),/explicit_owners_required/);
});
scenario('unadmitted-game-unchanged',()=>{
 const g=new GameState();assert.equal(createUpperAncient(root,g,swogi,undefined),null);assert.equal(g.currentUpperAncientOwns,undefined);
});
console.log(JSON.stringify({scenarios:cases.length,cases,additive_branch_card_admitted:false}));
