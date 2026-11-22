import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='f326da01c1e395d0343c8e50a9434771263d3d5a353db9e945d3f57ce71b4e5f',cache=new Map(),registered=new WeakSet(),installed=new WeakSet();
const check=(v,m)=>{if(!v)throw new Error('nethermind_unresolved:'+m);};
export function nethermindFacts(root){
 if(cache.has(root))return cache.get(root);
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-nethermind-turnstart-v118.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');const f=JSON.parse(raw);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,f);return f;
}
export function registerNethermind(root,swogi){
 check(!registered.has(swogi),'already_registered');
 for(const c of nethermindFacts(root).cards){
  check(!Object.hasOwn(swogi,c.runtime_id),'alias_collision');
  const flags=Object.fromEntries(Object.keys(swogi['644021']).filter(k=>k.startsWith('is_')).map(k=>[k,false]));
  swogi[c.runtime_id]=Object.freeze({...swogi['644021'],...flags,name:c.config.name,names:[c.config.name],marking:'dx',
   qi_cost:0,hp_cost:0,is_continuous:true,is_add_physique:true,opening:undefined,
   card_actions:g=>g.executeCurrentNethermind(c.runtime_id)});
 }
 registered.add(swogi);
}
const snap=p=>Object.fromEntries(['hp','max_hp','qi','physique','max_physique','agility','meditation_of_xuan_stacks','internal_injury','regen'].map(k=>[k,p[k]]));
export function installNethermind(root,game,swogi,order=[0,1]){
 check(!installed.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 const f=nethermindFacts(root),cards=new Map(f.cards.map(c=>[c.runtime_id,c]));
 const states=new Map(game.players.map((p,i)=>[p,{index:order[i],active:false}])),events=[];
 game.executeCurrentNethermind=function(id){
  const p=this.players[0],s=states.get(p),c=cards.get(id);
  check(c&&p.currently_triggering_card_id===id,'card_identity');
  const e={kind:'card_body',raw_card_id:c.raw_id,player_index:s.index,slot:p.currently_triggering_card_idx,trigger_depth:p.trigger_depth,before:snap(p)};events.push(e);
  this.increase_idx_physique(0,c.config.physique);
  this.increase_idx_x_by_c(0,'meditation_of_xuan_stacks',c.config.otherParams[0]);
  this.increase_idx_x_by_c(0,'agility',c.config.otherParams[1]);
  this.continuous();s.active=true;e.after=snap(p);
 };
 const start=game.do_meditation_of_xuan.bind(game);
 game.do_meditation_of_xuan=function(...args){
  const p=this.players[0],s=states.get(p);
  if(!s.active)return start(...args);
  const amount=p.meditation_of_xuan_stacks;
  check(Number.isSafeInteger(amount)&&amount>=0&&amount<=2147483647,'invalid391');
  if(amount===0)return;
  const e={kind:'391_turn_start',player_index:s.index,amount,before:snap(p)};events.push(e);
  // Client reads391 once before either callback, not again after adding100.
  this.increase_idx_x_by_c(0,'internal_injury',amount);
  this.increase_idx_x_by_c(0,'regen',amount);
  e.after=snap(p);
 };
 installed.add(game);
 return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),recorded_action_log:false,training_label_allowed:false}:null};
}
