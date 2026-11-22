import assert from 'node:assert/strict';
import path from 'node:path';
import fs from 'node:fs';
import crypto from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerCivet,installCivet} from '../tools/current_civet_v38.mjs';
import {installCloudsRain} from '../tools/current_clouds_rain_v39.mjs';
import {installSevenStars} from '../tools/current_seven_stars_v39.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex');
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));registerCivet(root,swogi);
let scenarios=0;
function fresh(raw=433) {
 const alias=String(806141+(raw-433)/10000),g=new GameState(undefined,undefined,'name-context-software');
 for(const p of g.players){p.character='sw3';p.hp=40;p.max_hp=100;p.destiny=40;p.cards=[alias,'601011','601011'];p.hand_count=2;}
 return {g,entry:{hand:[15,15],board:[raw,0,0]}};
}
for(const raw of [433,10433,20433])for(const order of [[0,1],[1,0]]) {
 const {g,entry}=fresh(raw);const cloud=installCloudsRain(root,g,{players:[entry,entry]},order);
 const stars=installSevenStars(root,g,{players:[{strategy_id:7056,unlocked_slots:3},{strategy_id:7056,unlocked_slots:3}]},order);
 const civet=installCivet(root,g,{is_mirror:[false,false]},order);g.start_of_game_setup();
 assert.deepEqual(g.players.map(p=>p.qi),[1,1]);
 assert.deepEqual(cloud.metadata().events.map(e=>e.board_cloud_count),[0,0]);
 assert.deepEqual(cloud.metadata().events.map(e=>e.hand_cloud_count),[2,2]);
 assert.equal(cloud.metadata().evidence_sha256,sha('data/inspection/current-clouds-rain-v39.json'));
 for(let i=0;i<2;i++){g.play_card(g.players[0].cards[0],0);g.swap_players();}
 assert.equal(stars.metadata().events.length,0);assert.deepEqual(stars.metadata().remaining.map(e=>e.charges),[7,7]);
 assert.deepEqual(civet.metadata().events.map(e=>e.player_index),order);
 assert.throws(()=>g.do_cloud_sword_softheart_and_friends('unknown'),/unknown_card_classification/);
 assert.throws(()=>installCloudsRain(root,g,{players:[entry,entry]},order),/already_installed/);
 scenarios++;
}
for(const mutate of [e=>{e.board[1]=999999999;},e=>{e.board[0]=10433;},e=>{e.hand=[15,true];}]) {
 const {g,entry}=fresh();mutate(entry);
 assert.throws(()=>installCloudsRain(root,g,{players:[entry,null]}),/unknown_card|raw_board_mismatch/);scenarios++;
}
{
 const {g,entry}=fresh();for(const p of g.players)p.cards.fill('601011');entry.board=[0,0,0];
 const c=installCloudsRain(root,g,{players:[entry,null]});
 const s=installSevenStars(root,g,{players:[{strategy_id:7056,unlocked_slots:3},null]});
 g.start_of_game_setup();assert.equal(c.metadata().evidence_sha256,sha('data/inspection/current-clouds-rain-v35.json'));
 assert.equal(s.metadata().evidence_sha256,sha('data/inspection/current-seven-stars-v37.json'));
 // A second install cannot cross from the legacy branch to the extended one.
 entry.board[0]=433;
 assert.throws(()=>installCloudsRain(root,g,{players:[entry,null]}),/already_installed/);
 assert.throws(()=>installSevenStars(root,g,{players:[{strategy_id:7056,unlocked_slots:3},null]},[0,1],true),/already_installed/);
 scenarios++;
}
{
 const {g,entry}=fresh();g.players[0].cloud_sword_softheart_stacks=1;
 // Existing classification guard, not an unrelated native cloud callback.
 const facts=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-clouds-rain-v39.json')));
 g.players[0][facts.unsupported_classification_fields[0]]=1;
 installCloudsRain(root,g,{players:[entry,null]});
 assert.throws(()=>g.start_of_game_setup(),/conditional_classification/);scenarios++;
}
{
 const {g}=fresh();g.players[0].cards.fill('601011');
 const s=installSevenStars(root,g,{players:[{strategy_id:7056,unlocked_slots:3},null]},[0,1],true);
 installCivet(root,g,{is_mirror:[false,false]});g.start_of_game_setup();
 // A supported non-star temporary Civet use must not consume a star charge.
 g.trigger_card('806141',0);assert.equal(s.metadata().remaining[0].charges,7);scenarios++;
}
process.stdout.write(JSON.stringify({passed:true,scenarios}));
