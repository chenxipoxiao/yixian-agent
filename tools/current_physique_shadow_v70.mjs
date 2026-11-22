import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='4a6dfa6eb8c9e889f8a72d1ec38a6d954e51540790a67896ececc8d6075336b1',cache=new Map(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('physique_shadow_unresolved:'+why);};
export function physiqueShadowFacts(root){
 if(cache.has(root))return cache.get(root);
 const b=fs.readFileSync(path.join(root,'data/inspection/current-physique-shadow-v70.json'));
 check(crypto.createHash('sha256').update(b).digest('hex')===digest,'evidence_changed');const f=JSON.parse(b);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,f);return f;
}
const fields=['internal_injury','weaken','flaw','decrease_atk','entangle','wound','styx','indigestion'];
function positiveDebuffs(p){return fields.reduce((n,k)=>{check(Number.isSafeInteger(p[k]),'invalid_debuff:'+k);return n+Math.max(0,p[k]);},0);}
export function registerPhysiqueShadow(root,swogi){
 for(const c of physiqueShadowFacts(root).cards){
  check(!Object.hasOwn(swogi,c.runtime_id),'alias_collision');
  const flags=Object.fromEntries(Object.keys(swogi['601011']).filter(k=>k.startsWith('is_')).map(k=>[k,false]));
  swogi[c.runtime_id]=Object.freeze({...swogi['601011'],...flags,name:c.config.name,names:[c.config.name],marking:'dx',
   qi_cost:0,hp_cost:c.config.hpCost,opening:undefined,is_add_qi:c.config.anima>0,is_add_physique:c.config.physique>0,
   card_actions:g=>g.executeCurrentPhysiqueShadow(c.runtime_id)});
 }
}
const snap=p=>Object.fromEntries(['hp','max_hp','qi','physique','max_physique','increase_atk','agility',...fields].map(k=>[k,p[k]]));
export function installPhysiqueShadow(root,game,swogi,order=[0,1]){
 const f=physiqueShadowFacts(root),byId=new Map(f.cards.map(c=>[c.runtime_id,c]));
 check(!installed.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(x=>x===0||x===1),'invalid_order');
 const seats=new Map(game.players.map((p,i)=>[p,order[i]])),events=[],after=new WeakMap(game.players.map(p=>[p,false]));
 // Client382 exists throughout OnAfterExecuted, not just explicit atk(...,true).
 // Nested cleanup removes it; an outer value is not restored.
 const body=game.just_do_the_card_and_nothing_else.bind(game);
 game.just_do_the_card_and_nothing_else=function(card){const p=this.players[0];const value=body(card);after.set(p,true);return value;};
 const trigger=game.trigger_card.bind(game);
 game.trigger_card=function(...args){const p=this.players[0];try{return trigger(...args);}finally{after.set(p,false);}};
 game.current_shadow_adjacency_attack=function(p,idx){
  const n=p.cards.length,slot=p.currently_triggering_card_idx;
  if(after.get(p)||p.trigger_depth<1||!swogi[p.currently_triggering_card_id])return 0;
  check(Number.isInteger(slot)&&slot>=0&&slot<n,'physical_slot_required');
  check(p.card_play_direction===1||p.card_play_direction===-1,'direction_required');
  const next=(slot+p.card_play_direction+n)%n,c=byId.get(p.cards[next]);
  if(c?.base_id!==10000077||c.config.level<4)return 0;
  const count=positiveDebuffs(p),amount=Math.floor(count/f.shadow_passive_divisor);
  events.push({kind:'shadow_neighbor_attack',player_index:seats.get(p),slot,next_slot:next,neighbor_raw_id:c.raw_id,
   triggering_runtime_id:p.currently_triggering_card_id,trigger_depth:p.trigger_depth,debuff_layers:count,amount});
  return amount;
 };
 game.executeCurrentPhysiqueShadow=function(id){
  const c=byId.get(id);check(c!==undefined,'unknown_card');const p=this.players[0],q=this.players[1];
  check(p.currently_triggering_card_id===id,'card_identity');
  const e={kind:'card_body',raw_card_id:c.raw_id,player_index:seats.get(p),slot:p.currently_triggering_card_idx,trigger_depth:p.trigger_depth,before:snap(p),target_before:snap(q)};
  events.push(e);
  if(c.base_id===10000110){
   this.increase_idx_qi(0,c.config.anima);this.increase_idx_physique(0,c.config.physique);this.increase_idx_x_by_c(0,'increase_atk',c.config.otherParams[0]);
  }else if(c.base_id===10000070){
   this.increase_idx_physique(0,c.config.physique);this.increase_idx_hp(0,c.config.otherParams[0]);
   check(Number.isSafeInteger(p.physique)&&p.physique>=0,'invalid_physique');
   e.internal_injury=c.config.level<=3?c.config.otherParams[1]:Math.floor(p.physique/c.config.otherParams[1]);
   if(e.internal_injury>0){this.increase_idx_debuff(0,'internal_injury',e.internal_injury);this.increase_idx_debuff(1,'internal_injury',e.internal_injury);}
  }else{
   e.base_attack=c.config.attack+(c.config.level<=3&&positiveDebuffs(p)>0?1:0);
   for(let i=0;i<c.config.attackCount;i++)this.atk(e.base_attack);
   if(c.config.level>=4)this.increase_idx_x_by_c(0,'agility',c.config.otherParams[1]);
  }
  e.after=snap(p);e.target_after=snap(q);
 };
 installed.add(game);
 return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),recorded_action_log:false,training_label_allowed:false}:null};
}
