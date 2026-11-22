import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installPreparationConsumption} from '../tools/current_preparation_v77.mjs';
import {installCurrentEngravings} from '../tools/current_engraving_effects_v77.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const names=[],scenario=(name,fn)=>{fn();names.push(name);};
function fresh(order=[0,1],ids=[13015],slot=0){
 const g=new GameState(undefined,undefined,'preparation-software');
 g.players.forEach(p=>{p.hp=80;p.max_hp=100;p.cards=['601011','601011','601011'];p.hand_count=0;p.post_deck_setup();});
 const entries=[[],[]];entries[order[0]]=ids.map(id=>({strategy_id:id,slot}));
 const input={players:entries};installPreparationConsumption(root,g,swogi,input);
 const e=installCurrentEngravings(root,g,input,order,undefined,swogi);
 return {g,e,p:g.players[0],q:g.players[1]};
}
for(const order of [[0,1],[1,0]])scenario('actual-first-use-and-stable-seat-'+order[0],()=>{
 const {g,e,p,q}=fresh(order);g.play_card_inner('601011',0);
 assert.equal(q.hp,71);assert.equal(q.max_hp,94);assert.equal(q.consume_next_card_played_stacks,1);
 g.play_card_inner('601011',0);assert.equal(q.max_hp,94);assert.equal(q.consume_next_card_played_stacks,1);
 g.players.reverse();g.play_card_inner('601011',0);
 assert.equal(q.consume_next_card_played_stacks,0);assert.equal(q.can_play[0],false);assert.equal(p.hp,77);
 assert.equal(e.metadata().events.find(x=>x.kind==='consume663_before_action').player_index,order[1]);
});
scenario('unused-selected-slot-only',()=>{const {g,q}=fresh([0,1],[13015],1);g.play_card_inner('601011',0);assert.equal(q.max_hp,100);g.play_card_inner('601011',1);assert.equal(q.max_hp,94);});
scenario('already-used-physical-card',()=>{const {g,p,q}=fresh();p.can_post_action[0]=true;g.play_card_inner('601011',0);assert.equal(q.max_hp,100);});
scenario('temporary-execution-neither-fires-nor-consumes',()=>{const {g,p,q}=fresh();p.trigger_depth=1;p.consume_next_card_played_stacks=2;g.trigger_card('601011',0);assert.equal(p.consume_next_card_played_stacks,2);assert.equal(q.max_hp,100);assert.equal(p.can_play[0],true);});
scenario('guard-blocks-hp-but-not-maxhp-or-mark',()=>{const {g,q,e}=fresh();q.guard_up=1;g.play_card_inner('601011',0);const a=e.metadata().events[0].after;assert.deepEqual(a,{hp:80,max_hp:94,marks:1});assert.equal(q.guard_up,0);});
scenario('maxhp-clamp-after-guard',()=>{const {g,q,e}=fresh();q.hp=100;q.guard_up=1;g.play_card_inner('601011',0);assert.deepEqual(e.metadata().events[0].after,{hp:94,max_hp:94,marks:1});});
scenario('negative-hp-not-clamped-to-zero',()=>{const {g,q,e}=fresh();q.hp=2;g.play_card_inner('601011',0);assert.equal(e.metadata().events[0].after.hp,-4);assert.equal(q.consume_next_card_played_stacks,1);});
scenario('one-mark-consumed-before-own-action',()=>{
 const {g,p}=fresh();p.consume_next_card_played_stacks=2;
 const body=g.just_do_the_card_and_nothing_else.bind(g);let observed;
 g.just_do_the_card_and_nothing_else=function(card){observed=[p.consume_next_card_played_stacks,p.can_play[0]];return body(card);};
 g.play_card_inner('601011',0);assert.deepEqual(observed,[1,false]);assert.equal(p.consume_next_card_played_stacks,1);
});
scenario('mark-gained-during-action-survives-current-card',()=>{
 const {g,p}=fresh();p.consume_next_card_played_stacks=1;
 const body=g.just_do_the_card_and_nothing_else.bind(g);
 g.just_do_the_card_and_nothing_else=function(card){const r=body(card);this.increase_idx_x_by_c(0,'consume_next_card_played_stacks',1);return r;};
 g.play_card_inner('601011',0);assert.equal(p.consume_next_card_played_stacks,1);
});
scenario('nested-body-does-not-pay-second-mark',()=>{
 const {g,p}=fresh();p.consume_next_card_played_stacks=2;
 const body=g.just_do_the_card_and_nothing_else.bind(g);
 g.just_do_the_card_and_nothing_else=function(card){if(p.trigger_depth===1)this.trigger_card('601011',1);return body(card);};
 g.play_card_inner('601011',0);assert.equal(p.consume_next_card_played_stacks,1);assert.equal(p.can_play[0],false);assert.equal(p.can_play[1],true);
});
scenario('both-owners-can-mark-and-consume-in-same-turn',()=>{
 const g=new GameState(undefined,undefined,'both-ash');g.players.forEach(p=>{p.hp=80;p.max_hp=100;p.cards=['601011','601011','601011'];p.post_deck_setup();});
 const input={players:[[{strategy_id:13015,slot:0}],[{strategy_id:13015,slot:0}]]};
 installPreparationConsumption(root,g,swogi,input);const e=installCurrentEngravings(root,g,input,[0,1],undefined,swogi);
 g.play_card_inner('601011',0);g.players.reverse();g.play_card_inner('601011',0);
 assert.equal(e.metadata().events.filter(x=>x.kind==='13015_first_use').length,2);assert.equal(g.players[0].can_play[0],false);assert.equal(g.players[1].consume_next_card_played_stacks,1);
});
scenario('before-later-sword-intent-engraving',()=>{const {g,p,q,e}=fresh([0,1],[13015,13016]);g.play_card_inner('601011',0);assert.equal(e.metadata().events[0].after.hp,80-6);assert.equal(q.hp,68);assert.equal(p.sword_intent,0);});
scenario('nonowner-scheduler-is-original',()=>{const g=new GameState();const old=g.trigger_card;assert.equal(installPreparationConsumption(root,g,swogi,{players:[[{strategy_id:13016,slot:0}],[]]}),false);assert.equal(g.trigger_card,old);});
scenario('invalid-slot-rejected',()=>{assert.throws(()=>fresh([0,1],[13015],8),/Invalid engraving/);});
process.stdout.write(JSON.stringify({passed:true,scenarios:names.length,names}));
