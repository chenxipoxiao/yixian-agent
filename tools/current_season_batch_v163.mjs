import {dreamFormationFacts} from './current_dream_formations_v163.mjs';
import {websiteCardFacts} from './current_website_cards_v142.mjs';
import {dreamBrushLoadFacts} from './current_dream_brush_load_v127.mjs';
// Candidate batch: current-season battle effects. Validation is a separate,
// subsequent campaign. The frozen v123 runtime and reports remain callable.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {FIST_STANCE,STICK_STANCE} from '../external/yisim/card_info.js';
const digest='46046c3afa40788377a7bb7e98864ca8a8454da809b0493755acd411e07de6b0';
const installed=new WeakSet(),cache=new Map();
const check=(ok,why)=>{if(!ok)throw new Error('season_batch_unresolved:'+why);};
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const integer=(x,why)=>{check(Number.isSafeInteger(x)&&Math.abs(x)<=2147483647,why);return x;};
export function seasonBatchFacts(root){
 if(cache.has(root))return cache.get(root);
 const raw=fs.readFileSync(path.join(root,'data/inspection/season-batch-catalogue-v124.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'catalogue_changed');
 const facts=JSON.parse(raw);
 for(const [p,h] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,facts);return facts;
}
export function createSeasonBatch(root,game,swogi,value,order=[0,1]){
 if(value===undefined)return null;
 check(!installed.has(game),'duplicate_install');
 check(object(value)&&Object.keys(value).every(k=>['players','source_binding'].includes(k))&&Array.isArray(value.players)&&value.players.length===2,'explicit_two_players');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'order');
 const facts=structuredClone(seasonBatchFacts(root)),states=new Map(),events=[],openingBoundaries=new Set(),playBoundaries=new Set();
 for(const c of dreamBrushLoadFacts(root).cards){
  check(facts.raw_to_runtime[c.raw_id]===undefined&&!facts.runtime_cards[c.runtime_id],'duplicate_dream_identity');
  const raw=facts.raw_cards[c.raw_id];check(JSON.stringify(raw)===JSON.stringify(c.config),'dream_configuration_changed');
  facts.raw_to_runtime[c.raw_id]=c.runtime_id;
  facts.runtime_cards[c.runtime_id]=[{...raw,raw_id:c.raw_id,base_id:c.kind==='dream_brush'?341:10000083,upgrade_runtime:null}];
 }
 for(const c of websiteCardFacts(root).cards){
  check(facts.raw_to_runtime[c.raw_id]===undefined&&!facts.runtime_cards[c.runtime_id],'duplicate_website_identity');
  const raw=facts.raw_cards[c.raw_id];check(JSON.stringify(raw)===JSON.stringify(c.config),'website_configuration_changed');
  facts.raw_to_runtime[c.raw_id]=c.runtime_id;
  facts.runtime_cards[c.runtime_id]=[{...raw,raw_id:c.raw_id,base_id:c.base_id,upgrade_runtime:c.config.noUpgrade?null:c.runtime_id.slice(0,-1)+String(c.config.rarity+2)}];
 }
 for(const c of dreamFormationFacts(root).cards){
  check(facts.raw_to_runtime[c.raw_id]===undefined&&!facts.runtime_cards[c.runtime_id],'duplicate_dream_formation_identity');
  const raw=facts.raw_cards[c.raw_id];check(JSON.stringify(raw)===JSON.stringify(c.config),'dream_formation_config_changed');
  facts.raw_to_runtime[c.raw_id]=c.runtime_id;
  facts.runtime_cards[c.runtime_id]=[{...raw,raw_id:c.raw_id,base_id:c.base_id,upgrade_runtime:null}];
 }
 for(const [seat,p] of game.players.entries()){
  const input=value.players[order[seat]];
  check(object(input)&&Object.keys(input).every(k=>['ids','switches','grids','permanent','effective','vase','raw_cards'].includes(k)),'player_fields');
  check(Array.isArray(input.ids)&&new Set(input.ids).size===input.ids.length&&input.ids.every(id=>facts.pending_ids.includes(id)),'unique_ownership');
  for(const k of ['switches','grids','permanent','effective'])check(input[k]===undefined||object(input[k]),'invalid_'+k);
  check(Array.isArray(input.raw_cards)&&input.raw_cards.length===p.cards.length&&input.raw_cards.every((raw,i)=>Number.isInteger(raw)&&facts.raw_to_runtime[raw]===p.cards[i]),'explicit_raw_card_identities');
  states.set(p,{index:order[seat],input,rawCards:[...input.raw_cards],ids:new Set(input.ids),opened:new Set(),used:new Set(),counters:new Map(),turn:0,physiqueQi:false,reactivated:false,pendingGuard:0,waterExtra:0,firstStrike:true});
 }
 const state=p=>{const s=states.get(p);check(s,'player_identity');return s;};
 const has=(p,id)=>state(p).ids.has(id);
 const param=(id,index=0)=>integer(facts.strategies[id]?.otherParams[index],'parameter:'+id+':'+index);
 const enabled=(p,id)=>{const v=state(p).input.switches?.[id];check(typeof v==='boolean','explicit_switch:'+id);return v;};
 const effective=(p,id)=>{
  const cfg=facts.strategies[id];check(cfg,'strategy:'+id);
  return p.round_number>=cfg.effectRound;
 };
 const emit=(p,id,phase,extra={})=>events.push({player_index:state(p).index,strategy_id:id,phase,...extra});
 const card=(id,keys=['name','desc','sect','career','level','rarity','hidden','noUpgrade','anima','hpCost','base_id','upgrade_runtime'],identity)=>{
  let rows=facts.runtime_cards[id];check(rows?.length&&typeof swogi[id]?.card_actions==='function','unknown_card:'+id);
  if(rows.length>1&&keys.some(key=>rows.some(c=>JSON.stringify(c[key])!==JSON.stringify(rows[0][key])))){
   const p=identity?.player??game.players[0],slot=identity?.slot??p.currently_triggering_card_idx;
   check(Number.isInteger(slot)&&p.cards[slot]===id&&(identity||p.trigger_depth<=1),'ambiguous_temporary_identity:'+id);
   const raw=state(p).rawCards[slot];rows=rows.filter(c=>c.raw_id===raw);
   check(rows.length===1,'raw_identity_not_preserved:'+id);
  }
  const result={};for(const key of keys){check(rows.every(c=>JSON.stringify(c[key])===JSON.stringify(rows[0][key])),'ambiguous_card:'+id+':'+key);result[key]=rows[0][key];}return result;
 };
 const actualSlot=(p,id)=>{
  if(p.trigger_depth>1){const v=game.currentSeasonTemporaryGrid?.(p,id);check(Number.isInteger(v)&&v>=0&&v<p.cards.length,'temporary_card_grid:'+id);return v;}
  const v=p.currently_triggering_card_idx;check(Number.isInteger(v)&&v>=0&&v<p.cards.length,'actual_card_grid');return v;
 };
 const add=(idx,field,n)=>game.increase_idx_x_by_c(idx,field,integer(n,'buff_amount'));
 const counter=(p,id)=>state(p).counters.get(id)??0;
 const setCounter=(p,id,n)=>state(p).counters.set(id,integer(n,'counter:'+id));
 const consume=(p,id)=>{const n=counter(p,id);if(n<=0)return false;setCounter(p,id,n-1);return true;};
 const raiseHp=(idx,n)=>{game.increase_idx_max_hp(idx,n);game.increase_idx_hp(idx,n);};
 const replace=(p,slot,raw)=>{const id=facts.raw_to_runtime[raw];check(typeof id==='string'&&typeof swogi[id]?.card_actions==='function','replacement_not_executable:'+raw);p.cards[slot]=id;state(p).rawCards[slot]=raw;};
 const upgrade=(p,slot)=>{const c=card(p.cards[slot],['raw_id','noUpgrade','upgrade_runtime'],{player:p,slot});if(c.noUpgrade)return false;check(c.upgrade_runtime&&typeof swogi[c.upgrade_runtime]?.card_actions==='function','upgrade_not_executable:'+p.cards[slot]);replace(p,slot,c.raw_id+10000);return true;};
 const upgradeFirst=(p,predicate)=>{for(let i=0;i<p.cards.length;i++){const c=card(p.cards[i],undefined,{player:p,slot:i});if(predicate(c)&&!c.noUpgrade){upgrade(p,i);return i;}}return null;};
 const elements=['wood','fire','earth','metal','water'];
 const elementNames=['木灵','火灵','土灵','金灵','水灵'];
 const activate=(idx,element)=>game.increase_idx_activate(idx,'activate_'+element+'_spirit_stacks',1);
 const deckElements=p=>{
  const found=new Set();for(const id of p.cards){const c=card(id,['name']);elementNames.forEach((n,i)=>{if(c.name.includes(n))found.add(elements[i]);});}
  if(has(p,7085)){
   const vase=state(p).input.vase;check(Array.isArray(vase)&&[0,3].includes(vase.length),'explicit_vase_for7085');
   for(const raw of vase){check(Number.isSafeInteger(raw)&&facts.raw_cards[raw],'vase_raw_identity');const c=facts.raw_cards[raw];elementNames.forEach((n,i)=>{if(c.name.includes(n))found.add(elements[i]);});}
  }
  return found;
 };
 const deckElementCount=(p,forMarrow=false)=>{
  let extra292=0,extraTransmutation=0;
  for(const [slot,id] of p.cards.entries()){const c=card(id,['base_id','otherParams'],{player:p,slot});if(c.base_id===292)extra292=c.otherParams[1];if(c.base_id===7000101)extraTransmutation+=c.otherParams[0];}
  // Talent278 is admitted through the existing five-elements-anima field.
  const five=p.five_elements_anima_stacks>0;
  if(five&&forMarrow)return 1;
  return (five?5:deckElements(p).size)+extraTransmutation+Math.max(0,extra292);
 };
 const permanent=(p,id)=>{const m=state(p).input.permanent;check(object(m),'complete_permanent_map_required:'+id);return Object.hasOwn(m,id)?integer(m[id],'permanent:'+id):0;};
 const opening=(p,id)=>{
  if(!has(p,id))return;const s=state(p);check(!s.opened.has(id),'opening_repeated:'+id);s.opened.add(id);
  switch(id){
   case 1004:if(enabled(p,id)){game.increase_idx_debuff(0,'internal_injury',param(id));game.increase_idx_debuff(1,'internal_injury',param(id));}break;
   case 1008:if(enabled(p,id)){add(0,'apparition_confusion_stacks',param(id));add(1,'apparition_confusion_stacks',param(id));}break;
   case 7017:setCounter(p,741,param(id));break;
   case 7021:if(p.cards.length>=8){const c=card(p.cards[7],['base_id','noUpgrade'],{player:p,slot:7});if(c.base_id===11&&!c.noUpgrade)upgrade(p,7);else if(c.base_id===0)replace(p,7,11);}break;
   case 7024:{const n=permanent(p,'10037');if(n>0)game.increase_idx_hexagram(0,n);break;}
   case 7031:if(enabled(p,id))setCounter(p,742,1);break;
   case 7036:if(enabled(p,id))add(0,'hexproof',param(id));game.increase_idx_hp(0,param(id,1));break;
   case 7058:upgradeFirst(p,c=>c.name.includes('木灵'));break;
   case 7063:setCounter(game.players[1],753,counter(game.players[1],753)+param(id));break;
   case 7066:activate(0,'wood');game.increase_idx_qi(0,param(id));break;
   case 7067:add(0,'sword_qi',param(id));break;
   case 7077:setCounter(p,764,param(id));break;
   case 7078:game.increase_idx_star_power(0,1);if(p.cultivation>=game.players[1].cultivation+param(id))game.increase_idx_star_power(0,1);break;
   case 7083:raiseHp(0,param(id)*deckElementCount(p));break;
   case 7087:setCounter(p,769,param(id));break;
   case 7091:setCounter(p,771,param(id));break;
   case 7093:setCounter(p,772,param(id));break;
   case 7094:if(enabled(p,id)){add(0,'increase_atk',param(id));game.increase_idx_debuff(0,'internal_injury',param(id,1));}break;
   case 7095:activate(0,'earth');game.increase_idx_def(0,param(id));break;
   case 7096:activate(0,'metal');game.increase_idx_penetrate(0,param(id));break;
   case 7098:activate(0,'fire');game.reduce_idx_hp(1,param(id));game.reduce_idx_max_hp(1,param(id));break;
   case 7099:if(effective(p,id))setCounter(p,768,param(id));break;
   case 7100:if(effective(p,id))upgradeFirst(p,c=>c.name.includes('火灵'));break;
   case 7104:setCounter(p,770,1);break;
   case 23066:activate(0,'wood');break;
   case 7122:upgradeFirst(p,c=>c.name.includes('水灵'));break;
   case 7123:if(p.destiny<=param(id))raiseHp(0,Math.trunc(p.hp*param(id,1)/100));break;
   case 7127:setCounter(p,574,1);break;
   case 7128:upgradeFirst(p,c=>c.name.includes('星弈')||c.name.includes('卦'));break;
   case 7129:upgradeFirst(p,c=>c.desc.includes('灵气')||c.desc.includes('卦象'));break;
   case 7136:add(0,'unrestrained_sword_count',1);break;
   case 11003:setCounter(p,792,1);break;
   case 11004:game.increase_idx_physique(0,param(id,2));break;
   default:check(false,'unknown_opening:'+id);
  }
  emit(p,id,'season_opening');
 };
 const play=(id,cardId)=>{
  const p=game.players[0],s=state(p);if(!has(p,id))return;
  const c=card(cardId);let triggered=false;
  switch(id){
   case 7010:if(game.is_cloud_sword(cardId)){add(0,'cloud_sea',1);triggered=true;}break;
   case 7017:if(counter(p,741)>0&&game.is_sword_formation(cardId)){consume(p,741);game.increase_idx_def(0,param(id,1));add(0,'guard_up',param(id,2));triggered=true;}break;
   case 7022:if(actualSlot(p,cardId)===7){game.increase_idx_debuff(1,'internal_injury',param(id));triggered=true;}break;
   case 7026:if(c.name.includes('金灵')){game.increase_idx_qi(0,param(id));triggered=true;}if(c.name.includes('水灵')){game.increase_idx_penetrate(0,param(id,1));triggered=true;}break;
   case 7052:if(game.is_unrestrained_sword(cardId)){game.increase_idx_qi(0,1);triggered=true;}break;
   case 7037:if(c.hpCost>0){const n=Math.trunc(c.hpCost*param(id)/100);if(n>0)game.deal_damage(n);triggered=true;}break;
   case 7057:if(c.name.includes('卦')&&!p.can_post_action[actualSlot(p,cardId)]){game.increase_idx_debuff(1,'weaken',1);triggered=true;}break;
   case 7060:if(c.base_id===381){game.increase_idx_qi(0,1);triggered=true;}break;
   case 7097:if(effective(p,id)&&c.name.includes('土灵')){game.increase_idx_penetrate(0,param(id));triggered=true;}break;
   case 7130:if(c.base_id===19){add(0,'cloud_sea',param(id));add(0,'cloud_sword_chain_count',param(id,1));p.cloud_sword_used_count+=param(id,1);triggered=true;}break;
   case 23045:if(c.base_id===19){game.increase_idx_qi(0,param(id));triggered=true;}break;
   case 23079:if(effective(p,id)&&c.base_id===22){add(0,'guard_up',param(id));s.pendingGuard+=param(id);triggered=true;}break;
   default:check(false,'unknown_play_boundary:'+id);
  }
  if(triggered)emit(p,id,'season_before_body',{card:cardId});
 };
 game.currentSeasonBatchHas=has;
 game.currentSeasonBatchState=state;
 game.currentSeasonBatchCard=card;
 game.currentSeasonBatchCounter=counter;
 game.currentSeasonBatchConsume=consume;
 game.currentSeasonBatchSetCounter=setCounter;
 game.currentSeasonBatchEnabled=enabled;
 game.currentSeasonBatchEffective=effective;
 game.currentSeasonBatchSlot=actualSlot;
 game.currentSeasonBatchDeckElements=deckElements;
 game.currentSeasonBatchEmit=emit;
 const api={facts,has,state,param,enabled,effective,card,actualSlot,add,counter,setCounter,consume,raiseHp,replace,upgrade,deckElements,deckElementCount,activate,emit,
  installOpening(ids){
   for(const id of [...ids].reverse()){
    check(!openingBoundaries.has(id),'duplicate_opening_hook:'+id);openingBoundaries.add(id);
    const before=game.do_plant_start_permanent_buffs.bind(game);
    game.do_plant_start_permanent_buffs=function(...args){opening(this.players[0],id);return before(...args);};
   }
  },
  installPlay(ids){
   for(const id of [...ids].reverse()){
    check(!playBoundaries.has(id),'duplicate_play_hook:'+id);playBoundaries.add(id);
    const before=game.do_cloud_sword_softheart_and_friends.bind(game);
    game.do_cloud_sword_softheart_and_friends=function(cardId){play(id,cardId);return before(cardId);};
   }
  },
  metadata:()=>({schema:'season-battle-batch-candidate-v124',catalogue_sha256:digest,events:structuredClone(events),training_label_allowed:false})
 };
 installed.add(game);return api;
}
