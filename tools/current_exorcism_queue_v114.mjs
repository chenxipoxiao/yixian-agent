// Typed, original-record FIFO. Buff identifiers are not RNG fractions or indices.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='1533eafebe87426796ea6f03e8db8401d04376a0c752c59c59ea6b1dfafc276c';
const installed=new WeakSet();
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const check=(ok,why)=>{if(!ok)throw new Error('exorcism_parameters_unresolved:'+why);};
const canonical=x=>Array.isArray(x)?'['+x.map(canonical).join(',')+']':object(x)?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}':JSON.stringify(x);
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');

// Standalone component entry; the whole-battle entry below requires frozen binding.
export function createExorcismQueue(swogi,game,stream,order,facts,engraving){
 check(!installed.has(game),'already_installed');
 check(Array.isArray(stream)&&stream.length>0&&stream.length<=256&&stream.every(x=>Number.isSafeInteger(x)&&x>=-1&&x<=2147483647),'invalid_stream');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(x=>x===0||x===1),'invalid_order');
 const values=[...stream],cards=new Map(facts.cards.map(c=>[swogi[c.runtime_id],c]));
 check(!cards.has(undefined),'missing_card_identity');
 const seats=new Map(game.players.map((p,i)=>[p,order[i]])),fields=facts.debuff_fields,events=[];
 const snap=p=>Object.fromEntries(['hp','max_hp','physique','hexproof','hexagram','triggered_hexagram_count',...Object.values(fields)].map(k=>[k,p[k]]));
 let cursor=0,active=null,preCrash=null;
 const noOther=()=>check(!game.used_randomness,'other_random_consumer');
 const take=(kind,amount,phase='card_body')=>{
  noOther();const p=game.players[0];
  check(Object.entries(p).every(([k,v])=>!k.startsWith('resonance_')||v===0),'resonance_context');
  check(cursor<values.length,'parameter_underflow:'+kind);
  const value=values[cursor],field=fields[value];
  check(value===-1||field!==undefined,'unknown_buff_id');
  if(kind==='mad_obsession')check(value===-1||facts.mad_random_buff_ids.includes(value),'unsupported_random_add_buff_id');
  else if(value!==-1)check(Number.isSafeInteger(p[field])&&p[field]>0,'selected_debuff_not_present');
  const event={kind,phase,player_index:seats.get(p),queue_index:cursor++,value,field:field??null,amount,
   raw_card_id:active?.id??null,runtime_card_id:p.currently_triggering_card_id,slot:p.currently_triggering_card_idx,
   explicit_noop:value===-1,before:snap(p),target_before:snap(game.players[1])};
  events.push(event);return event;
 };
 const after=e=>{e.after=snap(game.players[0]);e.target_after=snap(game.players[1]);};
 // Keep every other random entry closed, including guaranteed/no-RNG branches.
 for(const method of facts.blocked_random_entrypoints){
  check(typeof game[method]==='function','missing_random_guard:'+method);
  game[method]=()=>{throw new Error('exorcism_parameters_unresolved:unsupported_consumer:'+method);};
 }
 game.rng=()=>{throw new Error('exorcism_parameters_unresolved:other_random_consumer');};
 game.reduce_idx_random_debuff_by_c_n_times=function(idx,c,n){
  check(active&&['exorcism_elixir','thousand_catty'].includes(active.kind)&&idx===0,'unsupported_reduction_consumer');
  const expected=active.kind==='exorcism_elixir'?[active.otherParams[1],active.otherParams[0]]:[active.otherParams[0],1];
  check(c===expected[0]&&n===expected[1],'reduction_contract_changed');
  for(let i=0;i<n;i++){
   const e=take(active.kind,c);if(!e.explicit_noop)this.reduce_idx_x_by_c(0,e.field,c);after(e);
  }
 };
 game.transfer_random_debuff=function(){
  const phase=preCrash?'next_crash_before_card':'card_body';
  check(preCrash||active?.kind==='crash_truncate','unsupported_transfer_consumer');
  const n=preCrash?preCrash.count:active.otherParams[0];
  check(Number.isSafeInteger(n)&&n>0&&n<=256,'invalid_transfer_count');
  for(let i=0;i<n;i++){
   const e=take('crash_truncate',1,phase);
   if(!e.explicit_noop){this.reduce_idx_x_by_c(0,e.field,1);this.increase_idx_debuff(1,e.field,1);}
   after(e);
  }
 };
 game.convert_random_debuffs_to_increase_atk=function(n){
  check(active?.kind==='demon_breaking_palm','unsupported_conversion_consumer');
  check(Number.isSafeInteger(n)&&n>=0&&n<=256&&n===Math.floor(this.players[0].physique/active.otherParams[0]),'conversion_contract_changed');
  let converted=0;
  for(let i=0;i<n;i++){
   const e=take(active.kind,1);
   if(e.explicit_noop){e.breaks_conversion_loop=true;after(e);break;}
   this.reduce_idx_x_by_c(0,e.field,1);converted++;after(e);
  }
  if(converted>0)this.increase_idx_x_by_c(0,'increase_atk',converted);
 };
 const allowed=new Map(game.players.map((p,i)=>[p,engraving.players[order[i]].filter(e=>e.strategy_id===13002)]));
 check([...allowed.values()].some(es=>es.length===1),'engraving_owner_required');
 const usedEngraving=new WeakSet();
 game.consume_exorcism_engraving_v114=function(slot,healPerMiss,count){
  const p=this.players[0],entries=allowed.get(p);
  check(entries.length===1&&entries[0].slot===slot&&p.currently_triggering_card_idx===slot&&p.trigger_depth===1,'engraving_slot_or_temporary');
  check(!usedEngraving.has(p)&&!p.can_post_action[slot],'engraving_already_used');
  check(healPerMiss===2&&count===4,'engraving_parameters');usedEngraving.add(p);
  const hpBefore=p.hp;let removed=0;
  for(let i=0;i<count;i++){
   const e=take('engraving_13002',1,'season_on_play_card');
   if(!e.explicit_noop){this.reduce_idx_x_by_c(0,e.field,1);removed++;}
   after(e);
  }
  const requestedHeal=(count-removed)*healPerMiss;
  if(requestedHeal>0)this.increase_idx_hp(0,requestedHeal);
  events.push({kind:'engraving_13002_summary',player_index:seats.get(p),slot,removed_count:removed,noop_count:count-removed,
   requested_heal:requestedHeal,hp_before:hpBefore,hp_after:p.hp});
 };
 const pre=game.do_pre_crash_fist.bind(game);
 game.do_pre_crash_fist=function(id){
  const saved=preCrash;preCrash=this.is_crash_fist(id)?{count:this.players[0].crash_fist_truncate_stacks}:null;
  try{return pre(id);}finally{preCrash=saved;}
 };
 const body=game.just_do_the_card_and_nothing_else.bind(game);
 game.just_do_the_card_and_nothing_else=function(card){
  const config=cards.get(card),saved=active;active=config??null;
  try{
   if(!config)return body(card);
   noOther();const p=this.players[0];
   if(config.kind!=='mad_obsession')return body(card);
   this.increase_idx_debuff(0,'styx',config.otherParams[0]);
   for(let i=0;i<config.otherParams[1];i++){
    const e=take(config.kind,1);if(!e.explicit_noop)this.increase_idx_debuff(0,e.field,1);after(e);
   }
   const count=Object.values(fields).reduce((sum,k)=>{check(Number.isSafeInteger(p[k]),'invalid_debuff_state');return sum+Math.max(0,p[k]);},0);
   this.increase_idx_physique(0,Math.min(config.otherParams[2],config.physique+count));
  }finally{active=saved;}
 };
 installed.add(game);
 return {verifyTerminal:()=>{noOther();check(cursor===values.length,'unused_parameters');},
  metadata:()=>({evidence_sha256:digest,events:structuredClone(events),consumed:cursor,total_parameters:values.length,
   record_conditioned:true,other_rng_allowed:false,recorded_action_log:false,
   random_distribution_verified:false,counterfactual_reuse_allowed:false,training_label_allowed:false})};
}

