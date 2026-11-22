// Complete, original-record FIFO for Qi Therapy and Cutting Weeds.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='ada9bf8434263aa679f59d653c20a04a448d037ea49b473092d5216f0a549754';
const installed=new WeakSet();
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const check=(ok,why)=>{if(!ok)throw new Error('card_parameters_unresolved:'+why);};
const canonical=x=>Array.isArray(x)?'['+x.map(canonical).join(',')+']':object(x)?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}':JSON.stringify(x);
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const snap=p=>({hp:p.hp,max_hp:p.max_hp,hexagram:p.hexagram,triggered_hexagram_count:p.triggered_hexagram_count});

// Component entry is exported for boundary checks, not a whole-battle adapter.
export function createTypedCardQueue(swogi,game,stream,order,facts) {
 check(!installed.has(game),'already_installed');
 check(Array.isArray(stream)&&stream.length>0&&stream.length<=256&&stream.every(x=>Number.isSafeInteger(x)&&x>=0&&x<=2147483647),'invalid_stream');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(x=>x===0||x===1),'invalid_order');
 const values=[...stream],cards=new Map(facts.cards.map(c=>[swogi[c.runtime_id],c]));
 check(!cards.has(undefined),'missing_card_identity');
 const seats=new Map(game.players.map((p,i)=>[p,order[i]]));
 const events=[];let cursor=0;
 const noOther=()=>check(!game.used_randomness,'other_random_consumer');
 const trigger=game.trigger_hexagram.bind(game);
 const take=(card,p)=>{
  noOther();
  check(Object.entries(p).every(([k,v])=>!k.startsWith('resonance_')||v===0),'resonance_context');
  const forced=trigger(0);noOther();
  check(cursor<values.length,'parameter_underflow:'+card.kind);
  const value=values[cursor],[lo,hi]=card.otherParams;
  check(value>=lo&&value<=hi,'parameter_out_of_range:'+card.kind);
  check(!forced||value===hi,'forced_hexagram_result_mismatch');
  const event={kind:card.kind,player_index:seats.get(p),queue_index:cursor++,value,
    raw_card_id:card.id,runtime_card_id:card.runtime_id,slot:p.currently_triggering_card_idx,
    forced_by_hexagram:forced,before:snap(p),target_before:snap(game.players[1])};
  events.push(event);return event;
 };
 const original=game.just_do_the_card_and_nothing_else.bind(game);
 game.just_do_the_card_and_nothing_else=function(card) {
  const config=cards.get(card);if(!config)return original(card);
  const p=this.players[0];noOther();
  if(config.kind==='cutting_weeds')for(let i=0;i<config.attackCount;i++)this.atk(config.attack);
  const event=take(config,p);
  if(config.kind==='qi_therapy'){
   this.increase_idx_max_hp(0,config.otherParams[0]);this.increase_idx_hp(0,event.value);
  }else this.reduce_enemy_max_hp(event.value);
  event.after=snap(p);event.target_after=snap(this.players[1]);
 };
 for(const method of facts.blocked_random_entrypoints){
  check(typeof game[method]==='function','missing_random_guard:'+method);
  game[method]=()=>{throw new Error('card_parameters_unresolved:unsupported_consumer:'+method);};
 }
 game.rng=()=>{throw new Error('card_parameters_unresolved:other_random_consumer');};
 installed.add(game);
 return {verifyTerminal:()=>{noOther();check(cursor===values.length,'unused_parameters');},
  metadata:()=>({evidence_sha256:digest,events:structuredClone(events),consumed:cursor,total_parameters:values.length,
   record_conditioned:true,other_rng_allowed:false,recorded_action_log:false,
   random_distribution_verified:false,counterfactual_reuse_allowed:false,training_label_allowed:false})};
}

export function installCardParameters(root,swogi,game,value,order,battle){
 if(value===undefined)return null;
 check(object(value)&&Object.keys(value).sort().join(',')==='battle_sha256,record_binding,stream','explicit_bound_stream_required');
 check(object(battle)&&battle.first_player===order[0]&&!['falling_paper','typed_parameters','cloud_sword_parameters'].some(k=>Object.hasOwn(battle,k)),'exclusive_bound_initiative_required');
 const plain=Object.fromEntries(Object.entries(battle).filter(([k])=>k!=='card_parameters'));
 check(hash(canonical(plain))===value.battle_sha256,'compiled_battle_binding_mismatch');
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-card-parameters-v86.json'));
 check(hash(bytes)===digest,'evidence_changed');const facts=JSON.parse(bytes);
 for(const [p,h] of Object.entries(facts.source_sha256))check(hash(fs.readFileSync(path.join(root,p)))===h,'source_changed:'+p);
 const expected=facts.admitted_records[value.record_binding?.record_id];
 check(expected!==undefined&&canonical(expected.binding)===canonical(value.record_binding),'unaudited_record_binding');
 check(expected.compiled_battle_sha256===value.battle_sha256,'unaudited_compiled_start');
 check(hash(canonical(value.stream))===expected.binding.stream_sha256,'recorded_stream_mismatch');
 return createTypedCardQueue(swogi,game,value.stream,order,facts);
}
