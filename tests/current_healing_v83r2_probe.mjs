// OpenConfig74 recovery,612 blocking,744 consumption and engraving routing.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installSpiritOutburst} from '../tools/current_spirit_outburst_v83.mjs';
import {installYanQi} from '../tools/current_yan_qi_v83.mjs';
import {installCurrentEngravings} from '../tools/current_engraving_effects_v83.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const facts=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-engraving-effects-v21.json')));
let scenarios=0;
function fresh(){
 const g=new GameState(undefined,undefined,'healing-v83-software');
 for(const p of g.players){Object.assign(p,{character:'sw3',hp:40,max_hp:100,max_physique:100,cards:['601011','601011','601011'],hand_count:0});p.reset_can_play();}
 return g;
}
for(const start of [-5,0,1])for(const blocked of [false,true]){
 const g=fresh(),p=g.players[0],s=installSpiritOutburst(root,g);
 g.current_spirit_outburst_gain(2,4000106);p.hp=start;p.got_void_split_speared=blocked;
 g.increase_idx_hp(0,7);
 assert.equal(p.hp,blocked&&start<=0?start:start+7);assert.equal(s.forPlayer(p).remaining,2);scenarios++;
}
for(const start of [-5,0])for(const blocked of [false,true]){
 const g=fresh(),m=installYanQi(root,g,{players:[{strategy_id:7053},null]}),s=installSpiritOutburst(root,g);
 m.attachHealing(s);g.start_of_game_setup();const p=g.players[0];p.hp=start;p.got_void_split_speared=blocked;
 g.increase_idx_max_hp(0,5);
 assert.equal(p.max_hp,105);assert.equal(p.hp,blocked?start:start+21);
 assert.equal(m.metadata().remaining[0].pending_uses,0); // consumed even when612 blocks recovery
 assert.equal(m.metadata().events.at(-1).requested_bonus,21);scenarios++;
}
for(const id of [13004,13013,13019])for(const start of [-3,0,1])for(const blocked of [false,true]){
 const g=fresh(),p=g.players[0];p.hp=start;p.hp_lost=50;p.got_void_split_speared=blocked;p.internal_injury=1;
 installCurrentEngravings(root,g,{players:[[{strategy_id:id,slot:0}],[]]},[0,1],undefined,swogi);
 p.currently_triggering_card_idx=0;p.trigger_depth=1;p.can_post_action[0]=false;
 g.do_cloud_sword_softheart_and_friends('601011');
 const gain=id===13004?10:id===13013?1:7;
 assert.equal(p.hp,blocked&&start<=0?start:start+gain,JSON.stringify({id,start,blocked}));scenarios++;
}
{
 const g=fresh(),p=g.players[0];installSpiritOutburst(root,g);g.current_spirit_outburst_gain(2,4000106);
 p.hp=-5;g.players[1].hp=100;g.increase_idx_hp(0,110);
 assert.equal(p.hp,100);assert.equal(g.players[1].hp,95);scenarios++;
}
process.stdout.write(JSON.stringify({passed:true,scenarios,scope:'explicit software boundaries, not replay calibration'}));
