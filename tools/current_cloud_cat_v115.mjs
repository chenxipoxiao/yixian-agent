import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='fc540631d631c5be1fceb57ef36b5c1ed6b531cc7220f46b03a0227828625c59',cache=new Map(),registered=new WeakSet(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('cloud_cat_unresolved:'+why);};
export function cloudCatFacts(root){
 if(cache.has(root))return cache.get(root);
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-cloud-cat-v115.json'));
 check(crypto.createHash('sha256').update(bytes).digest('hex')===digest,'evidence_changed');
 const facts=JSON.parse(bytes);
 for(const [p,h] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,facts);return facts;
}
export function registerCloudCat(root,swogi){
 check(!registered.has(swogi),'already_registered');
 for(const c of cloudCatFacts(root).cards){
  check(!Object.hasOwn(swogi,c.runtime_id),'alias_collision');
  const flags=Object.fromEntries(Object.keys(swogi['601011']).filter(k=>k.startsWith('is_')).map(k=>[k,false]));
  swogi[c.runtime_id]=Object.freeze({...swogi['601011'],...flags,name:c.config.name,names:[c.config.name],marking:'sw',
   qi_cost:0,hp_cost:0,is_sword:true,is_cloud_sword:true,is_continuous:true,opening:undefined,
   card_actions:g=>g.executeCurrentCloudCat(c.runtime_id)});
 }
 registered.add(swogi);
}
const snap=p=>({hp:p.hp,max_hp:p.max_hp,qi:p.qi,def:p.def,sword_intent:p.sword_intent,increase_atk:p.increase_atk});
export function installCloudCat(root,game,swogi,order=[0,1]){
 check(!installed.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 const byId=new Map(cloudCatFacts(root).cards.map(c=>[c.runtime_id,c]));
 const states=new Map(game.players.map((p,i)=>[p,{index:order[i],stacks:0}])),events=[];
 game.executeCurrentCloudCat=function(id){
  const p=this.players[0],s=states.get(p),c=byId.get(id);
  check(c&&p.currently_triggering_card_id===id&&swogi[id],'card_identity');
  const e={kind:'card_body',raw_card_id:c.raw_id,player_index:s.index,slot:p.currently_triggering_card_idx,
   trigger_depth:p.trigger_depth,before:snap(p),stacks_before:s.stacks};events.push(e);
  const [health,stacks]=c.config.otherParams;
  if(health>0){this.increase_idx_max_hp(0,health);this.increase_idx_hp(0,health);}
  check(Number.isSafeInteger(s.stacks+stacks)&&s.stacks+stacks<=2147483647,'757_overflow');
  s.stacks+=stacks;this.continuous();e.after=snap(p);e.stacks_after=s.stacks;
 };
 // Client OnAfterExecuted0x57a: after446, before255, inside !isTempCard.
 //757 is independent of whether the triggering card directly attacked.
 const endless=game.do_cloud_sword_endless.bind(game);
 game.do_cloud_sword_endless=function(id){
  const p=this.players[0],s=states.get(p);
  // The frozen446 helper has a narrower direct-attack condition. Do not admit
  // that unresolved combination just because the new757 reader is understood.
  if(s.stacks>0&&p.cloud_sword_endless_stacks>0&&!p.this_card_directly_attacked&&this.is_cloud_sword(id))
   throw new Error('cloud_cat_unresolved:446_nonattacking_interaction');
  const result=endless(id);
  if(s.stacks>0&&p.trigger_depth===1&&this.is_cloud_sword(id)){
   const e={kind:'757_after_cloud',player_index:s.index,slot:p.currently_triggering_card_idx,
    runtime_id:id,base_attack:s.stacks,trigger_depth:p.trigger_depth,before:snap(p),opponent_before:snap(this.players[1])};
   events.push(e);this.atk(s.stacks,true);e.after=snap(p);e.opponent_after=snap(this.players[1]);
  }
  return result;
 };
 installed.add(game);
 return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),
  recorded_action_log:false,training_label_allowed:false}:null};
}
