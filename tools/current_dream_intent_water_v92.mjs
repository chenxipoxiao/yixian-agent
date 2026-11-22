import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='ddab310cc13e925d219c7efa52c812170ba86a36077e867b2fa2aa6cd0d3ac49',cache=new Map(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('dream_intent_water_unresolved:'+why);};
export function dreamIntentWaterFacts(root){
 if(cache.has(root))return cache.get(root);
 const b=fs.readFileSync(path.join(root,'data/inspection/current-dream-intent-water-v92.json'));
 check(crypto.createHash('sha256').update(b).digest('hex')===digest,'evidence_changed');const f=JSON.parse(b);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,f);return f;
}
export function registerDreamIntentWater(root,swogi){
 for(const c of dreamIntentWaterFacts(root).cards){
  check(!Object.hasOwn(swogi,c.runtime_id),'alias_collision');
  const flags=Object.fromEntries(Object.keys(swogi['601011']).filter(k=>k.startsWith('is_')).map(k=>[k,false]));
  swogi[c.runtime_id]=Object.freeze({...swogi['601011'],...flags,name:c.config.name,names:[c.config.name],
   marking:c.base_id===1000085?'sw':'fe',qi_cost:0,hp_cost:0,opening:undefined,
   is_water_spirit:c.base_id===7000103,card_actions:g=>g.executeCurrentDreamIntentWater(c.runtime_id)});
 }
}
const snap=p=>Object.fromEntries(['hp','max_hp','qi','def','force_of_water','sword_intent','increase_atk','next_attack_double_sword_intent_and_increase_atk','this_card_chases','damage_dealt_to_hp_by_this_card_atk'].map(k=>[k,p[k]]));
export function installDreamIntentWater(root,game,swogi,order=[0,1]){
 check(!installed.has(game),'already_installed');check(order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 const f=dreamIntentWaterFacts(root),cards=new Map(f.cards.map(c=>[c.runtime_id,c])),seats=new Map(game.players.map((p,i)=>[p,order[i]])),events=[];
 game.executeCurrentDreamIntentWater=function(id){
  const c=cards.get(id),p=this.players[0],q=this.players[1];check(c&&p.currently_triggering_card_id===id&&swogi[id],'card_identity');
  const e={kind:'card_body',player_index:seats.get(p),raw_card_id:c.raw_id,runtime_id:id,trigger_depth:p.trigger_depth,before:snap(p),target_before:snap(q)};events.push(e);
  if(c.base_id===1000085){
   if(c.config.jianYi>0)this.increase_idx_x_by_c(0,'sword_intent',c.config.jianYi);

  }else{
   check(Number.isSafeInteger(p.qi)&&Number.isSafeInteger(p.force_of_water),'invalid_water_state');
   e.base_attack=c.config.attack+p.qi+p.force_of_water;check(Number.isSafeInteger(e.base_attack)&&e.base_attack>=0&&e.base_attack<=2147483647,'attack_overflow');
   this.atk(e.base_attack);
   const n=p.damage_dealt_to_hp_by_this_card_atk;check(Number.isSafeInteger(n)&&n>=0,'invalid_hit_counter302');
   e.hit_counter302=n;e.recovery=0;

  }
  e.after=snap(p);e.target_after=snap(q);
 };
 installed.add(game);return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),recorded_action_log:false,training_label_allowed:false}:null};
}
