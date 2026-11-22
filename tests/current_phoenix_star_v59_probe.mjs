import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createPhoenixStar} from '../tools/current_phoenix_star_v59.mjs';
import {installCurrentEngravings} from '../tools/current_engraving_effects_v54.mjs';
import {installSevenStars} from '../tools/current_seven_stars_v39.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const names=[],scenario=(name,fn)=>{fn();names.push(name);};
function fresh(ids=[[7064,7079],[]],order=[0,1],engraving=null){
 const g=new GameState(undefined,undefined,'phoenix-star-software');
 for(const p of g.players){p.hp=p.max_hp=100;p.round_number=13;p.cards=['601011','601011','601011'];p.post_deck_setup();}
 const e=createPhoenixStar(root,g,{players:ids},order);
 if(engraving)installCurrentEngravings(root,g,{players:engraving},order,undefined,swogi);
 e.installBeforeEngraving();e.installOpening(7079);e.installOpening(7064);
 g.do_plant_start_permanent_buffs();g.players.reverse();g.do_plant_start_permanent_buffs();g.players.reverse();
 return {g,e};
}
const events=(e,id)=>e.metadata().events.filter(x=>x.strategy_id===id);
function before(g,idx){const p=g.players[0];p.currently_playing_card_idx=idx;p.currently_triggering_card_idx=idx;p.trigger_depth=1;g.do_cloud_sword_softheart_and_friends(p.cards[idx]);p.trigger_depth=0;}
for(const round of [12,13])for(const hp of [19,20,21])scenario('phoenix-round-'+round+'-hp-'+hp,()=>{
 const {g,e}=fresh([[7064],[]]),p=g.players[0];p.round_number=round;p.hp=hp;g.do_def_decay();
 const trigger=round>=13&&hp<=20;assert.equal(p.guard_up,Number(trigger));assert.equal(events(e,7064).length,Number(trigger));
 assert.equal(e.metadata().remaining[0].phoenix,!trigger);
});
scenario('phoenix-consumes-once-and-does-not-reset-on-opening-call',()=>{
 const {g,e}=fresh([[7064],[]]),p=g.players[0];p.hp=20;g.do_def_decay();g.reduce_idx_x_by_c(0,'guard_up',1);
 g.do_plant_start_permanent_buffs();g.do_def_decay();assert.equal(p.guard_up,0);assert.equal(events(e,7064).length,1);
});
scenario('phoenix-ignores-damage-crossing-threshold-until-next-turn',()=>{
 const {g,e}=fresh([[7064],[]]),p=g.players[0];p.hp=21;p.internal_injury=2;g.sim_turn();
 assert.equal(p.hp,19);assert.equal(events(e,7064).length,0);g.sim_turn();assert.equal(events(e,7064).length,1);
});
scenario('phoenix-start-before-regeneration-not-after',()=>{
 const {g,e}=fresh([[7064],[]]),p=g.players[0];p.hp=20;p.regen=3;g.sim_turn();
 assert.equal(events(e,7064).length,1);assert.equal(events(e,7064)[0].hp,20);assert.ok(p.hp>20);
});
scenario('phoenix-survives-expiring-engraving-guard-cleanup',()=>{
 const {g,e}=fresh([[7064],[]],[0,1],[[{strategy_id:13008,slot:0}],[]]),p=g.players[0];
 before(g,0);assert.ok(p.guard_up>0);p.hp=20;g.do_def_decay();assert.equal(p.guard_up,1);
 assert.equal(events(e,7064)[0].guard_before,0);g.do_def_decay();assert.equal(p.guard_up,1);
});
scenario('phoenix-only-own-turn-with-seat-swaps',()=>{
 const {g,e}=fresh([[],[7064]]),owner=g.players[1];owner.hp=20;g.do_def_decay();assert.equal(owner.guard_up,0);
 g.players.reverse();g.do_def_decay();assert.equal(owner.guard_up,1);assert.equal(events(e,7064)[0].player_index,1);
});
for(const order of [[0,1],[1,0]])scenario('star-three-charges-both-seat-orders-'+order,()=>{
 const {g,e}=fresh([[7079],[]],order);if(order[0]!==0)g.players.reverse();const p=g.players[0],enemy=g.players[1];
 before(g,0);assert.equal(enemy.internal_injury,0);assert.equal(e.metadata().remaining[0].star,3);
 for(let i=0;i<5;i++)before(g,2);
 assert.equal(enemy.internal_injury,3);assert.equal(events(e,7079).length,3);assert.ok(events(e,7079).every(x=>x.player_index===0));
 assert.deepEqual(events(e,7079).map(x=>x.after.charges),[2,1,0]);
});
scenario('star-reads-live-grid-after-activation',()=>{
 const {g,e}=fresh([[7079],[]]);before(g,0);g.become_idx_star_point(0,0);before(g,0);
 assert.equal(events(e,7079).length,1);assert.equal(events(e,7079)[0].slot,0);
});
scenario('star-current-execution-slot-must-match-real-card',()=>{
 const {g}=fresh([[7079],[]]),p=g.players[0];p.trigger_depth=1;p.currently_playing_card_idx=0;p.currently_triggering_card_idx=2;
 assert.throws(()=>g.do_cloud_sword_softheart_and_friends(p.cards[2]),/temporary_or_unknown_card_grid/);
});
scenario('star-rejects-nested-reference-even-on-nonstar-slot',()=>{
 const {g,e}=fresh([[7079],[]]),p=g.players[0];p.trigger_depth=2;p.currently_triggering_card_idx=p.currently_playing_card_idx=0;
 assert.throws(()=>g.do_cloud_sword_softheart_and_friends(p.cards[0]),/temporary_or_unknown_card_grid/);assert.equal(e.metadata().remaining[0].star,3);
});
scenario('exhausted-star-does-not-block-unrelated-nested-card',()=>{
 const {g,e}=fresh([[7079],[]]);for(let i=0;i<3;i++)before(g,2);
 g.players[0].trigger_depth=2;g.do_cloud_sword_softheart_and_friends(g.players[0].cards[2]);assert.equal(events(e,7079).length,3);
});
scenario('star-injury-uses-normal-hexproof-and-consumes-charge',()=>{
 const {g,e}=fresh([[7079],[]]);g.players[1].hexproof=1;before(g,2);
 assert.equal(g.players[1].internal_injury,0);assert.equal(g.players[1].hexproof,0);assert.equal(e.metadata().remaining[0].star,2);
});
scenario('star-resolves-before-attack-engraving',()=>{
 const {g,e}=fresh([[7079],[]],[0,1],[[{strategy_id:13016,slot:2}],[]]);let injuryAtDamage=null;
 const native=g.deal_damage.bind(g);g.deal_damage=function(...args){injuryAtDamage=this.players[1].internal_injury;return native(...args);};
 g.players[0].sword_intent=20;before(g,2);assert.equal(injuryAtDamage,1);assert.equal(events(e,7079).length,1);
});
scenario('ordinary-repeat-play-consumes-each-real-star-execution',()=>{
 const {g,e}=fresh([[7079],[]]);g.players[0].is_star_point[0]=true;
 g.play_card('601011',0);g.play_card('601011',0);assert.equal(events(e,7079).length,2);
});
scenario('seven-stars-next-grid-is-not-the-current-grid',()=>{
 const {g,e}=fresh([[7079],[]]);
 // 7056 is separately installed outside7079, matching bridge order.
 installSevenStars(root,g,{players:[{strategy_id:7056,unlocked_slots:3},null]},[0,1]);g.do_plant_start_permanent_buffs();
 g.players[0].cards[0]='121011';before(g,0);assert.equal(events(e,7079).length,0);
});
scenario('independent-owners-share-neither-charges-nor-guard',()=>{
 const {g,e}=fresh([[7064,7079],[7064,7079]]);for(let i=0;i<2;i++){g.players[0].hp=20;g.do_def_decay();before(g,2);g.players.reverse();}
 assert.deepEqual(e.metadata().remaining.map(x=>[x.phoenix,x.star]),[[false,2],[false,2]]);
});
scenario('metadata-is-detached-and-duplicate-hooks-rejected',()=>{
 const {g,e}=fresh();const copy=e.metadata();copy.remaining[0].star=99;assert.equal(e.metadata().remaining[0].star,3);
 assert.throws(()=>e.installBeforeEngraving(),/duplicate_before_boundary/);assert.throws(()=>e.installOpening(7064),/duplicate_or_unknown_opening/);
 assert.throws(()=>createPhoenixStar(root,g,{players:[[7064],[]]}),/already_installed/);
});
console.log(JSON.stringify({passed:true,scenarios:names.length,names}));
