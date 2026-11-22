import {elementArraysFacts} from './current_element_arrays_v75.mjs';
// Ordered, non-consuming prebattle hands. A missing first target never becomes a later one.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='2be2802df323d4c925226bb94d8aecc4e05928be883fa8042311a8f05deba11f',cache=new Map(),installed=new WeakSet();
const fail=m=>{throw new Error('element_flag_unresolved:'+m);};
const check=(c,m)=>{if(!c)fail(m);};
function factsAt(root) {
 if(cache.has(root))return cache.get(root);
 const b=fs.readFileSync(path.join(root,'data/inspection/current-dream-fire-v63.json'));
 check(crypto.createHash('sha256').update(b).digest('hex')===digest,'evidence_changed');
 const f=JSON.parse(b);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 const extra=elementArraysFacts(root);for(const c of extra.cards){check(f.hand_metadata[c.raw_id]?.runtime_id===null,'array_flag_binding');f.hand_metadata[c.raw_id]=extra.hand_metadata[c.raw_id];}
 cache.set(root,f);return f;
}
export function registerElementFlag(root,swogi) {
 for(const c of factsAt(root).flag_cards) {
  check(!Object.hasOwn(swogi,c.runtime_id),'alias_collision');
  swogi[c.runtime_id]=Object.freeze({...swogi['601011'],name:c.config.name,names:[c.config.name],
   marking:'no_marking',qi_cost:0,hp_cost:0,opening:undefined,is_continuous:false,is_consumption:false,
   card_actions:g=>{check(typeof g.current_element_flag==='function','hand_context_required');g.current_element_flag(c.raw_id);}});
 }
}
export function installArrayFlag(root,game,swogi,value,order=[0,1]) {
 const facts=factsAt(root),flagIds=new Set(facts.flag_cards.map(c=>c.runtime_id));
 if(value===undefined){check(!game.players.some(p=>p.cards.some(c=>flagIds.has(c))),'hand_context_required');return null;}
 check(!installed.has(game),'already_installed');
 check(value&&Object.keys(value).length===1&&Array.isArray(value.hands)&&value.hands.length===2,'explicit_hands_required');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(v=>v===0||v===1),'invalid_order');
 const states=new WeakMap(),events=[];
 game.players.forEach((p,i)=>{
  const h=value.hands[order[i]];
  check(h===null||Array.isArray(h)&&h.length<=256&&h.length===p.hand_count&&h.every(c=>Number.isSafeInteger(c)&&Object.hasOwn(facts.hand_metadata,c)),'invalid_hand');
  check(h!==null||!p.cards.some(c=>flagIds.has(c)),'hand_context_required');
  states.set(p,{hand:h===null?null:[...h],owner:order[i]});
 });
 const selected=(s,kind,cap)=>{
  const source=s.hand.find(c=>facts.hand_metadata[c].kind===kind);
  if(source===undefined)return null;
  const m=facts.hand_metadata[source];let raw=source;
  // Dream grades are separate hidden, non-upgradeable cards; never convert them to ordinary formations.
  if(kind==='formation'&&!m.hidden&&m.rarity>=cap)raw-=10000*(m.rarity-cap+1);
  const target=facts.hand_metadata[raw];
  check(target?.kind===kind&&target.runtime_id&&typeof swogi[target.runtime_id]?.card_actions==='function','unmapped_first_'+kind+':'+raw);
  return {source_raw:source,raw,runtime_id:target.runtime_id};
 };
 game.current_element_flag=function(raw) {
  const me=this.players[0],s=states.get(me),c=facts.flag_cards.find(c=>c.raw_id===raw),idx=me.currently_triggering_card_idx;
  check(c&&me.currently_triggering_card_id===c.runtime_id,'card_identity');
  check(s?.hand!==null&&Array.isArray(s?.hand),'hand_context_required');
  check(me.trigger_depth===1&&idx===me.currently_playing_card_idx&&me.cards[idx]===c.runtime_id,'nested_slot_identity');
  const odd=idx%2===0,formation=selected(s,'formation',c.config.otherParams[0]),seal=odd?null:selected(s,'seal',null);
  const event={player_index:s.owner,raw_id:raw,slot:idx,odd,formation,seal,hp_before:me.hp,hand_mutated:false};
  if(formation){this.trigger_card(formation.runtime_id,idx);if(facts.hand_metadata[formation.raw].action_again)this.chase();}
  if(odd){this.reduce_idx_hp(0,c.config.otherParams[1]);this.chase();}
  else if(seal){this.trigger_card(seal.runtime_id,idx);if(facts.hand_metadata[seal.raw].action_again)this.chase();}
  event.hp_after=me.hp;event.restored_runtime=me.currently_triggering_card_id;event.flag_remains_playable=me.can_play[idx];events.push(event);
 };
 installed.add(game);
 return {metadata:()=>({evidence_sha256:digest,events:structuredClone(events),recorded_parameters_as_input:false,policy_observation:false,training_label_allowed:false})};
}
