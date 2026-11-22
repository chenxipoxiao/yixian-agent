import {dreamBasicsFacts} from './current_dream_basics_v93r2.mjs';
import {parrotFacts} from './current_parrot_v78.mjs';
import {elementArraysFacts} from './current_element_arrays_v75.mjs';
// Versioned ownership hooks. Existing nonowner battles keep the frozen path.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='e720472f3bfe293bcfaf61a37c83aae872d4a1f66adc0cf5ff98ed18268366a6';
const installed=new WeakSet();
const check=(v,m)=>{if(!v)throw new Error('season_passives_unresolved:'+m);};
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
export function createSeasonPassives(root,game,swogi,value,order=[0,1]) {
 if(value===undefined)return null;
 check(object(value)&&Object.keys(value).length===1&&Array.isArray(value.players)&&value.players.length===2,'explicit_players_required');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 check(value.players.every(a=>Array.isArray(a)&&new Set(a).size===a.length&&a.every(id=>[7035,7050,7132].includes(id))),'invalid_ownership');
 check(value.players.some(a=>a.length),'empty_ownership');check(!installed.has(game),'already_installed');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-season-passives-v55.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');const facts=JSON.parse(raw);
 for(const [p,h] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 const states=new Map(game.players.map((p,i)=>[p,{index:order[i],ids:new Set(value.players[order[i]])}])),events=[],boundaries=new Set();
 const emit=(p,id,phase,extra)=>events.push({player_index:states.get(p).index,strategy_id:id,phase,...extra});
 const has=(p,id)=>states.get(p).ids.has(id);
 for(const c of elementArraysFacts(root).cards){check(!Object.hasOwn(facts.runtime_classification,c.runtime_id),'duplicate_array');facts.runtime_classification[c.runtime_id]={cloud:false,formation:false};}
 for(const c of parrotFacts(root).cards){check(!Object.hasOwn(facts.runtime_classification,c.runtime_id),'duplicate_parrot');facts.runtime_classification[c.runtime_id]={cloud:false,formation:false};}
 const newIds=new Set(dreamBasicsFacts(root).cards.map(c=>c.runtime_id));
 const metadata=id=>{const c=facts.runtime_classification[id]??(newIds.has(id)?{cloud:false,formation:false}:null);check(c&&typeof swogi[id]?.card_actions==='function','unknown_card:'+id);return c;};
 const cloud=game.is_cloud_sword.bind(game),formation=game.is_sword_formation.bind(game);
 // Explicit static213/261 identities also work outside their original character.
 // Native learned-family and temporary classification is evaluated on the live
 // player, after transformations and within each repeated card execution.
 game.is_cloud_sword=function(id){
  const p=this.players[0];if(!has(p,7050)&&!has(p,7132))return cloud(id);
  return metadata(id).cloud||cloud(id);
 };
 game.is_sword_formation=function(id){
  if(!has(this.players[0],7132))return formation(id);
  return metadata(id).formation||formation(id);
 };
 const add=game.increase_idx_x_by_c.bind(game);
 game.increase_idx_x_by_c=function(idx,field,amount){
  const p=this.players[idx];
  if(field==='increase_atk'&&has(p,7035)){
   check(Number.isSafeInteger(amount)&&amount>=0,'invalid_attack_gain');
   if(amount>0){
    // Legacy fate148 is still rejected by compile_start, so this branch is the
    // sole member of the client OR. Native646 runs next in add().
    const before={increase_atk:p.increase_atk,wood_thorn:p.wood_thorn};
    add(idx,'wood_thorn',1);const out=add(idx,field,amount-1);
    emit(p,7035,'positive_attack_gain_before646',{requested:amount,before,after:{increase_atk:p.increase_atk,wood_thorn:p.wood_thorn}});return out;
   }
  }
  return add(idx,field,amount);
 };
 const chain=game.do_cloud_sword_chain_count.bind(game);
 game.do_cloud_sword_chain_count=function(id){
  const p=this.players[0];
  if(!has(p,7132)||this.is_cloud_sword(id)||p.cloud_sea<=0)return chain(id);
  // Current mode rejects legacy97/380 and unsupported7010. Their additional
  // rewards are not silently represented by this season7132-only branch.
  p.cloud_sword_chain_count++;p.cloud_sword_used_count++;p.cloud_sea--;
  const before=p.def;this.increase_idx_def(0,2);
  emit(p,7132,'cloud_sea_consumed_after_card',{card:id,cloud_sea:p.cloud_sea,chain:p.cloud_sword_chain_count,requested_def:2,def_before:before,def_after:p.def});
 };
 // Record actual reuse of the existing202 decay boundary, including zero def.
 const decay=game.do_def_decay.bind(game);
 game.do_def_decay=function(...args){
  const p=this.players[0],before=p.moon_water_sword_formation_stacks,def=p.def;
  const out=decay(...args);
  if(has(p,7050)&&before>0)emit(p,7050,'owner_turn_def_decay',{stacks_before:before,stacks_after:p.moon_water_sword_formation_stacks,def_before:def,def_after:p.def});
  return out;
 };
 installed.add(game);
 return {
  installBoundary(id){
   check([7050,7132].includes(id)&&!boundaries.has(id),'duplicate_or_unknown_boundary');boundaries.add(id);
   const previous=game.do_cloud_sword_softheart_and_friends.bind(game);
   game.do_cloud_sword_softheart_and_friends=function(card){
    const p=this.players[0];
    if(has(p,id)&&(id===7050?this.is_cloud_sword(card):this.is_sword_formation(card))){
     const field=id===7050?'moon_water_sword_formation_stacks':'cloud_sea',before=p[field];
     this.add_c_of_x(1,field);emit(p,id,'season_before_card_body',{card,trigger_depth:p.trigger_depth,field,before,after:p[field]});
    }
    return previous(card);
   };
  },
  metadata:()=>({evidence_sha256:digest,events:structuredClone(events),training_label_allowed:false})
 };
}
