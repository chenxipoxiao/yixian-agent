import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {registerHexagramFates,installHexagramFates,hexagramFatesFacts} from '../tools/current_hexagram_fates_v79r2.mjs';
import {installCurrentFanQi} from '../tools/current_fan_qi_v79r2.mjs';
import {createOpeningQi} from '../tools/current_opening_qi_v79r2.mjs';
import {installCurrentQiPayment} from '../tools/current_qi_payment_v79.mjs';
import {installChasePayment} from '../tools/current_chase_payment_v79.mjs';
import {installCurrentSoundScheduler} from '../tools/current_sound_scheduler_v79.mjs';
import {installChaseSoundScheduler} from '../tools/current_chase_sound_scheduler_v79.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
registerHexagramFates(root,swogi);const f=hexagramFatesFacts(root),names=[];
const scenario=(n,fn)=>{fn();names.push(n);};
function fresh(ids=[195,197],raw=[4000001,4000002,0,0,0,0,0,0],order=[0,1],other=[]){
 const g=new GameState(undefined,undefined,'hexagram-native-boundary');
 const entries=[{fate_ids:ids,starting_raw_cards:raw},{fate_ids:other,starting_raw_cards:Array(8).fill(0)}];
 for(let i=0;i<2;i++){
  const p=g.players[i];p.hp=50;p.max_hp=100;p.cards=entries[order[i]].starting_raw_cards.map(x=>f.raw_to_runtime[x]);p.hand_count=0;
  p.post_deck_setup();p.is_star_point.fill(false);
 }
 installCurrentFanQi(root,g,order);const e=installHexagramFates(root,g,swogi,{players:entries},order);
 return {g,e,p:g.players[order.indexOf(0)],q:g.players[order.indexOf(1)]};
}
function body(g,id,slot=0){const p=g.players[0];p.currently_triggering_card_idx=slot;p.currently_triggering_card_id=id;swogi[id].card_actions(g);}
const expectedHex={4000001:[1,1,2],4000002:[2,3,4],4000003:[1,1,1],4000015:[2,3,4],4000016:[2,3,4],4000025:[2,3,4],4000026:[1,2,3],4000034:[3,4,5]};
for(const c of f.cards)scenario('197-eight-branches-all-grades-'+c.raw_id,()=>{
 const grade=Math.floor((c.raw_id-c.base_id)/10000),{g,e,p,q}=fresh([197]);
 body(g,c.runtime_id,7);
 assert.equal(p.hexagram,expectedHex[c.base_id][grade]+(c.base_id===4000034?1:0));
 if(c.base_id===4000001)assert.equal(p.qi,[5,6,6][grade]);
 if(c.base_id===4000002){assert.equal(p.def,2);assert.equal(q.weaken,2);}
 if(c.base_id===4000003){assert.equal(q.hp,50-[4,7,10][grade]);assert.equal(q.flaw,4);}
 if(c.base_id===4000015){assert.deepEqual(p.is_star_point,[true,true,true,true,true,false,false,false]);assert.equal(p.qi,0);assert.deepEqual(e.metadata().events[0].star_slots,[0,1,2,3,4]);}
 if(c.base_id===4000016){assert.equal(p.max_hp,112+grade);assert.equal(p.hp,62+grade);}
 if(c.base_id===4000025){assert.equal(p.qi,2+grade);assert.equal(q.qi,2+grade);assert.equal(q.internal_injury,3);}
 if(c.base_id===4000026)assert.equal(p.this_card_chases,1);
 if(c.base_id===4000034){assert.equal(q.hp,47-grade);assert.equal(q.max_hp,97-grade);}
 assert.equal(e.metadata().events.filter(x=>x.fate_id===197).length,1);
});
scenario('exact-two-instances-including-duplicates',()=>{
 const {g,e,q}=fresh([197],[4000003,4000003,0,0,0,0,0,0]);body(g,'121051');assert.equal(q.flaw,4);assert.equal(e.metadata().players[0].qualifying_start_count,2);
});
scenario('three-hexagrams-and-nonowner-delegate-base',()=>{
 for(const [ids,raw] of [[[197],[4000003,4000003,4000003,0,0,0,0,0]],[[195],[4000003,4000003,0,0,0,0,0,0]]]){
  const {g,e,q}=fresh(ids,raw);body(g,'121051');assert.equal(q.flaw,0);assert.equal(q.hp,46);assert.equal(e.metadata().events.length,0);
 }
});
scenario('live-transform-never-recounts-original-board',()=>{
 const {g,p,q}=fresh([197]);p.cards.fill('601011');body(g,'121051');assert.equal(q.flaw,4);
 const b=fresh([197],[0,0,0,0,0,0,0,0]);b.p.cards[0]='121051';b.p.cards[1]='121051';body(b.g,'121051');assert.equal(b.q.flaw,0);
});
scenario('kan-uses-trigger-grid-not-playing-grid-and-keeps-direction',()=>{
 const {g,p}=fresh([197]);p.currently_playing_card_idx=1;p.card_play_direction=-1;p.can_play[5]=false;body(g,'122051',7);
 assert.deepEqual(p.is_star_point,[false,false,true,true,true,true,true,false]);
});
scenario('195-positive-once-until-owner-end-and-add-before-clear',()=>{
 const {g,e,p}=fresh([195]);g.increase_idx_qi(0,1);g.increase_idx_qi(0,3);assert.equal(p.hexagram,0);
 const gain=g.increase_idx_hexagram.bind(g);let markerDuringCallback;
 g.increase_idx_hexagram=(idx,n)=>{markerDuringCallback=e.metadata().players[0].pending439;g.increase_idx_qi(0,1);return gain(idx,n);};
 g.current_hexagram_fates_turn_end();assert.equal(markerDuringCallback,true);assert.equal(p.hexagram,1);assert.equal(e.metadata().players[0].pending439,false);
 g.current_hexagram_fates_turn_end();assert.equal(p.hexagram,1);g.increase_idx_qi(0,1);g.current_hexagram_fates_turn_end();assert.equal(p.hexagram,2);
 assert.equal(e.metadata().events.filter(x=>x.phase==='positive_qi_add439').length,2);
});
scenario('zero-and-physique-conversion-never-mark195',()=>{
 const {g,e,p}=fresh([195]);g.increase_idx_qi(0,0);p.dream_nine_evil_ruptsprite_stacks=1;g.increase_idx_qi(0,1);
 p.dream_nine_evil_ruptsprite_stacks=0;p.mortal_body_stacks=1;p.max_physique=100;g.increase_idx_qi(0,2);
 assert.equal(e.metadata().events.length,0);g.current_hexagram_fates_turn_end();assert.equal(p.hexagram,0);
});
for(const [name,installer] of [['plain',installCurrentQiPayment],['chase',installChasePayment],['sound',installCurrentSoundScheduler],['chase-sound',installChaseSoundScheduler]])scenario('195-offturn-owner-turn-end-'+name,()=>{
 const {g,e,p,q}=fresh([195],Array(8).fill(0),[1,0]);installer(g,()=>{});
 g.increase_idx_qi(1,2);assert.equal(e.metadata().events[0].active_player_index,1);g.sim_turn();assert.equal(p.hexagram,0);
 g.players.reverse();g.sim_turn();assert.equal(p.hexagram,1);assert.equal(e.metadata().players.find(x=>x.player_index===0).pending439,false);
 g.sim_turn();assert.equal(p.hexagram,1);assert.equal(q.hexagram,0);
});
scenario('195-before-tail-debuff-decrements',()=>{
 const {g,p}=fresh([195],Array(8).fill(0));installCurrentQiPayment(g);g.increase_idx_qi(0,1);p.weaken=2;
 const gain=g.increase_idx_hexagram.bind(g);let weak;g.increase_idx_hexagram=(idx,n)=>{weak=p.weaken;return gain(idx,n);};g.sim_turn();assert.equal(weak,2);assert.equal(p.weaken,1);
});
scenario('195-opening-qi-variant-and197-dui-opponent-gain',()=>{
 const {g,e,p,q}=fresh([195,197],undefined,[0,1],[195]);
 const opening=createOpeningQi(root,g,{players:[[7059,7109],[]]});[7005,7059,7109].forEach(id=>opening.installBoundary(id));
 body(g,'123031');assert.equal(e.metadata().players.every(x=>x.pending439),true);
 g.current_hexagram_fates_turn_end();assert.equal(p.hexagram,3);assert.equal(q.hexagram,0);g.players.reverse();g.current_hexagram_fates_turn_end();assert.equal(q.hexagram,1);
});
scenario('195-fan-callback-precedes-marker-and197-extra-hex-uses-hook',()=>{
 const {g,e,p,q}=fresh([195,197]);p.star_moon_hexagram_fan_stacks=1;
 const damage=g.deal_damage_inner.bind(g);let seen;
 g.deal_damage_inner=(n,a,i)=>{seen=e.metadata().players[0].pending439;return damage(n,a,i);};g.increase_idx_qi(0,1);assert.equal(seen,false);assert.equal(q.hp,49);
 body(g,'124041');assert.equal(q.hp,42);assert.equal(p.hexagram,4);
});
scenario('invalid-start-binding-and-legacy-state-rejected',()=>{
 const g=new GameState(undefined,undefined,'bad-binding');g.players.forEach(p=>p.cards=['601011']);
 assert.throws(()=>installHexagramFates(root,g,swogi,{players:[{fate_ids:[197],starting_raw_cards:[4000001]},{fate_ids:[],starting_raw_cards:[0]}]}),/starting_mapping_mismatch/);
 g.players[0].hexagrams_explain_stacks=1;
 assert.throws(()=>installHexagramFates(root,g,swogi,{players:[{fate_ids:[197],starting_raw_cards:[0]},{fate_ids:[],starting_raw_cards:[0]}]}),/legacy_fate_state_conflict/);
});
scenario('195-marker-before-wind-spirit267',()=>{const {g,e,p}=fresh([195]);p.wind_spirit_forging_stacks=1;p.max_physique=100;const old=g.increase_idx_physique.bind(g);let pending;g.increase_idx_physique=(i,n)=>{pending=e.metadata().players.find(x=>x.player_index===0).pending439;return old(i,n);};g.increase_idx_qi(0,1);assert.equal(pending,true);});
console.log(JSON.stringify({passed:true,scenarios:names.length,names}));
