// Source-derived software boundaries. These are not independent replay wins.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execute} from '../tools/full_battle_bridge_v124.mjs';
import {FIST_STANCE,STICK_STANCE} from '../external/yisim/card_info.js';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const facts=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/season-batch-catalogue-v124.json')));
const cases=[],failures=[],covered=new Set();
const scenario=(name,ids,fn)=>{try{fn();cases.push(name);ids.forEach(x=>covered.add(x));}catch(e){failures.push({name,ids,error:e.stack});}};
const eq=assert.equal;
const rawBy=(predicate)=>{const found=Object.values(facts.raw_cards).find(c=>facts.raw_to_runtime[c.id]&&predicate(c));assert.ok(found,'fixture card must exist');return found.id;};
const byName=name=>rawBy(c=>c.name.includes(name));
const basePlayer=raw=>({character:'he1',hp:100,max_hp:100,cultivation:20,round_number:13,destiny:100,qi:0,def:0,physique:0,max_physique:100,hand_count:0,cards:raw.map(x=>facts.raw_to_runtime[x])});
function input(ids=[],opt={}){
 const raws=opt.raw??Array(8).fill(0),otherRaw=opt.otherRaw??Array(8).fill(0);
 return {players:[{...basePlayer(raws),...opt.p},{...basePlayer(otherRaw),cultivation:10,...opt.q}],first_player:opt.first??0,seed:'season-batch-software',max_turns:64,include_trace:true,current_rules_context:{realms:[5,5]},
  ...opt.battle,season_batch:{players:[{ids,raw_cards:raws,...opt.data},{ids:opt.otherIds??[],raw_cards:otherRaw,...opt.otherData}]}};
}
function fresh(ids=[],opt={}){
 return execute(input(ids,opt),({game:g,seasonBatch:a,swogi})=>{
  if(opt.setup!==false)g.start_of_game_setup();
  const p=g.players[0],q=g.players[1];
  const select=(slot=0)=>{p.currently_triggering_card_idx=slot;p.currently_triggering_card_id=p.cards[slot];p.currently_playing_card_idx=slot;p.trigger_depth=1;};select();
  return {g,p,q,a,select,swogi};
 });
}
scenario('two-sided sounds keep separate switches',[1004,1008],()=>{
 const {p,q}=fresh([1004,1008],{data:{switches:{1004:true,1008:true}}});eq(p.internal_injury,3);eq(q.internal_injury,3);eq(p.apparition_confusion_stacks,2);eq(q.apparition_confusion_stacks,2);
 const off=fresh([1004,1008],{data:{switches:{1004:false,1008:false}}});eq(off.p.internal_injury,0);eq(off.q.apparition_confusion_stacks,0);
});
scenario('third own-turn damage window, both damage types',[1010],()=>{
 const {g,p,q}=fresh([1010],{data:{switches:{1010:true}}});g.currentSeasonTurnStart();g.atk(10);eq(q.hp,90);g.currentSeasonTurnStart();g.currentSeasonTurnStart();g.atk(10);eq(q.hp,84);g.deal_damage(10);eq(q.hp,78);g.currentSeasonTurnStart();g.atk(10);eq(q.hp,68);
});
scenario('late physical slot attack and last slot debuff bonus',[3003,7088],()=>{
 const {g,p,q,select}=fresh([3003,7088]);p.internal_injury=6;p.weaken=0;select(3);g.atk(10);eq(q.hp,90);select(4);g.atk(10);eq(q.hp,79);select(7);g.atk(10);eq(q.hp,66);g.atk(10,true);eq(q.hp,56);
});
scenario('skipped slots preserve actual selection',[5010],()=>{const raw=Array(8).fill(byName('木灵印'));raw[7]=0;const {g,p}=fresh([5010],{raw,data:{switches:{5010:true}}});p.next_card_index=5;g.currentSeasonSkipSelected();eq(p.next_card_index,7);});
scenario('no-attack turn grants sword intent only once at end',[7002],()=>{const {g,p}=fresh([7002]);p.this_turn_attacked=false;g.currentSeasonNoAttackTurnEnd();eq(p.sword_intent,1);p.this_turn_attacked=true;g.currentSeasonNoAttackTurnEnd();eq(p.sword_intent,1);});
scenario('cloud-sea preserves chain and grants qi on noncloud consumption',[7010],()=>{const raw=[byName('云剑'),0,0];const {g,p,select}=fresh([7010],{raw});g.do_cloud_sword_softheart_and_friends(p.cards[0]);eq(p.cloud_sea,1);select(1);g.currentSeasonCloudSeaConsumed();eq(p.qi,1);});
scenario('first sword formation defensive opening',[7017],()=>{const {g,p}=fresh([7017],{raw:[byName('剑阵'),0,0]});g.do_cloud_sword_softheart_and_friends(p.cards[0]);eq(p.def,7);eq(p.guard_up,1);g.do_cloud_sword_softheart_and_friends(p.cards[0]);eq(p.def,7);});
scenario('eighth slot replacement and second-grade upgrade',[7021],()=>{let x=fresh([7021]);eq(x.p.cards[7],facts.raw_to_runtime[11]);x=fresh([7021],{raw:[0,0,0,0,0,0,0,11]});eq(x.p.cards[7],facts.raw_to_runtime[10011]);});
scenario('eighth physical slot injury',[7022],()=>{const {g,p,q,select}=fresh([7022]);select(7);g.do_cloud_sword_softheart_and_friends(p.cards[7]);eq(q.internal_injury,2);});
scenario('stored divination consumer, complete map and absence',[7024],()=>{eq(fresh([7024],{data:{permanent:{10037:7}}}).p.hexagram,7);eq(fresh([7024],{data:{permanent:{}}}).p.hexagram,0);assert.throws(()=>fresh([7024]),/complete_permanent/);});
scenario('metal and water before-body effects',[7026],()=>{const {g,p,select}=fresh([7026],{raw:[byName('金灵印'),byName('水灵印'),0]});g.do_cloud_sword_softheart_and_friends(p.cards[0]);eq(p.qi,1);select(1);g.do_cloud_sword_softheart_and_friends(p.cards[1]);eq(p.penetrate,2);});
scenario('formation repeat uses first grade and restores high grade',[7031],()=>{const raw=rawBy(c=>c.name.includes('灵阵')&&c.id>=10000&&facts.raw_to_runtime[c.id-10000]&&c.anima>=0);const {g,p,a}=fresh([7031],{raw:[raw,0,0],data:{switches:{7031:true}},p:{qi:99}});p.trigger_depth=0;g.play_card(p.cards[0],0);const events=a.metadata().events.filter(e=>e.strategy_id===7031&&e.phase==='first_spirit_formation_replay');eq(events.length,1);eq(events[0].replay,facts.raw_to_runtime[raw-Math.trunc(raw/10000)%100*10000]);eq(p.cards[0],facts.raw_to_runtime[raw]);});
scenario('hexproof toggle does not disable separate opening heal',[7036],()=>{const {p}=fresh([7036],{data:{switches:{7036:false}},p:{hp:70}});eq(p.hp,79);eq(p.hexproof,0);eq(fresh([7036],{data:{switches:{7036:true}}}).p.hexproof,2);});
scenario('life-cost card damage uses configured cost',[7037],()=>{const raw=rawBy(c=>c.hpCost===5);const {g,p,q}=fresh([7037],{raw:[raw,0,0]});g.do_cloud_sword_softheart_and_friends(p.cards[0]);eq(q.hp,98);});
scenario('first physique gain resets on own turn',[7042],()=>{const {g,p}=fresh([7042]);g.increase_idx_physique(0,1);g.increase_idx_physique(0,1);eq(p.qi,1);g.currentSeasonTurnStart();g.increase_idx_physique(0,1);eq(p.qi,2);});
scenario('reactivation grants qi once per own turn',[7048],()=>{const {g,p}=fresh([7048]);g.increase_idx_activate(0,'activate_wood_spirit_stacks',1);eq(p.qi,0);g.increase_idx_activate(0,'activate_wood_spirit_stacks',1);g.increase_idx_activate(0,'activate_fire_spirit_stacks',2);eq(p.qi,1);g.currentSeasonTurnStart();g.increase_idx_activate(0,'activate_wood_spirit_stacks',1);eq(p.qi,2);});
scenario('formation career and injury text classify unrestrained',[7049,7068,7052],()=>{const raw=rawBy(c=>c.career===3);const {g,p}=fresh([7049,7052],{raw:[raw,0,0]});eq(g.is_unrestrained_sword(p.cards[0]),true);g.do_cloud_sword_softheart_and_friends(p.cards[0]);eq(p.qi,1);const x=fresh([7068],{raw:[rawBy(c=>c.desc.includes('[击伤]')),0,0]});eq(x.g.is_unrestrained_sword(x.p.cards[0]),true);});
scenario('divination first-use weakness',[7057],()=>{const {g,p,q}=fresh([7057],{raw:[byName('卦'),0,0]});g.do_cloud_sword_softheart_and_friends(p.cards[0]);eq(q.weaken,1);p.can_post_action[0]=true;g.do_cloud_sword_softheart_and_friends(p.cards[0]);eq(q.weaken,1);});
for(const [id,word,minRound] of [[7058,'木灵',1],[7100,'火灵',13],[7122,'水灵',1],[7128,'星弈',1],[7129,null,1]])scenario('opening first eligible upgrade '+id,[id],()=>{const raw=rawBy(c=>!c.noUpgrade&&(word?c.name.includes(word):c.desc.includes('灵气'))&&facts.raw_to_runtime[c.id+10000]);const x=fresh([id],{raw:[raw,raw,0],p:{round_number:minRound}});eq(x.p.cards[0],facts.raw_to_runtime[raw+10000]);eq(x.p.cards[1],facts.raw_to_runtime[raw]);});
scenario('exact golden crow base body grants qi',[7060],()=>{const {g,p}=fresh([7060],{raw:[381,0,0]});g.do_cloud_sword_softheart_and_friends(p.cards[0]);eq(p.qi,1);});
scenario('golden scroll replaces only empty neighbours',[7061],()=>{const {p}=fresh([7061],{raw:[0,215,0]});assert.deepEqual(p.cards,[facts.raw_to_runtime[216],facts.raw_to_runtime[215],facts.raw_to_runtime[217]]);});
scenario('first three opponent injury gains add one',[7063],()=>{const {g,q}=fresh([7063]);for(let i=0;i<4;i++)g.increase_idx_debuff(1,'internal_injury',1);eq(q.internal_injury,7);});
scenario('five-element opening activation and related gains',[7066,7095,7096,7098],()=>{const {p,q}=fresh([7066,7095,7096,7098]);eq(p.activate_wood_spirit_stacks,1);eq(p.activate_earth_spirit_stacks,1);eq(p.activate_metal_spirit_stacks,1);eq(p.activate_fire_spirit_stacks,1);eq(p.qi,2);eq(p.def,8);eq(p.penetrate,4);eq(q.hp,96);eq(q.max_hp,96);});
scenario('cloud sword-qi branch qualifies a single hit',[7067],()=>{const {g,p}=fresh([7067],{raw:[byName('云剑'),0,0]});eq(p.sword_qi,1);eq(g.currentSeasonSwordQiQualifies(p.cards[0]),true);});
scenario('first three positive hexagram gains each add one',[7077],()=>{const {g,p}=fresh([7077]);for(let i=0;i<4;i++)g.increase_idx_hexagram(0,1);eq(p.hexagram,7);});
scenario('cultivation boundary for opening star',[7078],()=>{eq(fresh([7078],{p:{cultivation:14}}).p.star_power,1);eq(fresh([7078],{p:{cultivation:15}}).p.star_power,2);});
scenario('accepted selected debuffs recover qi after prevention',[7080],()=>{const {g,p,q}=fresh([7080]);g.increase_idx_debuff(1,'internal_injury',2);g.increase_idx_debuff(1,'wound',2);eq(p.qi,1);q.hexproof=1;g.increase_idx_debuff(1,'weaken',1);eq(p.qi,1);});
scenario('marrow two-element condition and current card grade',[7082],()=>{const raw=7000073;const {g,p,swogi}=fresh([7082],{raw:[raw,byName('木灵印'),byName('水灵印')]});g.just_do_the_card_and_nothing_else(swogi[p.cards[0]]);eq(p.five_elements_heavenly_marrow_rhythm_stacks,facts.raw_cards[raw].otherParams[0]);});
scenario('opening HP counts explicit vase elements',[7083,7085],()=>{const {p}=fresh([7083,7085],{raw:[byName('木灵印'),0,0],data:{vase:[byName('火灵印'),byName('水灵印'),byName('水灵印')]}});eq(p.hp,109);eq(p.max_hp,109);});
scenario('first force bonus and capacity clamp',[7087],()=>{const {g,p}=fresh([7087]);g.increase_idx_force(0,1);eq(p.force,3);g.increase_idx_force(0,1);eq(p.force,4);});
scenario('first five agility gains each add physique',[7091],()=>{const {g,p}=fresh([7091]);for(let i=0;i<6;i++)g.increase_idx_x_by_c(0,'agility',1);eq(p.physique,5);});
scenario('crash-fist qi attack bonus capped at four',[7092],()=>{const {g,p}=fresh([7092],{raw:[byName('崩拳'),0,0],p:{qi:12}});eq(g.currentSeasonAttackBonus(0,false),4);eq(g.currentSeasonAttackBonus(0,true),0);});
scenario('revive adds health, consumes star/hex, respects no-revive',[7093],()=>{let x=fresh([7093]);x.p.hp=-2;x.p.star_power=2;x.p.hexagram=1;x.g.check_idx_for_revive(0);eq(x.p.hp,7);eq(x.p.max_hp,109);eq(x.p.star_power,0);eq(x.p.hexagram,0);x=fresh([7093]);x.p.hp=-2;x.p.star_power=2;x.p.got_void_split_speared=true;x.g.check_idx_for_revive(0);eq(x.p.hp,-2);});
scenario('opening attack toggle and self injury',[7094],()=>{const {p}=fresh([7094],{data:{switches:{7094:true}}});eq(p.increase_atk,1);eq(p.internal_injury,2);});
scenario('effective-round earth and fire effects',[7097,7099],()=>{let x=fresh([7097,7099],{raw:[byName('土灵印'),byName('火灵印'),0],p:{round_number:12}});x.g.do_cloud_sword_softheart_and_friends(x.p.cards[0]);eq(x.p.penetrate,0);x=fresh([7097,7099],{raw:[byName('土灵印'),byName('火灵印'),0]});x.g.do_cloud_sword_softheart_and_friends(x.p.cards[0]);eq(x.p.penetrate,2);x.select(1);x.g.currentSeasonAfterCard(x.p.cards[1]);eq(x.q.hp,94);x.g.currentSeasonAfterCard(x.p.cards[1]);eq(x.q.hp,94);});
scenario('qi-associated card attack bonus includes extra attacks',[7101],()=>{const {g}=fresh([7101],{raw:[rawBy(c=>c.anima<0),0,0]});eq(g.currentSeasonAttackBonus(0,false),3);eq(g.currentSeasonAttackBonus(0,true),3);});
scenario('positive health costs trigger physique, damage does not',[7102],()=>{const {g,p}=fresh([7102]);g.reduce_idx_hp(0,4,true);eq(p.physique,1);g.reduce_idx_hp(0,4,false);eq(p.physique,1);});
scenario('first attack injury stance chooses debuff',[7104],()=>{const {g,p,q}=fresh([7104]);p.stance=FIST_STANCE;g.atk(3);eq(q.decrease_atk,1);g.atk(3);eq(q.decrease_atk,1);});
scenario('second mover receives one early post-action',[7110],()=>{const {g,p,q,a}=fresh([],{otherIds:[7110]});eq(a.counter(q,335),1);g.players.reverse();q.currently_triggering_card_id=q.cards[0];q.currently_playing_card_idx=0;eq(g.if_post_action(),true);eq(a.counter(q,335),0);});
scenario('stance interactions preserve damage and stick bonuses',[7111,7113,7090,27023],()=>{const {g,p,q}=fresh([7111,7113,7090,27023]);eq(p.stance,STICK_STANCE);g.switch_stance();eq(p.physique,3);eq(p.def,3);eq(p.stance,STICK_STANCE);eq(q.hp,95);eq(p.increase_atk,1);});
scenario('skip fifth astral slot recovers health and qi',[7116],()=>{const {g,p}=fresh([7116],{raw:[0,0,0,0,byName('星弈'),0,0,0],p:{hp:70},data:{switches:{7116:true}}});p.next_card_index=4;g.currentSeasonSkipSelected();eq(p.next_card_index,5);eq(p.qi,1);eq(p.hp,73);});
scenario('inclusive half-destiny health increase',[7123],()=>{eq(fresh([7123],{p:{destiny:50}}).p.hp,115);eq(fresh([7123],{p:{destiny:51}}).p.hp,100);});
scenario('first thunder attack applies wound before damage',[7127],()=>{const {g,p,q}=fresh([7127],{raw:[byName('雷'),0,0]});q.def=20;g.atk(10);eq(q.wound,1);eq(p.smash_def,1);});
scenario('clear-heart before/body hooks coexist',[7130,23045,7071],()=>{const {g,p}=fresh([7130,23045,7071],{raw:[19,0,0],p:{qi:4}});g.do_cloud_sword_softheart_and_friends(p.cards[0]);eq(p.qi,5);eq(p.cloud_sea,5);eq(p.cloud_sword_chain_count,2);g.currentSeasonAfterBody(p.cards[0]);eq(p.qi,0);eq(p.sword_qi,5);eq(g.currentSeasonSwordQiQualifies(p.cards[0]),true);});
scenario('positive defense gain adds one only from effective round',[7133],()=>{const {g,p}=fresh([7133]);g.increase_idx_def(0,5);eq(p.def,6);g.increase_idx_def(0,0);eq(p.def,6);});
scenario('unrestrained opening count and water turn defense',[7136,7138],()=>{const {g,p}=fresh([7136,7138]);eq(p.unrestrained_sword_count,1);p.force_of_water=7;g.currentSeasonWaterDefense();eq(p.def,3);});
scenario('cloud-hit override and first eligible five-element upgrade',[11001,11003,11004],()=>{const raw=byName('木灵印');const {g,p}=fresh([11001,11003,11004],{raw:[raw,raw,0]});eq(g.if_cloud_hit(),true);eq(p.physique,3);g.currentSeasonBeforePot(0);eq(p.cards[0],facts.raw_to_runtime[raw+10000]);g.currentSeasonBeforePot(1);eq(p.cards[1],facts.raw_to_runtime[raw]);eq(g.if_fire_spirit(),true);});
for(const id of [7012,7134])scenario('stored swordsmith bonus uncapped '+id,[id],()=>{const {g,p,q}=fresh([id],{raw:[19,0,0],p:{swordsmith_stacks:27}});g.do_clear_heart();eq(q.hp,66);eq(p.swordsmith_stacks,27);});
scenario('wood qi-as-hp conversion and styx precedence',[23066,7115],()=>{const {g,p}=fresh([23066,7115],{raw:[byName('木灵印'),0,0],p:{qi:1,styx:2}});eq(g.currentSeasonStyxCost(p.cards[0],3),1);eq(p.styx,0);eq(g.currentSeasonWoodCost(p.cards[0],1),0);eq(p.hp,97);});
scenario('first configured life-cost card recovery once per turn',[7118],()=>{const raw=rawBy(c=>c.hpCost>0);const {g,p}=fresh([7118],{raw:[raw,0,0],p:{hp:70}});g.currentSeasonAfterHpCost(p.cards[0]);g.currentSeasonAfterHpCost(p.cards[0]);eq(p.qi,1);eq(p.hp,73);g.currentSeasonTurnStart();g.currentSeasonAfterHpCost(p.cards[0]);eq(p.qi,2);eq(p.hp,76);});
scenario('star conversion replaces star gain with opponent injury',[23069],()=>{const {g,p,q}=fresh([23069],{data:{switches:{23069:true}}});g.increase_idx_star_power(0,3);eq(p.star_power,0);eq(q.internal_injury,3);});
scenario('temporary guard expires only remaining generated portion',[23079],()=>{const {g,p}=fresh([23079],{raw:[22,0,0]});g.do_cloud_sword_softheart_and_friends(p.cards[0]);eq(p.guard_up,3);g.reduce_idx_hp(0,5,false);g.do_def_decay();eq(p.guard_up,0);});
scenario('second vase card activates its element',[23058],()=>{const vase=[byName('木灵印'),byName('水灵印'),byName('火灵印')];const {p}=fresh([23058],{data:{vase},p:{five_elements_pure_vase_stacks:1,five_elements_pure_vase_cards:vase.map(x=>facts.raw_to_runtime[x])}});eq(p.activate_water_spirit_stacks,1);});
scenario('styx gain health callback',[27021],()=>{const {g,p}=fresh([27021],{p:{hp:70}});g.increase_idx_styx(0,2);eq(p.hp,72);});
scenario('mortal body qi conversion exemption',[17071],()=>{const {g,p}=fresh([17071],{p:{mortal_body_stacks:1}});g.increase_idx_qi(0,2);eq(p.qi,2);});
scenario('chase restriction exemption retains successful chase',[28001],()=>{const {g,p}=fresh([28001]);p.entangle=1;p.predicament_stacks=1;p.this_card_chases=1;p.max_chases=1;p.chases=0;g.process_this_card_chases();eq(p.chases,1);eq(p.entangle,1);});
scenario('engravings share existing first-use grid ledger',[13005,13010,13011,13012,13014,13018],()=>{
 for(const id of [13005,13010,13011,13012,13014,13018]){
  const raw=byName(id===13011?'金灵印':id===13018?'木灵印':'水灵印');
  const {g,p}=fresh([id],{raw:[raw,0,0,0,0,0,0,0],battle:{season_engraving:{players:[[{strategy_id:id,slot:0}],[]]}}});
  p.increase_atk=3;g.do_cloud_sword_softheart_and_friends(p.cards[0]);
  if(id===13005)eq(p.def,5);
  if(id===13010)eq(p.is_star_point.slice(1,5).filter(Boolean).length,4);
  if(id===13011)eq(p.penetrate,4);
  if(id===13012){eq(p.max_force,7);eq(p.majestic_qi_stacks,3);}
  if(id===13014)eq(p.physique,2);
  if(id===13018){eq(p.increase_atk,1);eq(p.wood_thorn,2);}
  const before={def:p.def,force:p.max_force,phys:p.physique,thorn:p.wood_thorn};g.do_cloud_sword_softheart_and_friends(p.cards[0]);assert.deepEqual({def:p.def,force:p.max_force,phys:p.physique,thorn:p.wood_thorn},before);
 }
});
scenario('unknown starts and switches fail rather than silently default',[],()=>{assert.throws(()=>fresh([1004]),/explicit_switch/);const x=input([7002]);delete x.season_batch.players[0].raw_cards;assert.throws(()=>execute(x,()=>{}),/explicit_raw_card/);});
const expected=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-season-batch-v124.json'))).implemented_ids;
const missing=expected.filter(x=>!covered.has(x));
console.log(JSON.stringify({scenarios:cases.length,failures,covered_ids:[...covered].sort((a,b)=>a-b),missing_ids:missing,not_real_replays:true,training_labels:0}));
if(failures.length||missing.length)process.exitCode=1;
