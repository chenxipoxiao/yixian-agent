import {vesselPhysiqueFacts} from './current_vessel_physique_v74.mjs';
import {cloudDefenseFacts} from './current_cloud_defense_v71.mjs';
import {physiqueShadowFacts} from './current_physique_shadow_v70.mjs';
import {frenzyMantisFacts} from './current_frenzy_mantis_v69.mjs';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='2d27273823be098c052cd474f84b24a1057d0a81ab7d847c3e675995c72aa5e3',cache=new Map(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('hexagram_thunder_unresolved:'+why);};
function factsAt(root){
 if(cache.has(root))return cache.get(root);
 const b=fs.readFileSync(path.join(root,'data/inspection/current-hexagram-thunder-v67.json'));
 check(crypto.createHash('sha256').update(b).digest('hex')===digest,'evidence_changed');const f=JSON.parse(b);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 for(const c of frenzyMantisFacts(root).cards){check(!Object.hasOwn(f.neighbor_is_thunder,c.runtime_id),'duplicate_neighbor');f.neighbor_is_thunder[c.runtime_id]=false;}
 for(const c of physiqueShadowFacts(root).cards){check(!Object.hasOwn(f.neighbor_is_thunder,c.runtime_id),'duplicate_neighbor');f.neighbor_is_thunder[c.runtime_id]=false;}
 for(const c of cloudDefenseFacts(root).cards){check(!Object.hasOwn(f.neighbor_is_thunder,c.runtime_id),'duplicate_neighbor');f.neighbor_is_thunder[c.runtime_id]=false;}
 for(const c of vesselPhysiqueFacts(root).cards){check(!Object.hasOwn(f.neighbor_is_thunder,c.runtime_id),'duplicate_neighbor');f.neighbor_is_thunder[c.runtime_id]=false;}
 cache.set(root,f);return f;
}
export function registerHexagramThunder(root,swogi){
 for(const c of factsAt(root).cards){
  check(!Object.hasOwn(swogi,c.runtime_id),'alias_collision');
  swogi[c.runtime_id]=Object.freeze({...swogi['601011'],name:c.config.name,names:[c.config.name],marking:'he',
   qi_cost:0,hp_cost:0,is_add_qi:c.base_id===4000108,opening:undefined,
   is_sword:false,is_spirit_sword:false,is_cloud_sword:false,is_unrestrained_sword:false,
   is_thunder:c.config.name.includes('雷'),is_spirit_seal_or_formation:false,
   is_continuous:c.config.cardType===3,is_consumption:false,
   card_actions:g=>g.executeCurrentHexagramThunder(c.runtime_id)});
 }
}
const snap=p=>({hp:p.hp,qi:p.qi,def:p.def,hexagram:p.hexagram,hexagram_uses:p.triggered_hexagram_count,immunity:p.hexproof,formation:p.hexagram_formacide_stacks});
export function installHexagramThunder(root,game,swogi,order=[0,1]){
 const f=factsAt(root),byId=new Map(f.cards.map(c=>[c.runtime_id,c]));
 if(!game.players.some(p=>p.cards.some(id=>byId.has(id))))return null;
 check(!installed.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(x=>x===0||x===1),'invalid_order');
 const seats=new Map(game.players.map((p,i)=>[p,order[i]])),events=[];
 const hex=game.increase_idx_hexagram.bind(game);
 game.increase_idx_hexagram=function(idx,n){
  const p=this.players[idx];
  if(!p.cards.some(id=>byId.get(id)?.base_id===4000100))return hex(idx,n);
  check(Number.isSafeInteger(n)&&n>=0,'invalid_hexagram_gain');
  check(Number.isSafeInteger(p.hexagram_formacide_stacks)&&p.hexagram_formacide_stacks>=0&&n*p.hexagram_formacide_stacks<=2147483647,'formation_product_overflow');
  if(n===0)return hex(idx,n);
  const e={kind:'hexagram_gain',player_index:seats.get(p),amount:n,formation:p.hexagram_formacide_stacks,before:snap(p),target_before:snap(this.players[1-idx])};
  events.push(e);const result=hex(idx,n);e.after=snap(p);e.target_after=snap(this.players[1-idx]);return result;
 };
 game.executeCurrentHexagramThunder=function(id){
  const c=byId.get(id);check(c!==undefined,'unknown_card');
  const p=this.players[0],q=this.players[1];
  check(p.currently_triggering_card_id===id,'card_identity');
  const e={kind:'card_body',raw_card_id:c.raw_id,player_index:seats.get(p),slot:p.currently_triggering_card_idx,before:snap(p),target_before:snap(q)};
  events.push(e);
  if(c.base_id===4000100){
   this.add_c_of_x(c.config.otherParams[0],'hexagram_formacide_stacks');this.continuous();this.chase();
  }else if(c.base_id===4000108){
   this.increase_idx_qi(0,c.config.anima);
   // Independent typed consumers: one magnitude, then one probability request.
   e.amount=this.rand_range(c.config.def,c.config.randomDef);
   const slot=p.currently_triggering_card_idx,n=p.cards.length;
   check(Number.isInteger(slot)&&slot>=0&&slot<n,'physical_slot_required');
   e.neighbor_slots=[(slot+n-1)%n,(slot+1)%n];e.neighbor_ids=e.neighbor_slots.map(i=>p.cards[i]);
   check(e.neighbor_ids.every(id=>Object.hasOwn(f.neighbor_is_thunder,id)),'unknown_neighbor_identity');
   e.as_attack=e.neighbor_ids.some(id=>f.neighbor_is_thunder[id]);
   // Physical circular neighbors include continuous/consumed cards; direction
   // reverses the labels but does not change this unordered pair.
   if(e.as_attack)this.atk(e.amount);else this.increase_idx_def(0,e.amount);
   e.chase_requested=this.if_c_pct(10);if(e.chase_requested)this.chase();
  }else{
   e.amount=this.rand_range(c.config.attack,c.config.randomAttack);this.atk(e.amount);
   e.extra_attack=this.if_c_pct(1);if(e.extra_attack)this.atk(c.config.otherParams[0]);
   this.increase_idx_x_by_c(0,'hexproof',c.config.otherParams[1]);
  }
  e.after=snap(p);e.target_after=snap(q);
 };
 installed.add(game);
 return {metadata:()=>({evidence_sha256:digest,events:structuredClone(events),recorded_action_log:false,
  random_outcomes_reconstructed:false,random_distribution_server_verified:false,training_label_allowed:false})};
}
