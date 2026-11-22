import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='a89b7b0c1d0c561a6fbaebb6e0632280dce7858176db0aadeaa3abfa648fbd2b',cache=new Map(),registered=new WeakSet(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('cloud_shadow_unresolved:'+why);};
export function cloudShadowFacts(root){
 if(cache.has(root))return cache.get(root);
 const b=fs.readFileSync(path.join(root,'data/inspection/current-cloud-shadow-v99.json'));
 check(crypto.createHash('sha256').update(b).digest('hex')===digest,'evidence_changed');const f=JSON.parse(b);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,f);return f;
}
export function registerCloudShadow(root,swogi){
 check(!registered.has(swogi),'already_registered');
 for(const c of cloudShadowFacts(root).cards){
  check(!Object.hasOwn(swogi,c.runtime_id),'alias_collision');
  const flags=Object.fromEntries(Object.keys(swogi['601011']).filter(k=>k.startsWith('is_')).map(k=>[k,false]));
  swogi[c.runtime_id]=Object.freeze({...swogi['601011'],...flags,name:c.config.name,names:[c.config.name],marking:'sw',
   qi_cost:1,hp_cost:0,is_sword:true,is_cloud_sword:true,cloud_hit_cost_0_qi:true,
   card_actions:g=>g.executeCurrentCloudShadow(c.runtime_id)});
 }
 registered.add(swogi);
}
const snap=p=>({hp:p.hp,qi:p.qi,increase_atk:p.increase_atk,this_card_chases:p.this_card_chases,turn_chases:p.chases,cloud_chain:p.cloud_sword_chain_count});
export function installCloudShadow(root,game,swogi,order=[0,1]){
 check(!installed.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 const cards=new Map(cloudShadowFacts(root).cards.map(c=>[c.runtime_id,c])),states=new Map(game.players.map((p,i)=>[p,{index:order[i],successful:0}])),events=[];
 // The scheduler's p.chases resets every turn.738 is a distinct battle counter.
 // Install last so all accepted-chase effects precede this increment.
 const process=game.process_this_card_chases.bind(game);
 game.process_this_card_chases=function(...args){
  const p=this.players[0],s=states.get(p),before=p.chases,result=process(...args),delta=p.chases-before;
  check(delta===0||delta===1,'unexpected_chase_counter_delta');
  if(delta===1){s.successful++;check(Number.isSafeInteger(s.successful)&&s.successful<=2147483647,'738_overflow');}
  return result;
 };
 game.executeCurrentCloudShadow=function(id){
  const c=cards.get(id),p=this.players[0],s=states.get(p);
  check(c&&p.currently_triggering_card_id===id&&swogi[id],'card_identity');
  const e={kind:'card_body',raw_card_id:c.raw_id,player_index:s.index,slot:p.currently_triggering_card_idx,trigger_depth:p.trigger_depth,
   successful_chases_before:s.successful,before:snap(p)};events.push(e);
  for(let i=0;i<c.config.attackCount;i++)this.atk(c.config.attack);
  this.increase_idx_x_by_c(0,'increase_atk',c.config.otherParams[0]);
  e.requested_chase=s.successful>0;if(e.requested_chase)this.chase();e.after=snap(p);
 };
 installed.add(game);
 return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),successful_chases:[0,1].map(i=>states.get(game.players.find(p=>states.get(p).index===i)).successful),recorded_action_log:false,training_label_allowed:false}:null};
}
