import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='0f3cc9eb6b4aa79ae97d79ca7396fe5f6330e86a3e14d3b72d6ae919f2f0d503',cache=new Map(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('cloud_defense_unresolved:'+why);};
export function cloudDefenseFacts(root){
 if(cache.has(root))return cache.get(root);
 const b=fs.readFileSync(path.join(root,'data/inspection/current-cloud-defense-v71.json'));
 check(crypto.createHash('sha256').update(b).digest('hex')===digest,'evidence_changed');const f=JSON.parse(b);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,f);return f;
}
export function registerCloudDefense(root,swogi){
 for(const c of cloudDefenseFacts(root).cards){
  check(!Object.hasOwn(swogi,c.runtime_id),'alias_collision');
  const flags=Object.fromEntries(Object.keys(swogi['601011']).filter(k=>k.startsWith('is_')).map(k=>[k,false]));
  swogi[c.runtime_id]=Object.freeze({...swogi['601011'],...flags,name:c.config.name,names:[c.config.name],marking:'sw',
   qi_cost:0,hp_cost:0,is_sword:true,is_cloud_sword:true,is_continuous:c.config.cardType===3,
   opening:c.base_id===1000086&&c.config.level>=4?['executeCurrentCloudDefenseOpening',c.runtime_id]:undefined,
   card_actions:g=>g.executeCurrentCloudDefense(c.runtime_id)});
 }
}
const snap=p=>({hp:p.hp,max_hp:p.max_hp,qi:p.qi,def:p.def,cloud_chain:p.cloud_sword_chain_count,
 cloud_used:p.cloud_sword_used_count,cloud_sea:p.cloud_sea,softheart:p.cloud_sword_softheart_stacks,watermoon:p.moon_water_sword_formation_stacks});
export function installCloudDefense(root,game,swogi,order=[0,1]){
 const f=cloudDefenseFacts(root),byId=new Map(f.cards.map(c=>[c.runtime_id,c]));
 check(!installed.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(x=>x===0||x===1),'invalid_order');
 const seats=new Map(game.players.map((p,i)=>[p,order[i]])),events=[];
 game.executeCurrentCloudDefenseOpening=function(id){
  const c=byId.get(id),p=this.players[0];
  check(c?.base_id===1000086&&c.config.level>=4,'invalid_opening');
  check(p.currently_triggering_card_id===id,'opening_card_identity');
  const e={kind:'opening',raw_card_id:c.raw_id,player_index:seats.get(p),slot:p.currently_triggering_card_idx,before:snap(p)};
  events.push(e);this.increase_idx_x_by_c(0,'cloud_sea',c.config.otherParams[1]);e.after=snap(p);
 };
 game.executeCurrentCloudDefense=function(id){
  const c=byId.get(id),p=this.players[0];check(c!==undefined,'unknown_card');
  check(p.currently_triggering_card_id===id,'card_identity');
  const e={kind:'card_body',raw_card_id:c.raw_id,player_index:seats.get(p),slot:p.currently_triggering_card_idx,trigger_depth:p.trigger_depth,before:snap(p)};events.push(e);
  if(c.base_id===1000096){
   this.increase_idx_max_hp(0,c.config.otherParams[0]);
   this.increase_idx_x_by_c(0,'cloud_sword_softheart_stacks',c.config.otherParams[1]);
   this.chase();this.continuous();
  }else if(c.base_id===1000078){
   this.increase_idx_def(0,c.config.def);this.increase_idx_x_by_c(0,'cloud_sea',c.config.otherParams[2]);
   const chain=p.cloud_sword_chain_count;check(Number.isSafeInteger(chain)&&chain>=0,'invalid_cloud_chain');
   if(c.config.level>=4)this.increase_idx_x_by_c(0,'moon_water_sword_formation_stacks',c.config.otherParams[1]);
   const count=c.config.level===5?p.cloud_sword_used_count:chain;
   check(Number.isSafeInteger(count)&&count>=0,'invalid_cloud_count');e.count_source=c.config.level===5?'720_cumulative':'304_chain';e.count=count;
   e.extra_def=count*c.config.otherParams[0];if(e.extra_def>0)this.increase_idx_def(0,e.extra_def);
  }else{
   check(Number.isSafeInteger(p.qi)&&p.qi>=0,'invalid_qi');
   // Admitted304 lifecycle is positive increments or full removal on chain break.
   // This is not if_cloud_hit(), whose independent exemptions are different.
   check(Number.isSafeInteger(p.cloud_sword_chain_count)&&p.cloud_sword_chain_count>=0,'invalid_cloud_chain');
   const linked=p.cloud_sword_chain_count>0;
   const extra=c.config.level<=3?Number(p.qi>0):p.qi>0&&c.config.otherParams[0]>0?Math.floor(p.qi/c.config.otherParams[linked?2:0]):0;
   e.linked=linked;e.extra_repeats=extra;e.repeats=c.config.attackCount+extra;e.qi_snapshot=p.qi;
   for(let i=0;i<e.repeats;i++)this.atk(c.config.attack);
  }
  e.after=snap(p);
 };
 installed.add(game);
 return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),recorded_action_log:false,training_label_allowed:false}:null};
}
