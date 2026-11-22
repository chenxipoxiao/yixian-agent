import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='ec61192960ca5204a3bdbcd58d71d1d6921672c785167855925abd94e508aefd',cache=new Map(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('frenzy_mantis_unresolved:'+why);};
export function frenzyMantisFacts(root){
 if(cache.has(root))return cache.get(root);
 const b=fs.readFileSync(path.join(root,'data/inspection/current-frenzy-mantis-v69.json'));
 check(crypto.createHash('sha256').update(b).digest('hex')===digest,'evidence_changed');const f=JSON.parse(b);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,f);return f;
}
export function registerFrenzyMantis(root,swogi){
 for(const c of frenzyMantisFacts(root).cards){
  check(!Object.hasOwn(swogi,c.runtime_id),'alias_collision');
  const flags=Object.fromEntries(Object.keys(swogi['601011']).filter(k=>k.startsWith('is_')).map(k=>[k,false]));
  const cloud=c.base_id===401;
  swogi[c.runtime_id]=Object.freeze({...swogi['601011'],...flags,name:c.config.name,names:[c.config.name],
   marking:cloud?'sw':'he',qi_cost:0,hp_cost:0,opening:undefined,
   is_sword:cloud,is_cloud_sword:cloud,is_unrestrained_sword:cloud,is_post_action:!cloud,
   card_actions:g=>g.executeCurrentFrenzyMantis(c.runtime_id)});
 }
}
const snap=p=>({hp:p.hp,def:p.def,increase_atk:p.increase_atk,wound:p.wound,cloud:p.cloud_sword_chain_count,unrestrained:p.unrestrained_sword_count,chases:p.this_card_chases});
export function installFrenzyMantis(root,game,swogi,order=[0,1]){
 const f=frenzyMantisFacts(root),byId=new Map(f.cards.map(c=>[c.runtime_id,c]));
 check(!installed.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(x=>x===0||x===1),'invalid_order');
 const seats=new Map(game.players.map((p,i)=>[p,order[i]])),events=[],injury=new WeakMap();
 // Observe the existing wound-entry predicate, not HP loss. False per-hit resets
 // must not erase client303; card cleanup erases it, including nested cleanup.
 for(const p of game.players){
  let last=p.this_atk_injured;injury.set(p,false);
  Object.defineProperty(p,'this_atk_injured',{enumerable:true,configurable:true,get:()=>last,
   set:v=>{last=v;if(v===true)injury.set(p,true);}});
 }
 const trigger=game.trigger_card.bind(game);
 game.trigger_card=function(...args){const p=this.players[0];try{return trigger(...args);}finally{injury.set(p,false);}};
 game.currentHasCardInjury303=p=>{check(injury.has(p),"injury_player_identity");return injury.get(p);};
 game.executeCurrentFrenzyMantis=function(id){
  const c=byId.get(id);check(c!==undefined,'unknown_card');const p=this.players[0],q=this.players[1];
  check(p.currently_triggering_card_id===id,'card_identity');
  // Reference post-action uses the physical playing slot. A temporary CardItem
  // needs its own hadUsed identity and is deliberately not inferred from a slot.
  if(c.base_id===4000101)check(p.trigger_depth===1&&p.currently_playing_card_idx===p.currently_triggering_card_idx&&p.cards[p.currently_playing_card_idx]===id,'temporary_post_action_identity');
  const e={kind:'card_body',raw_card_id:c.raw_id,player_index:seats.get(p),slot:p.currently_triggering_card_idx,trigger_depth:p.trigger_depth,before:snap(p),target_before:snap(q)};
  events.push(e);
  for(let i=0;i<c.config.attackCount;i++)this.atk(c.config.attack);
  if(c.base_id===401){
   e.injured_card=injury.get(p);e.last_attack_injured=p.this_atk_injured;
   if(e.injured_card){this.increase_idx_debuff(1,'wound',c.config.otherParams[0]);this.chase();}
  }else{
   this.increase_idx_x_by_c(0,'increase_atk',c.config.otherParams[0]);
   e.first_use=!p.can_post_action[p.currently_playing_card_idx];
   e.post_action=this.if_post_action();
   if(e.post_action)for(let i=0;i<c.config.attackCount;i++)this.atk(c.config.attack);
  }
  e.after=snap(p);e.target_after=snap(q);
 };
 installed.add(game);
 return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),recorded_action_log:false,
  temporary_mantis_identity_supported:false,training_label_allowed:false}:null};
}
