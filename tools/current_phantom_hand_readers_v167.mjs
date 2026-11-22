// Bounded, prebattle-private-hand diagnostics. The website does not expose the
// client's GetNextParam stream: selected targets remain explicitly inferred.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='85cb744f5e9d6257228bced4378314c16bdf4bfe7c74d3f6622beec3672e8d1b';
const checked=new Map(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('phantom_hand_v167:'+why);};
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const canonical=x=>Array.isArray(x)?'['+x.map(canonical).join(',')+']':object(x)?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}':JSON.stringify(x);
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
function factsAt(root){
 if(checked.has(root))return checked.get(root);
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-phantom-hand-readers-v167.json'));
 check(hash(bytes)===digest,'evidence_changed');const f=JSON.parse(bytes);
 for(const [p,h] of Object.entries(f.source_sha256))check(hash(fs.readFileSync(path.join(root,p)))===h,'source_changed:'+p);
 checked.set(root,f);return f;
}
export function registerPhantomReaders(root,swogi){
 for(const c of factsAt(root).cards){
  check(typeof swogi[c.runtime_id]?.card_actions==='function','missing_card:'+c.runtime_id);
  swogi[c.runtime_id]=Object.freeze({...swogi[c.runtime_id],card_actions:g=>{
   check(typeof g.current_phantom_body_v167==='function','handler_required');
   return g.current_phantom_body_v167(c.runtime_id);
  }});
 }
}
const snap=p=>({hp:p.hp,max_hp:p.max_hp,qi:p.qi,def:p.def,charges:p.m_sinking_qi_stacks,
 cloud_chain:p.cloud_sword_chain_count,trigger_depth:p.trigger_depth,card:p.currently_triggering_card_id,slot:p.currently_triggering_card_idx});
export function installPhantomReaders(root,game,swogi,input,order){
 check(!installed.has(game),'already_installed');
 const f=factsAt(root),byId=new Map(f.cards.map(c=>[c.runtime_id,c]));
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(v=>v===0||v===1),'order');
 const seats=new Map(game.players.map((p,i)=>[p,order[i]])),events=[];
 const context=input.phantom_hand_v167;let binding=null;
 if(context!==undefined){
  check(object(context)&&Object.keys(context).sort().join(',')==='case_id,evidence_sha256,hand,seat','context_shape');
  binding=f.bindings[context.case_id];check(binding&&context.evidence_sha256===digest,'registered_binding');
  check(context.seat===binding.seat&&canonical(context.hand)===canonical(binding.hand),'private_hand_changed');
  const plain=Object.fromEntries(Object.entries(input).filter(([k])=>k!=='phantom_hand_v167'));
  check(hash(canonical(plain))===binding.old_battle_sha256,'compiled_battle_changed');
  check(input.players[binding.seat].hand_count===binding.hand.length,'hand_count');
 }
 for(const p of game.players){
  if(p.cards.some(c=>c.startsWith('71405')))check(binding&&seats.get(p)===binding.seat,'explicit_bound_hand_required');
 }
 game.current_phantom_body_v167=function(id){
  const c=byId.get(id),p=this.players[0];
  check(c&&p.currently_triggering_card_id===id,'active_card_identity');
  const e={player_index:seats.get(p),raw_id:c.raw_id,slot:p.currently_triggering_card_idx,before:snap(p)};events.push(e);
  if(c.raw_id%10000===278){
   this.increase_idx_qi(0,c.config.anima);this.increase_idx_hp(0,c.config.otherParams[0]);
   this.increase_idx_x_by_c(0,'m_sinking_qi_stacks',c.config.otherParams[1]);
   e.kind='sinking_qi_body';e.charges_added=c.config.otherParams[1];e.after=snap(p);return;
  }
  check(binding&&seats.get(p)===binding.seat,'explicit_bound_hand_required');
  let selected=null;
  for(const raw of binding.hand){
   const m=f.hand_metadata[raw];check(m,'unaudited_hand_card');
   if(!m.eligible)continue;
   const grade=Math.min(m.rarity+1,c.config.otherParams[0]);
   selected=f.targets.find(t=>t.raw_id===binding.selected_family+(grade-1)*10000);
   check(selected&&typeof swogi[selected.runtime_id]?.card_actions==='function','target_body_required');
  }
  e.kind='spiritage_hand_body';e.selection_inferred_from_prebattle_hand=true;
  if(!selected){e.selected_raw_id=null;e.after=snap(p);return;}
  e.selected_raw_id=selected.raw_id;e.selected_runtime_id=selected.runtime_id;
  const idx=p.currently_triggering_card_idx,original=p.cards[idx];
  check(Number.isInteger(idx)&&idx>=0&&idx<p.cards.length&&original===id,'physical_slot_required');
  try{
   p.cards[idx]=selected.runtime_id;
   this.trigger_card(selected.runtime_id,idx);
   if(selected.config.actionAgain)this.chase();
   check(p.currently_triggering_card_id===id&&p.currently_triggering_card_idx===idx,'nested_identity_not_restored');
   e.after_nested=snap(p);
  }finally{p.cards[idx]=original;}
  if(selected.config.level<=4){
   const amount=c.config.attack+Math.floor(p.qi/c.config.otherParams[1]);
   check(Number.isSafeInteger(amount)&&amount>=0,'attack_amount');
   e.appended_base_attack=amount;
   for(let n=0;n<c.config.attackCount;n++)this.atk(amount);
  }
  e.after=snap(p);e.hand_mutated=false;
 };
 installed.add(game);
 return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),
  source_parameter_sequence_observed:false,hand_target_selection_inferred:events.some(e=>e.kind==='spiritage_hand_body'),
  policy_observation_allowed:false,counterfactual_reuse_allowed:false,training_label_allowed:false}:null};
}
