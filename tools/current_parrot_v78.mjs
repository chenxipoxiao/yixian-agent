// Same physical grid, temporary identity, explicit supported copy targets.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='e5ea56d5f2aafcab6d9dba94e94ed7542e32a29e410b14648b1f646e9b641fd9',cache=new Map(),installed=new WeakSet();
const check=(v,m)=>{if(!v)throw new Error('parrot_unresolved:'+m);};
export function parrotFacts(root){
 if(cache.has(root))return cache.get(root);
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-parrot-v78.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');const f=JSON.parse(raw);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,f);return f;
}
export function registerParrot(root,swogi){
 for(const c of parrotFacts(root).cards){
  check(!Object.hasOwn(swogi,c.runtime_id),'alias_collision');
  const flags=Object.fromEntries(Object.keys(swogi['601011']).filter(k=>k.startsWith('is_')).map(k=>[k,false]));
  swogi[c.runtime_id]=Object.freeze({...swogi['601011'],...flags,name:c.config.name,names:[c.config.name],marking:'no_marking',
   qi_cost:0,hp_cost:0,opening:undefined,is_continuous:false,is_consumption:false,
   card_actions:g=>{check(typeof g.currentParrotEffect==='function','runtime_required');g.currentParrotEffect(c.runtime_id);}});
 }
}
export function installParrot(root,game,swogi,order=[0,1]){
 check(!installed.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(x=>x===0||x===1),'invalid_order');
 const f=parrotFacts(root),cards=new Map(f.cards.map(c=>[c.runtime_id,c])),targets=new Set(f.copy_targets.map(c=>c.runtime_id));
 const states=new Map(game.players.map((p,i)=>[p,{owner:order[i],guard9900008:0}])),events=[];
 game.currentParrotEffect=function(id){
  const p=this.players[0],q=this.players[1],s=states.get(p),c=cards.get(id),idx=p.currently_triggering_card_idx;
  check(c&&p.currently_triggering_card_id===id,'card_identity');
  check(Number.isInteger(idx)&&idx>=0&&idx<p.cards.length&&p.cards[idx]===id,'physical_grid_required');
  if(s.guard9900008>0){events.push({kind:'copy_loop_blocked',player_index:s.owner,slot:idx,raw_id:c.raw_id,healed:false});return;}
  const e={kind:'parrot_body',player_index:s.owner,slot:idx,raw_id:c.raw_id,trigger_depth:p.trigger_depth,hp_before:p.hp};events.push(e);
  s.guard9900008+=1;
  const original=p.cards[idx];
  try{
   this.increase_idx_hp(0,c.config.otherParams[0]);e.hp_after_heal=p.hp;
   if(idx>=q.cards.length){e.copy_target=null;return;}
   // GetBattleDeckIdList reads each live CardItem, including in-battle transforms.
   const target=q.cards[idx];
   check(targets.has(target)&&typeof swogi[target]?.card_actions==='function','copy_target_not_admitted:'+target);
   // RefreshSpecialCard has dynamic bodies only for19/126/13. None are admitted.
   // Temporary calls retain the real grid and do not repay costs or ordinary Execute.
   p.cards[idx]=target;e.copy_target=target;
   this.trigger_card(target,idx);
   const targetFact=f.copy_targets.find(c=>c.runtime_id===target);
   if(targetFact.action_again)this.chase();
  }finally{
   p.cards[idx]=original;s.guard9900008-=1;e.restored_runtime=p.cards[idx];e.guard_after=s.guard9900008;
  }
 };
 installed.add(game);
 return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),
  supported_copy_raw_ids:f.copy_targets.map(c=>c.raw_id),recorded_action_log:false,training_label_allowed:false}:null};
}
