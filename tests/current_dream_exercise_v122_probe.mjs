import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerDreamExercise,installDreamExercise,dreamExerciseFacts} from '../tools/current_dream_exercise_v122.mjs';
import {registerDreamBasics,installDreamBasics} from '../tools/current_dream_basics_v93r2.mjs';
import {installCurrentDelayedEffects} from '../tools/current_delayed_effects_v122.mjs';
import {createChaseSeason} from '../tools/current_chase_season_v122.mjs';
import {installCurrentEngravings} from '../tools/current_engraving_effects_v122.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const facts=dreamExerciseFacts(root);registerDreamBasics(root,swogi);registerDreamExercise(root,swogi);
const cases=[],scenario=(name,fn)=>{fn();cases.push(name);};
function fresh(cards=['D14195','111011','111011'],order=[0,1]){
 const g=new GameState(undefined,undefined,'dream-exercise-software');
 for(const p of g.players)Object.assign(p,{character:'he1',hp:10000,max_hp:10000,max_physique:1000,qi:20,cards:[...cards]});
 installCurrentDelayedEffects(root,g,swogi);installDreamBasics(root,g,swogi,order);const obs=installDreamExercise(root,g,swogi,order);
 g.start_of_game_setup();return {g,p:g.players[0],q:g.players[1],obs};
}
for(const c of facts.cards){
 scenario('two-hits-own-and-next-card-'+c.raw_id,()=>{
  const {g,p,q,obs}=fresh([c.runtime_id,'111011','111011']);const hp=q.hp;
  g.play_card(c.runtime_id,0);assert.equal(hp-q.hp,c.config.attack*2);assert.equal(p.physique,4);assert.equal(obs.forPlayer(p).remaining705,1);
  g.play_card('111011',1);assert.equal(p.physique,6);assert.equal(obs.forPlayer(p).remaining705,0);
  g.play_card('111011',1);assert.equal(p.physique,6);assert.equal(p.dream_exercise_fist_atk_physique_pct,0);
 });
 scenario('strict-chase-and-transform-metadata-'+c.raw_id,()=>{
  const {g,p}=fresh([c.runtime_id,'111011','111011']),board=[c.raw_id,1000001,1000001];
  assert.ok(createChaseSeason(root,g,swogi,{players:[[7051],[]],raw_boards:[board,board]}));
  installCurrentEngravings(root,g,{players:[[{strategy_id:13003,slot:0}],[]]},[0,1],{players:[board,board]},swogi);
  g.play_card(c.runtime_id,0);assert.equal(p.cards[0],c.runtime_id);
 });
}
scenario('actual-injury-each-hit-rounded-down',()=>{
 const {g,p,q,obs}=fresh();q.def=6;g.play_card('D14195',0);
 assert.equal(p.physique,2);assert.deepEqual(obs.metadata().events.filter(e=>e.kind==='hit_705').map(e=>[e.injury,e.requested_physique]),[[1,0],[7,2]]);
});
scenario('fully-blocked-following-card-consumes-once',()=>{
 const {g,p,q,obs}=fresh();g.play_card('D14195',0);q.def=1000;g.play_card('111011',1);
 assert.equal(p.physique,4);assert.equal(obs.forPlayer(p).remaining705,0);
 assert.equal(obs.metadata().events.filter(e=>e.kind==='post_card_706').length,1);
});
scenario('extra-attack-neither-gains-nor-consumes',()=>{
 const {g,p,obs}=fresh();g.play_card('D14195',0);p.currently_triggering_card_id='111011';g.atk(20,true);g.do_post_crash_fist('111011');
 assert.equal(p.physique,4);assert.equal(obs.forPlayer(p).remaining705,1);
});
scenario('nonattack-damage-neither-gains-nor-consumes',()=>{
 const {g,p,obs}=fresh();g.play_card('D14195',0);g.deal_damage_inner(20,false,0);g.do_post_crash_fist('111011');
 assert.equal(p.physique,4);assert.equal(obs.forPlayer(p).remaining705,1);
});
scenario('nonattack-card-retains-next-attack',()=>{
 const {g,p,obs}=fresh(['D14195','111021','111011']);g.play_card('D14195',0);g.play_card('111021',1);
 assert.equal(obs.forPlayer(p).remaining705,1);g.play_card('111011',2);assert.equal(obs.forPlayer(p).remaining705,0);
});
scenario('two-high-cards-maintain-one-continuation',()=>{
 const {g,p,obs}=fresh(['D14194','D14195','111011']);g.play_card('D14194',0);g.play_card('D14195',1);
 assert.equal(p.physique,8);assert.equal(obs.forPlayer(p).remaining705,1);g.play_card('111011',2);assert.equal(p.physique,10);
});
scenario('pending-count-is-not-percentage-and-consumed-once-per-card',()=>{
 const {g,p,obs}=fresh();p.currently_triggering_card_id='D14195';p.currently_playing_card_idx=0;
 g.executeCurrentDreamExercise('D14195');g.executeCurrentDreamExercise('D14195');
 assert.equal(obs.forPlayer(p).remaining705,2);assert.equal(p.physique,8);
 g.atk(10);assert.equal(p.physique,12);g.do_post_crash_fist('D14195');assert.equal(obs.forPlayer(p).remaining705,1);
});
scenario('mixed-low-high-and-low707-before-next-card',()=>{
 const {g,p,obs}=fresh(['D14191','D14195','111011']);g.play_card('D14191',0);assert.equal(p.physique,2);
 g.play_card('D14195',1);assert.equal(p.physique,8);assert.equal(obs.forPlayer(p).remaining705,1);
 g.play_card('D14191',0);assert.equal(p.physique,12);assert.equal(obs.forPlayer(p).remaining705,0);
 g.play_card('111011',2);assert.equal(p.physique,14);
});
scenario('player-counters-follow-player-object',()=>{
 const {g,p,q,obs}=fresh(undefined,[1,0]);g.play_card('D14195',0);g.players.reverse();g.play_card('D14195',0);
 assert.equal(obs.forPlayer(p).remaining705,1);assert.equal(obs.forPlayer(q).remaining705,1);
 assert.deepEqual(obs.metadata().events.filter(e=>e.kind==='card_body').map(e=>e.player_index),[1,0]);
});
scenario('unadmitted-game-keeps-native-path',()=>{
 const {g,obs}=fresh(['111011','111011','111011']);g.play_card('D14195',0);assert.equal(g.currentDreamExerciseActive,false);assert.equal(obs.metadata(),null);
});
scenario('unknown-legacy-percentage-is-rejected',()=>{
 const g=new GameState();g.players[0].cards=['D14195'];g.players[1].cards=['111011'];g.players[0].dream_exercise_fist_atk_physique_pct=40;
 assert.throws(()=>installDreamExercise(root,g,swogi),/unknown_legacy_percentage/);
});
scenario('wrong-grade-metadata-rejected',()=>{
 const {g}=fresh();assert.throws(()=>createChaseSeason(root,g,swogi,{players:[[7051],[]],raw_boards:[[10030087,1000001,1000001],[10040087,1000001,1000001]]}),/raw_board_mismatch/);
});
console.log(JSON.stringify({scenarios:cases.length,cases}));
