// Original-record raw comparisons and magnitudes, not a random generator.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='e19697d124db2e208ff4a1ad0dfc2f4e16d6650c724b81532a45d80ceac8290c';
const installed=new WeakSet();
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const check=(ok,why)=>{if(!ok)throw new Error('probability_parameters_unresolved:'+why);};
const canonical=x=>Array.isArray(x)?'['+x.map(canonical).join(',')+']':object(x)?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}':JSON.stringify(x);
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const snap=p=>({hp:p.hp,max_hp:p.max_hp,qi:p.qi,def:p.def,hexagram:p.hexagram,triggered_hexagram_count:p.triggered_hexagram_count});

export function createProbabilityQueue(swogi,game,stream,order,facts) {
 check(!installed.has(game),'already_installed');
 check(Array.isArray(stream)&&stream.length>0&&stream.length<=256&&stream.every(x=>Number.isSafeInteger(x)&&x>=0&&x<=2147483647),'invalid_stream');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(x=>x===0||x===1),'invalid_order');
 const values=[...stream],cards=new Map(facts.cards.map(c=>[swogi[c.runtime_id],c]));
 check(!cards.has(undefined),'missing_card_identity');
 const seats=new Map(game.players.map((p,i)=>[p,order[i]]));
 const events=[];let cursor=0,active=null;
 const noOther=()=>check(!game.used_randomness,'other_random_consumer');
 const trigger=game.trigger_hexagram.bind(game);
 const take=(type,args)=>{
  noOther();check(active!==null,'read_outside_audited_card');
  const {config,p}=active,expected=config.reads[active.reads];
  check(game.players[0]===p&&p.currently_triggering_card_id===config.runtime_id,'active_card_identity');
  check(expected?.type===type,'consumer_type_or_count:'+config.kind);
  check(type==='range'?args[0]===expected.lo&&args[1]===expected.hi:args[0]===expected.threshold,'consumer_arguments:'+config.kind);
  check(Object.entries(p).every(([k,v])=>!k.startsWith('resonance_')||v===0),'resonance_context');
  const before=snap(p);const forced=trigger(0);noOther();
  check(cursor<values.length,'parameter_underflow:'+config.kind);
  const value=values[cursor];
  let result;
  if(type==='range'){
   check(value>=expected.lo&&value<=expected.hi,'magnitude_out_of_range');
   check(!forced||value===expected.hi,'forced_magnitude_mismatch');result=value;
  }else{
   // Exact client bge/strict comparison. Do not invent a producer domain or
   // require a particular guaranteed encoding (e.g. zero).
   result=value<expected.threshold;check(!forced||result,'forced_probability_mismatch');
  }
  events.push({kind:config.kind,type,raw_card_id:config.id,runtime_card_id:config.runtime_id,
    player_index:seats.get(p),slot:p.currently_triggering_card_idx,queue_index:cursor++,card_read_index:active.reads++,
    value,result,request:{...expected},forced_by_hexagram:forced,before,after_read:snap(p)});
  return result;
 };
 const body=game.just_do_the_card_and_nothing_else.bind(game);
 game.just_do_the_card_and_nothing_else=function(card){
  const config=cards.get(card),outer=active;active=config?{config,p:this.players[0],reads:0}:null;
  try{
   let result;
   if(config?.kind==='qi_therapy'){
    // v86 client order: read, maxHP, then HP. Keep the old entry point frozen.
    const n=take('range',config.otherParams.slice(0,2));
    this.increase_idx_max_hp(0,config.otherParams[0]);this.increase_idx_hp(0,n);
   }else result=body(card);
   if(config)check(active.reads===config.reads.length,'missing_card_reads:'+config.kind);
   return result;
  }finally{active=outer;}
 };
 for(const method of facts.blocked_random_entrypoints){
  check(typeof game[method]==='function','missing_random_guard:'+method);
  game[method]=()=>{throw new Error('probability_parameters_unresolved:unsupported_consumer:'+method);};
 }
 game.rand_range=(lo,hi)=>take('range',[lo,hi]);
 game.if_c_pct=c=>take('probability',[c]);
 game.rng=()=>{throw new Error('probability_parameters_unresolved:other_random_consumer');};
 installed.add(game);
 return {verifyTerminal:()=>{noOther();check(active===null&&cursor===values.length,'unused_parameters');},
  metadata:()=>({evidence_sha256:digest,events:structuredClone(events),consumed:cursor,total_parameters:values.length,
   record_conditioned:true,other_rng_allowed:false,recorded_action_log:false,probability_producer_domain_verified:false,
   guaranteed_exact_encoding_verified:false,random_distribution_verified:false,counterfactual_reuse_allowed:false,training_label_allowed:false})};
}

export function installProbabilityParameters(root,swogi,game,value,order,battle){
 if(value===undefined)return null;
 check(object(value)&&Object.keys(value).sort().join(',')==='battle_sha256,record_binding,stream','explicit_bound_stream_required');
 check(object(battle)&&battle.first_player===order[0]&&!['falling_paper','typed_parameters','cloud_sword_parameters','card_parameters','debuff_parameters'].some(k=>Object.hasOwn(battle,k)),'exclusive_bound_initiative_required');
 const plain=Object.fromEntries(Object.entries(battle).filter(([k])=>k!=='probability_parameters'));
 check(hash(canonical(plain))===value.battle_sha256,'compiled_battle_binding_mismatch');
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-probability-parameters-v88.json'));
 check(hash(bytes)===digest,'evidence_changed');const facts=JSON.parse(bytes);
 for(const [p,h] of Object.entries(facts.source_sha256))check(hash(fs.readFileSync(path.join(root,p)))===h,'source_changed:'+p);
 const expected=facts.admitted_records[value.record_binding?.record_id];
 check(expected!==undefined&&canonical(expected.binding)===canonical(value.record_binding),'unaudited_record_binding');
 check(expected.compiled_battle_sha256===value.battle_sha256,'unaudited_compiled_start');
 check(hash(canonical(value.stream))===expected.binding.stream_sha256,'recorded_stream_mismatch');
 return createProbabilityQueue(swogi,game,value.stream,order,facts);
}
