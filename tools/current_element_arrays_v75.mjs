// Current array bodies. Shared attack and pre-card readers keep their frozen order.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {vesselPhysiqueFacts} from './current_vessel_physique_v74r2.mjs';
const digest='d74fa1b418c9ca1033da3b069fbc33aa4ababedf8157c707d33ccba1172a69ed',cache=new Map(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('element_arrays_unresolved:'+why);};
export function elementArraysFacts(root){
 if(cache.has(root))return cache.get(root);
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-element-arrays-v75.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');const f=JSON.parse(raw);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,f);return f;
}
export function registerElementArrays(root,swogi){
 for(const c of elementArraysFacts(root).cards){
  check(!Object.hasOwn(swogi,c.runtime_id),'alias_collision');
  const flags=Object.fromEntries(Object.keys(swogi['601011']).filter(k=>k.startsWith('is_')).map(k=>[k,false]));
  swogi[c.runtime_id]=Object.freeze({...swogi['601011'],...flags,name:c.config.name,names:[c.config.name],marking:'fe',qi_cost:0,hp_cost:0,opening:undefined,
   is_add_qi:c.config.anima>0,is_wood_spirit:c.base_id===7000081,is_water_spirit:c.base_id===7000104,
   is_spirit_seal_or_formation:true,is_continuous:true,is_consumption:false,
   card_actions:g=>g.executeCurrentElementArray(c.runtime_id)});
 }
}
export function usesNewArrayFlag(root,value){
 if(value===undefined)return false;
 const f=elementArraysFacts(root),ids=new Set(f.cards.map(c=>c.raw_id));
 return Array.isArray(value.hands)&&value.hands.some(h=>Array.isArray(h)&&ids.has(h.find(raw=>f.hand_metadata[raw]?.kind==='formation')));
}
const snap=p=>Object.fromEntries(['hp','max_hp','qi','activate_wood_spirit_stacks','water_spirit_formation_stacks','wood_thorn','convert_increase_atk_to_wood_thorn','dream_wood_spirit_formation_attack_steal_hp_stacks'].map(k=>[k,p[k]]));
export function installElementArrays(root,game,swogi,order=[0,1]){
 check(!installed.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(x=>x===0||x===1),'invalid_order');
 const f=elementArraysFacts(root),byId=new Map(f.cards.map(c=>[c.runtime_id,c])),seats=new Map(game.players.map((p,i)=>[p,order[i]])),events=[];
 game.executeCurrentElementArray=function(id){
  const c=byId.get(id),p=this.players[0];check(c&&p.currently_triggering_card_id===id,'card_identity');
  const e={kind:'card_body',raw_card_id:c.raw_id,player_index:seats.get(p),slot:p.currently_triggering_card_idx,trigger_depth:p.trigger_depth,before:snap(p)};events.push(e);
  if(c.base_id===7000104){
   this.increase_idx_qi(0,c.config.anima);
   this.increase_idx_x_by_c(0,'water_spirit_formation_stacks',c.config.otherParams[0]);
  }else{
   this.activate_wood_spirit();this.increase_idx_qi(0,c.config.anima);
   if(c.config.level<=4)this.increase_idx_x_by_c(0,'dream_wood_spirit_formation_attack_steal_hp_stacks',c.config.otherParams[0]);
   if(c.config.level>=4)this.increase_idx_x_by_c(0,'wood_thorn',c.config.otherParams[1]);
   if(c.config.level===5){
    this.increase_idx_max_hp(0,c.config.otherParams[2]);
    this.increase_idx_x_by_c(0,'convert_increase_atk_to_wood_thorn',c.config.otherParams[0]);
   }
  }
  // Native continuous() removes a physical card only at depth1. Flags trigger at depth2.
  this.continuous();if(c.config.actionAgain)this.chase();e.after=snap(p);
 };
 // The v74 table stays immutable. Only the newly registered identities use this extension.
 const pot=game.do_spirit_fusion_pot.bind(game),vessel=vesselPhysiqueFacts(root).vessel;
 game.do_spirit_fusion_pot=function(idx){
  const p=this.players[0],q=this.players[1],c=byId.get(p.cards[idx]);
  if(!c||!(p.spirit_fusion_pot_stacks>0))return pot(idx);
  check(Number.isInteger(idx)&&idx>=0&&idx<p.cards.length,'vessel_actual_slot_required');
  const next=c.config.rarity>=1?f.extra_transform_cards[c.raw_id].downgrade_raw_id:null;
  const target=next===null?null:f.extra_transform_cards[next]?.runtime_id;
  if(next!==null)check(typeof swogi[target]?.card_actions==='function','vessel_downgrade_target');
  const e={kind:'vessel_new_array',player_index:seats.get(p),slot:idx,raw_card_id:c.raw_id,before:[snap(p),snap(q)]};
  this.reduce_idx_x_by_c(0,'spirit_fusion_pot_stacks',1);
  if(target){p.cards[idx]=target;e.downgraded=true;}
  else{this.reduce_idx_hp(0,vessel.absorb);this.reduce_idx_max_hp(0,vessel.absorb);this.increase_idx_max_hp(1,vessel.absorb);this.increase_idx_hp(1,vessel.absorb);e.downgraded=false;}
  e.card_after=p.cards[idx];e.after=[snap(p),snap(q)];events.push(e);
 };
 installed.add(game);return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),recorded_action_log:false,training_label_allowed:false}:null};
}
