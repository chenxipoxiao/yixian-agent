import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installCloudsRain} from '../tools/current_clouds_rain_v35.mjs';
import {installHeavenSpirit} from '../tools/current_heaven_spirit_v34.mjs';
import {installCurrentSeasonContext} from '../tools/current_season_context_v27.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const facts=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-clouds-rain-v35.json')));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
let scenarios=0;
function fresh(hand=[],board=[0,0,0]) {
 const g=new GameState(undefined,undefined,'clouds-rain-software');
 for(const p of g.players){p.character='sw3';p.hp=50;p.max_hp=100;p.cards=['601011','601011','601011'];p.hand_count=0;}
 g.players[0].hand_count=hand.length;g.players[0].cards=board.map(c=>facts.metadata[c].runtime_id);
 return {g,entry:{hand,board}};
}
// The pool used for counting includes duplicates and currently unplayed cards.
for(let n=0;n<=9;n++) {
 const {g,entry}=fresh(Array(n).fill(15)),calls=[],gain=g.increase_idx_qi.bind(g);
 g.increase_idx_qi=(i,a)=>{calls.push([i,a]);return gain(i,a);};
 const x=installCloudsRain(root,g,{players:[entry,null]});g.start_of_game_setup();
 assert.equal(g.players[0].qi,Math.min(3,Math.floor(n/2)));
 assert.deepEqual(calls,n>=2?[[0,Math.min(3,Math.floor(n/2))]]:[]);
 assert.equal(x.metadata().events[0].hand_cloud_count,n);
 g.do_plant_start_permanent_buffs();assert.equal(x.metadata().events.length,1);scenarios++;
}
{
 const {g,entry}=fresh([1000037,15,213,261],[1000063,0,0]);
 const x=installCloudsRain(root,g,{players:[entry,null]});
 // Source arrays are copied; later runtime upgrade/transformation cannot change the count.
 entry.hand.length=0;g.players[0].cards.fill('601011');g.start_of_game_setup();
 assert.equal(g.players[0].qi,2);assert.equal(x.metadata().events[0].hand_cloud_count,3);
 assert.equal(x.metadata().events[0].board_cloud_count,1);scenarios++;
}
for(const order of [[0,1],[1,0]]) {
 const {g,entry}=fresh([15,15]);g.players[1].hand_count=4;
 const other={hand:[15,15,15,15],board:[0,0,0]},entries=[];
 entries[order[0]]=entry;entries[order[1]]=other;
 const x=installCloudsRain(root,g,{players:entries},order);g.start_of_game_setup();
 assert.deepEqual(g.players.map(p=>p.qi),[1,2]);assert.deepEqual(x.metadata().events.map(e=>e.player_index),order);scenarios++;
}
{
 const {g,entry}=fresh([15,15]),points=[];
 const plants=g.do_plant_start_permanent_buffs.bind(g),debuff=g.increase_idx_debuff.bind(g);
 g.do_plant_start_permanent_buffs=(...a)=>{points.push(['plants',g.players[0].qi]);return plants(...a);};
 g.increase_idx_debuff=(...a)=>{points.push(['3001',g.players[0].qi]);return debuff(...a);};
 const x=installCloudsRain(root,g,{players:[entry,null]});
 installCurrentSeasonContext(root,g,swogi,{players:[[3001],[]]},[0,1]);
 installHeavenSpirit(root,g,{players:[{strategy_id:1001,enabled:true},null]},[0,1]);
 g.start_of_game_setup();assert.deepEqual(points,[['3001',2],['plants',3],['plants',2]]);
 assert.equal(x.metadata().events[0].qi_before,2);scenarios++;
}
{
 const {g,entry}=fresh([15,15,15,15]);g.players[0].stillness_citta_dharma_stacks=2;g.players[0].spiritstat_tune_stacks=3;
 installCloudsRain(root,g,{players:[entry,null]});g.start_of_game_setup();
 assert.equal(g.players[0].hp,54);assert.equal(g.players[0].def,6);scenarios++;
}
for(const field of facts.unsupported_classification_fields)for(const value of [-1,1]) {
 const {g,entry}=fresh([15,15]);g.players[0][field]=value;
 installCloudsRain(root,g,{players:[entry,null]});
 assert.throws(()=>g.start_of_game_setup(),/conditional_classification/);assert.equal(g.players[0].qi,0);scenarios++;
}
for(const change of ['unknown','bool','wrong_board','wrong_count','wrong_character']) {
 const {g,entry}=fresh([15]);
 if(change==='unknown')entry.hand=[999999999];if(change==='bool')entry.hand=[true];
 if(change==='wrong_board')entry.board=[15,0,0];if(change==='wrong_count')g.players[0].hand_count=0;
 if(change==='wrong_character')g.players[0].character='sw1';
 assert.throws(()=>installCloudsRain(root,g,{players:[entry,null]}),/clouds_rain_unresolved/);scenarios++;
}
{
 const {g,entry}=fresh();installCloudsRain(root,g,{players:[entry,null]});
 assert.throws(()=>installCloudsRain(root,g,{players:[entry,null]}),/already_installed/);scenarios++;
}
process.stdout.write(JSON.stringify({passed:true,scenarios}));
