import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createChaseSeason} from '../tools/current_chase_season_v57.mjs';
import {installChasePayment} from '../tools/current_chase_payment_v57.mjs';
import {installChaseSoundScheduler} from '../tools/current_chase_sound_scheduler_v57.mjs';
import {installCurrentFullMoon} from '../tools/current_full_moon_v24.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const facts=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-chase-season-v57.json')));
const names=[];const scenario=(name,fn)=>{fn();names.push(name);};
function fresh(ids=[[7051,7054,7112],[]],boards=[[0,0,0],[0,0,0]],order=[0,1],open=true){
 const g=new GameState(undefined,undefined,'chase-season-software');
 g.players.forEach((p,i)=>{p.hp=100;p.max_hp=100;p.cards=boards[order[i]].map(raw=>facts.metadata[raw].runtime_id);p.post_deck_setup();});
 const e=createChaseSeason(root,g,swogi,{players:ids,raw_boards:boards},order);
 e.installBoundary(7112);e.installBoundary(7054);
 if(open)g.do_plant_start_permanent_buffs();return {g,e};
}
const events=(e,id,phase)=>e.metadata().events.filter(x=>x.strategy_id===id&&(!phase||x.phase===phase));
scenario('opening-max-hp-without-implicit-heal-once',()=>{
 const {g,e}=fresh([[7112],[]]);assert.equal(g.players[0].max_hp,120);assert.equal(g.players[0].hp,100);
 g.do_plant_start_permanent_buffs();assert.equal(g.players[0].max_hp,120);assert.equal(events(e,7112).length,1);
});
scenario('first-eligible-upgrade-skips-full-grade-and-ordinary',()=>{
 const {g,e}=fresh([[7054],[]],[[4020026,0,4010026],[0,0,0]]);
 assert.deepEqual(g.players[0].cards,['125033','601011','125033']);assert.equal(events(e,7054)[0].upgrade.slot,2);
 assert.equal(events(e,7054)[0].upgrade.to_raw,4020026);
});
scenario('hidden-name-thunder-card-is-eligible',()=>{
 assert.equal(facts.metadata[29].hidden,true);
 const boards=[[29,4010026,0],[0,0,0]],saved=structuredClone(boards);const {g,e}=fresh([[7054],[]],boards);
 assert.equal(g.players[0].cards[0],facts.metadata[10029].runtime_id);assert.equal(g.players[0].cards[1],'125032');
 assert.deepEqual(boards,saved);assert.equal(events(e,7054)[0].upgrade.from_raw,29);
});
scenario('conditional-chase-text-is-eligible-without-thunder-name',()=>{
 const {g,e}=fresh([[7054],[]],[[12,0,0],[0,0,0]]);
 assert.equal(facts.metadata[12].name_has_thunder,false);assert.equal(g.players[0].cards[0],facts.metadata[10012].runtime_id);
 assert.equal(events(e,7054)[0].upgrade.to_raw,10012);
});
scenario('no-upgrade-candidate-is-explicit-noop',()=>{
 const {g,e}=fresh([[7054],[]],[[4020026,0,0],[0,0,0]]);assert.equal(events(e,7054)[0].upgrade,null);
 g.do_plant_start_permanent_buffs();assert.equal(events(e,7054).length,1);
});
scenario('earlier-copied-deck-transformation-is-observed',()=>{
 const {g,e}=fresh([[7054],[]],[[4010026,29,0],[0,0,0]],[0,1],false);
 g.players[0].cards[0]='125033';g.do_plant_start_permanent_buffs();
 assert.equal(events(e,7054)[0].upgrade.from_raw,29);assert.equal(g.players[0].cards[1],facts.metadata[10029].runtime_id);
});
scenario('unknown-transformed-identity-does-not-guess',()=>{
 const {g}=fresh([[7054],[]],undefined,undefined,false);g.players[0].cards[0]='unknown-card';
 assert.throws(()=>g.do_plant_start_permanent_buffs(),/ambiguous_or_unknown_runtime/);
});
scenario('ambiguous-transformed-normal-attack-does-not-guess',()=>{
 const {g,e}=fresh([[7051],[]],[[16,0,0],[0,0,0]]);g.players[0].cards[0]='601011';
 assert.throws(()=>e.reduceQiCost('601011',0,0),/ambiguous_or_unknown_runtime/);
});
scenario('discount-clamped-and-no-shared-cost-change',()=>{
 const {g,e}=fresh([[7051],[]],[[16,4000026,0],[0,0,0]]),id=g.players[0].cards[0],cost=swogi[id].qi_cost;
 assert.equal(e.reduceQiCost(id,0,1),0);assert.equal(e.reduceQiCost(id,0,0),0);
 assert.equal(e.reduceQiCost(g.players[0].cards[1],1,2),1);assert.equal(swogi[id].qi_cost,cost);
 assert.equal(e.reduceQiCost('601011',2,2),2);assert.equal(events(e,7051).length,3);
});
scenario('nonowner-cost-unchanged-after-player-swap',()=>{
 const {g,e}=fresh([[7051],[]],[[16,0,0],[16,0,0]]);g.players.reverse();
 assert.equal(e.reduceQiCost(g.players[0].cards[0],0,1),1);assert.equal(events(e,7051).length,0);
});
for(const install of [installChasePayment,installChaseSoundScheduler]){
 scenario(install.name+'-discount-before-gather-or-payment',()=>{
  const {g,e}=fresh([[7051],[]],[[16,0,0],[0,0,0]]),p=g.players[0];p.qi=0;
  install(g,e.reduceQiCost.bind(e));g.sim_turn();
  assert.ok(p.can_post_action[0]);assert.ok(p.def>0);assert.equal(p.qi,0);
  assert.equal(events(e,7051)[0].before_cost,1);assert.equal(events(e,7051)[0].after_cost,0);
 });
 scenario(install.name+'-nonowner-still-gathers',()=>{
  const {g,e}=fresh([[],[7051]],[[16,0,0],[16,0,0]]),p=g.players[0];
  install(g,e.reduceQiCost.bind(e));g.sim_turn();assert.equal(p.can_post_action[0],false);assert.ok(p.qi>0);assert.equal(p.def,0);
 });
 scenario(install.name+'-post-action-cost-lookup-defined',()=>{
  const {g,e}=fresh([[7051],[]],[[12,0,0],[0,0,0]]);g.players[0].spiritual_hunter_stacks=1;
  install(g,e.reduceQiCost.bind(e));g.sim_turn();assert.ok(g.players[0].can_post_action[0]);
 });
}
scenario('one-heal-per-success-not-per-request',()=>{
 const {g,e}=fresh([[7112],[]]),p=g.players[0];p.hp=50;p.this_card_chases=3;
 g.process_this_card_chases();assert.equal(p.chases,1);assert.equal(p.hp,53);assert.equal(events(e,7112,'accepted_chase_before235').length,1);
});
for(const condition of ['none','entangle','dream_predicament_for_immortals_stacks','limit'])scenario('no-heal-for-'+condition,()=>{
 const {g,e}=fresh([[7112],[]]),p=g.players[0];p.hp=50;p.this_card_chases=condition==='none'?0:1;
 if(condition==='limit')p.chases=p.max_chases;else if(condition!=='none')p[condition]=1;
 g.process_this_card_chases();assert.equal(p.hp,50);assert.equal(events(e,7112,'accepted_chase_before235').length,0);
});
scenario('agility-chase-without-card-text-heals',()=>{
 const {g}=fresh([[7112],[]]),p=g.players[0];p.hp=50;p.agility=10;g.process_this_card_chases();
 assert.equal(p.agility,0);assert.equal(p.chases,1);assert.equal(p.hp,53);
});
scenario('full-moon-nine-agility-path-heals',()=>{
 const {g}=fresh([[7112],[]]);installCurrentFullMoon(root,g,{players:[[7065],[]]},[0,1]);
 const p=g.players[0];p.hp=50;p.agility=9;g.process_this_card_chases();assert.equal(p.agility,0);assert.equal(p.hp,53);
});
scenario('anti-entangle-exemption-success-heals',()=>{
 const {g}=fresh([[7112],[]]),p=g.players[0];p.hp=50;p.entangle=1;p.prevent_anti_chase=1;p.this_card_chases=1;
 g.process_this_card_chases();assert.equal(p.hp,53);assert.equal(p.entangle,1);assert.equal(p.prevent_anti_chase,0);
});
scenario('healing-before-shadow-owl-cost-keeps-low-hp-alive',()=>{
 const {g}=fresh([[7112],[]]),p=g.players[0];p.hp=2;p.shadow_owl_rabbit_stacks=4;p.this_card_chases=1;
 g.process_this_card_chases();assert.equal(p.hp,5);g.do_shadow_owl_rabbit_lose_hp(1);assert.equal(p.hp,1);
});
scenario('healing-retains-normal-indigestion-callback',()=>{
 const {g,e}=fresh([[7112],[]]),p=g.players[0];p.hp=50;p.indigestion=2;p.this_card_chases=1;
 g.process_this_card_chases();assert.equal(p.hp,51);assert.equal(events(e,7112,'accepted_chase_before235')[0].requested_heal,3);
});
scenario('healing-respects-max-hp',()=>{
 const {g}=fresh([[7112],[]]),p=g.players[0];p.hp=119;p.this_card_chases=1;g.process_this_card_chases();assert.equal(p.hp,120);
});
scenario('source-order-and-owner-objects-survive-swapping',()=>{
 const {g,e}=fresh([[7112],[7112]],undefined,[1,0]);g.players[0].hp=50;g.players[0].this_card_chases=1;g.process_this_card_chases();
 g.players.reverse();g.do_plant_start_permanent_buffs();g.players[0].hp=50;g.players[0].this_card_chases=1;g.process_this_card_chases();
 assert.deepEqual(events(e,7112,'accepted_chase_before235').map(x=>x.player_index),[1,0]);
 assert.equal(g.players[0].hp,53);assert.equal(g.players[1].hp,53);
});
scenario('bad-ownership-and-incomplete-boundaries-rejected',()=>{
 const g=new GameState();g.players.forEach(p=>{p.cards=['601011'];p.post_deck_setup();});
 assert.throws(()=>createChaseSeason(root,g,swogi,{players:[[7054,7054],[]],raw_boards:[[0],[0]]}),/invalid_ownership/);
 const e=createChaseSeason(root,g,swogi,{players:[[7054],[]],raw_boards:[[0],[0]]});e.installBoundary(7054);
 assert.throws(()=>g.do_plant_start_permanent_buffs(),/incomplete/);assert.throws(()=>e.installBoundary(7054),/duplicate/);
});
console.log(JSON.stringify({passed:true,scenarios:names.length,names}));
