import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='4658b948e50da28a160caf9328a783c00f6b4121d56719ff4389091301ef5335',cache=new Map(),registered=new WeakSet(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('diligent_v90_unresolved:'+why);};
export function diligentFacts(root){
 if(cache.has(root))return cache.get(root);
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-diligent-chasewind-v90.json'));
 check(crypto.createHash('sha256').update(bytes).digest('hex')===digest,'evidence_changed');
 const f=JSON.parse(bytes);
 for(const [name,h] of Object.entries(f.source_sha256))
  check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,name))).digest('hex')===h,'source_changed:'+name);
 cache.set(root,f);return f;
}
export function registerDiligentChaseWind(root,swogi){
 check(!registered.has(swogi),'already_registered');
 for(const c of diligentFacts(root).cards){
  const old=swogi[c.runtime_id];check(typeof old?.card_actions==='function','missing_native_card');
  swogi[c.runtime_id]={...old,card_actions:g=>{
   if(c.family==='chase_wind'){
    g.increase_idx_def(0,c.config.def);
    g.add_c_of_x(c.config.otherParams[0],'cloud_sea');
    const extra=c.config.otherParams[1]-1;
    g.add_c_of_x(extra,'cloud_sword_chain_count');
    g.add_c_of_x(extra,'cloud_sword_used_count');
    g.chase();
   }else{
    check(typeof g.current_diligent_gain==='function','runtime_missing');
    for(let n=0;n<c.config.attackCount;n++)g.atk(c.config.attack);
    const p=g.players[0];check(Number.isSafeInteger(p.cultivation),'explicit_cultivation_required');
    g.current_diligent_gain(c,p.cultivation>=c.config.otherParams[1]?c.config.otherParams[2]:c.config.otherParams[0]);
   }
  }};
 }
 registered.add(swogi);
}
export function installDiligent(root,game,swogi,order=[0,1]){
 check(!installed.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(x=>x===0||x===1),'invalid_order');
 const facts=diligentFacts(root),events=[],seats=new Map(game.players.map((p,i)=>[p,order[i]]));
 // This field is not an accepted input. Fresh battle591 is absent; only the
 // card body below creates it. Existing runtime starts must never be erased.
 for(const p of game.players){check(!Object.hasOwn(p,'m_diligent_sword_stacks'),'unexpected_existing591');p.m_diligent_sword_stacks=0;}
 const integer=n=>Number.isSafeInteger(n)&&n>=0&&n<=2147483647;
 game.current_diligent_gain=function(c,amount){
  const p=this.players[0],before=p.m_diligent_sword_stacks;
  check(integer(before)&&integer(amount)&&integer(before+amount),'invalid591_gain');
  this.add_c_of_x(amount,'m_diligent_sword_stacks');
  events.push({kind:'body_gain591',player_index:seats.get(p),raw_id:c.raw_id,amount,before,after:p.m_diligent_sword_stacks});
 };
 const brush=game.do_flying_brush_chase.bind(game);
 game.do_flying_brush_chase=function(){
  const p=this.players[0],count=p.m_diligent_sword_stacks;
  check(integer(count),'nonfinite591');
  if(count===0)return brush();
  const id=p.currently_triggering_card_id,c=facts.runtime_classification[id];
  check(c!==undefined&&typeof swogi[id]?.card_actions==='function','unknown_current_card:'+id);
  const ultimate=p.quench_of_sword_heart_ultimate_stacks>0;
  if(ultimate&&c.raw_ids.includes(19))check(c.raw_ids.every(x=>x===19),'ambiguous_exact_raw19');
  const excluded=c.raw_ids.includes(19)&&ultimate;
  if(c.name_contains_sword&&!excluded&&p.this_card_chases<=0&&p.chases<p.max_chases){
   this.reduce_idx_x_by_c(0,'m_diligent_sword_stacks',1);
   this.chase();
   events.push({kind:'before_card_consume591_add315',player_index:seats.get(p),runtime_id:id,
    slot:p.currently_triggering_card_idx,depth:p.trigger_depth,before:count,after:p.m_diligent_sword_stacks,
    chases:p.chases,max_chases:p.max_chases});
   // Client681 is immediately next and sees positive315, so it cannot consume
   // a FlyingBrush charge supplied for a later card.
   return;
  }
  // While591 is pending, preserve681's adjacent guards even when591 itself
  // was ineligible (non-sword, pre-existing315, or exhausted turn capacity).
  if(p.this_card_chases>0||p.chases>=p.max_chases)return;
  return brush();
 };
 installed.add(game);
 return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),training_label_allowed:false}:null};
}
