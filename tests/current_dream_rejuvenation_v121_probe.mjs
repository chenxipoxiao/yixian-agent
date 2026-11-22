import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerDreamRejuvenation,installDreamRejuvenation,dreamRejuvenationFacts} from '../tools/current_dream_rejuvenation_v121.mjs';
import {createChaseSeason} from '../tools/current_chase_season_v121.mjs';
import {installCloudsRain} from '../tools/current_clouds_rain_v121.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const facts=dreamRejuvenationFacts(root),prior=new Map(Object.entries(swogi));registerDreamRejuvenation(root,swogi);
for(const [id,v] of prior)if(!facts.cards.some(c=>c.runtime_id===id))assert.equal(swogi[id],v);
assert.throws(()=>registerDreamRejuvenation(root,swogi),/already_registered/);
const cases=[],scenario=(name,fn)=>{fn();cases.push(name);};
function fresh(cards=['D12185','111011','111011'],order=[0,1]){
 const g=new GameState(undefined,undefined,'dream-rejuvenation-software');
 for(const p of g.players)Object.assign(p,{character:'he1',hp:10000,max_hp:10000,qi:20,cards:[...cards]});
 const obs=installDreamRejuvenation(root,g,swogi,order);g.start_of_game_setup();return {g,p:g.players[0],q:g.players[1],obs};
}
for(const c of facts.cards){
 scenario('realm-repeated-'+c.raw_id,()=>{
  const {g,p,q,obs}=fresh([c.runtime_id,'111011','111011']);const hits=[];
  for(let i=0;i<3;i++){const hp=q.hp;g.play_card(c.runtime_id,0);hits.push(hp-q.hp);}
  assert.deepEqual(hits,[c.config.attack,2*c.config.attack,(c.config.level===5?4:2)*c.config.attack]);
  assert.equal(p.dream_revitalized_played_count,3);assert.equal(p.dream_revitalized_doublings,0);
  assert.deepEqual(obs.metadata().events.map(e=>e.count_before),[0,1,2]);
 });
 scenario('strict-metadata-'+c.raw_id,()=>{
  const {g,p}=fresh([c.runtime_id,'111011','111011']);const board=[c.raw_id,1000001,1000001];
  assert.ok(createChaseSeason(root,g,swogi,{players:[[7051],[]],raw_boards:[board,board]}));
  p.character='sw3';p.hand_count=0;assert.ok(installCloudsRain(root,g,{players:[{hand:[],board},null]}));
 });
}
scenario('mixed-realms-share-counter-across-slots',()=>{
 const {g,p,q}=fresh(['D12181','D12185','111011']);const hp=q.hp;
 g.play_card('D12181',0);g.play_card('D12185',1);g.play_card('D12185',1);
 assert.equal(hp-q.hp,5+24+48);assert.equal(p.dream_revitalized_played_count,3);
});
scenario('other-card-does-not-increment-or-reset',()=>{
 const {g,p}=fresh();g.play_card('D12185',0);g.play_card('111011',1);assert.equal(p.dream_revitalized_played_count,1);
});
scenario('player-counter-independent-and-order-preserved',()=>{
 const {g,p,q,obs}=fresh(undefined,[1,0]);g.play_card('D12185',0);g.players.reverse();g.play_card('D12185',0);
 assert.equal(p.dream_revitalized_played_count,1);assert.equal(q.dream_revitalized_played_count,1);
 assert.deepEqual(obs.metadata().events.map(e=>e.player_index),[1,0]);
});
scenario('counter-updated-after-hit',()=>{
 const {g,p}=fresh();p.dream_revitalized_played_count=2;const original=g.atk.bind(g);let observed=false;
 g.atk=function(n){assert.equal(p.dream_revitalized_played_count,2);original(n);assert.equal(p.dream_revitalized_played_count,2);observed=true;};
 g.play_card('D12185',0);assert.ok(observed);assert.equal(p.dream_revitalized_played_count,3);
});
scenario('double-after-additive-ironbone-before-percentage',()=>{
 const {g,p,q}=fresh();p.dream_revitalized_played_count=2;p.increase_atk=3;p.weaken=1;q.metal_spirit_iron_bone_stacks=1;
 const hp=q.hp;g.play_card('D12185',0);assert.equal(hp-q.hp,24);
});
scenario('new-game-counter-is-zero',()=>{const {p,q}=fresh();assert.equal(p.dream_revitalized_played_count,0);assert.equal(q.dream_revitalized_played_count,0);});
scenario('unadmitted-game-keeps-native-temporary-behavior',()=>{
 const {g,obs}=fresh(['111011','111011','111011']);g.players[0].trigger_depth=1;g.players[0].currently_playing_card_idx=1;g.trigger_card('D12185',1);
 assert.equal(g.currentDreamRejuvenationActive,false);assert.equal(obs.metadata(),null);
});
scenario('unknown-counter-rejected',()=>{const {g,p}=fresh();p.dream_revitalized_played_count=undefined;assert.throws(()=>g.play_card('D12185',0),/664_numeric_domain/);});
scenario('unsupported-counter-domain-rejected',()=>{const {g,p}=fresh();p.dream_revitalized_played_count=21;assert.throws(()=>g.play_card('D12185',0),/664_numeric_domain/);});
scenario('wrong-grade-metadata-rejected',()=>{
 const {g}=fresh();assert.throws(()=>createChaseSeason(root,g,swogi,{players:[[7051],[]],raw_boards:[[4030087,1000001,1000001],[4040087,1000001,1000001]]}),/raw_board_mismatch/);
});
console.log(JSON.stringify({scenarios:cases.length,cases}));
