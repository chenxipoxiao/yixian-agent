import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='86f5d71698bde147f85bcb519bfa8f3b7a992481537dbd72996cc9c900f89cb5',cache=new Map(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('wood_patrol_unresolved:'+why);};
export function woodPatrolFacts(root){
 if(cache.has(root))return cache.get(root);
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-mirror-card-consumers-v130.json'));
 check(crypto.createHash('sha256').update(bytes).digest('hex')===digest,'evidence_changed');
 const facts=JSON.parse(bytes);
 for(const [name,hash] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,name))).digest('hex')===hash,'source_changed:'+name);
 cache.set(root,facts);return facts;
}
export function registerWoodPatrol(root,swogi){
 for(const c of woodPatrolFacts(root).cards){
  check(!Object.hasOwn(swogi,c.runtime_id),'alias_collision');
  const flags=Object.fromEntries(Object.keys(swogi['601011']).filter(k=>k.startsWith('is_')).map(k=>[k,false]));
  swogi[c.runtime_id]=Object.freeze({...swogi['601011'],...flags,name:c.config.name,names:[c.config.name],
   marking:'fe',qi_cost:0,hp_cost:0,opening:undefined,is_wood_spirit:true,
   card_actions:game=>game.executeCurrentWoodPatrol(c.runtime_id)});
 }
}
const snap=p=>Object.fromEntries(['hp','max_hp','qi','def','hp_gained','wood_thorn','this_card_chases'].map(k=>[k,p[k]]));
export function installWoodPatrol(root,game,swogi,order=[0,1]){
 check(!installed.has(game),'already_installed');
 check(order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 const cards=new Map(woodPatrolFacts(root).cards.map(c=>[c.runtime_id,c]));
 const seats=new Map(game.players.map((p,i)=>[p,order[i]])),events=[];
 game.executeCurrentWoodPatrol=function(id){
  const c=cards.get(id),p=this.players[0],q=this.players[1];
  check(c&&p.currently_triggering_card_id===id&&swogi[id],'card_identity');
  const e={kind:'card_body',raw_card_id:c.raw_id,player_index:seats.get(p),slot:p.currently_triggering_card_idx,
   trigger_depth:p.trigger_depth,before:snap(p),target_before:snap(q)};
  events.push(e);
  this.increase_idx_x_by_c(0,'wood_thorn',c.config.otherParams[0]);
  for(let i=0;i<c.config.attackCount;i++)this.atk(c.config.attack);
  check(Number.isSafeInteger(p.hp_gained)&&p.hp_gained>=0,'invalid_counter313');
  e.counter313=p.hp_gained;e.wood_active=this.if_wood_spirit();
  e.action_again=e.wood_active&&p.hp_gained>=c.config.otherParams[0];
  if(e.action_again)this.chase();
  e.after=snap(p);e.target_after=snap(q);
 };
 installed.add(game);
 return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),recorded_action_log:false,training_label_allowed:false}:null};
}
