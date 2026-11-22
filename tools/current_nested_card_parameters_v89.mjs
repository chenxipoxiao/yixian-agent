// Original-record branch / card identities. No random pool or policy action.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='c0353b02499bd3b9d98f9436f98e36f20cfc72a69fcc681f8e9779a298bfbab8';
const installed=new WeakSet();
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const check=(ok,why)=>{if(!ok)throw new Error('nested_card_parameters_unresolved:'+why);};
const canonical=x=>Array.isArray(x)?'['+x.map(canonical).join(',')+']':object(x)?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}':JSON.stringify(x);
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const snap=p=>({hp:p.hp,max_hp:p.max_hp,qi:p.qi,def:p.def,guard_up:p.guard_up,hexagram:p.hexagram,
 unrestrained_sword_count:p.unrestrained_sword_count,played_card_count:p.played_card_count,
 twin_dragons:p.unrestrained_sword_twin_dragons_stacks,trigger_depth:p.trigger_depth,
 triggering_card:p.currently_triggering_card_id,triggering_slot:p.currently_triggering_card_idx});

export function createNestedCardQueue(swogi,game,stream,order,facts){
 check(!installed.has(game),'already_installed');
 check(Array.isArray(stream)&&stream.length>0&&stream.length<=256&&stream.every(x=>Number.isSafeInteger(x)&&x>=0&&x<=2147483647),'invalid_stream');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(x=>x===0||x===1),'invalid_order');
 const values=[...stream],cards=new Map(facts.cards.map(c=>[swogi[c.runtime_id],c]));
 check(!cards.has(undefined),'missing_card_identity');
 const targets=new Map(facts.selected_targets.map(c=>[c.raw_id,c]));
 for(const c of targets.values())check(typeof swogi[c.runtime_id]?.card_actions==='function','missing_target_body');
 const seats=new Map(game.players.map((p,i)=>[p,order[i]])),events=[];let cursor=0;
 const noOther=()=>check(!game.used_randomness,'other_random_consumer');
 const take=(c,p,type)=>{
  noOther();check(cursor<values.length,'parameter_underflow:'+c.kind);
  const value=values[cursor];
  if(type==='effect_branch')check(value>=0&&value<=2,'invalid_falling_paper_branch');
  else check(targets.has(value),'selected_card_not_admitted:'+value);
  const e={kind:c.kind,type,raw_card_id:c.id,runtime_card_id:c.runtime_id,player_index:seats.get(p),
    slot:p.currently_triggering_card_idx,queue_index:cursor++,value,before:snap(p)};
  events.push(e);return e;
 };
 const body=game.just_do_the_card_and_nothing_else.bind(game);
 game.just_do_the_card_and_nothing_else=function(card){
  const c=cards.get(card);if(!c)return body(card);
  const p=this.players[0],idx=p.currently_triggering_card_idx;noOther();
  check(p.currently_triggering_card_id===c.runtime_id,'active_card_identity');
  if(c.kind==='falling_paper'){
   const e=take(c,p,'effect_branch'),v=c.config.otherParams;
   if(e.value===0)this.increase_idx_def(0,v[0]);
   else if(e.value===1)this.increase_idx_hp(0,v[1]);
   else this.add_c_of_x(v[2],'guard_up');
   e.after=snap(p);return;
  }
  check(c.kind==='divine','unsupported_card_kind');
  check(Number.isInteger(idx)&&idx>=0&&idx<p.cards.length&&p.cards[idx]===c.runtime_id,'physical_grid_required');
  check(c.config.otherParams[0]===1,'unaudited_parent_repeat_count');
  const original=p.cards[idx];
  // Parent configuration is cached by its action object, even while the live
  // card slot takes the selected identity. Parent effects precede the read.
  this.increase_idx_def(0,c.config.def);this.increase_idx_hp(0,c.config.otherParams[1]);
  const e=take(c,p,'card_identity'),selected=targets.get(e.value);
  try{
   p.cards[idx]=selected.runtime_id;e.selected_runtime_id=selected.runtime_id;
   // ExecuteEffect(true): same physical grid, existing before/body/after hooks.
   // Do not use play_card / ordinary Execute, repay costs or consume repeats.
   this.trigger_card(selected.runtime_id,idx);
   if(selected.action_again)this.chase();
   check(p.currently_triggering_card_id===c.runtime_id&&p.currently_triggering_card_idx===idx,'nested_identity_not_restored');
   e.after_nested=snap(p);
  }finally{p.cards[idx]=original;e.restored_runtime_id=original;}
  e.after=snap(p);
 };
 for(const method of facts.blocked_random_entrypoints){
  check(typeof game[method]==='function','missing_random_guard:'+method);
  game[method]=()=>{throw new Error('nested_card_parameters_unresolved:unsupported_consumer:'+method);};
 }
 game.rng=()=>{throw new Error('nested_card_parameters_unresolved:other_random_consumer');};
 installed.add(game);
 return {verifyTerminal:()=>{noOther();check(cursor===values.length,'unused_parameters');},
  metadata:()=>({evidence_sha256:digest,events:structuredClone(events),consumed:cursor,total_parameters:values.length,
   record_conditioned:true,other_rng_allowed:false,recorded_action_log:false,random_distribution_verified:false,
   legal_random_pool_verified:false,counterfactual_reuse_allowed:false,training_label_allowed:false})};
}

export function installNestedCardParameters(root,swogi,game,value,order,battle){
 if(value===undefined)return null;
 check(object(value)&&Object.keys(value).sort().join(',')==='battle_sha256,record_binding,stream','explicit_bound_stream_required');
 check(object(battle)&&battle.first_player===order[0]&&!['falling_paper','typed_parameters','cloud_sword_parameters','card_parameters','debuff_parameters','probability_parameters'].some(k=>Object.hasOwn(battle,k)),'exclusive_bound_initiative_required');
 const plain=Object.fromEntries(Object.entries(battle).filter(([k])=>k!=='nested_card_parameters'));
 check(hash(canonical(plain))===value.battle_sha256,'compiled_battle_binding_mismatch');
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-nested-card-parameters-v89.json'));
 check(hash(bytes)===digest,'evidence_changed');const facts=JSON.parse(bytes);
 for(const [p,h] of Object.entries(facts.source_sha256))check(hash(fs.readFileSync(path.join(root,p)))===h,'source_changed:'+p);
 const expected=facts.admitted_records[value.record_binding?.record_id];
 check(expected!==undefined&&canonical(expected.binding)===canonical(value.record_binding),'unaudited_record_binding');
 check(expected.compiled_battle_sha256===value.battle_sha256,'unaudited_compiled_start');
 check(hash(canonical(value.stream))===expected.binding.stream_sha256,'recorded_stream_mismatch');
 return createNestedCardQueue(swogi,game,value.stream,order,facts);
}
