// One original-record FIFO across magnitudes, probabilities and debuff IDs.
// No sampler: values are accepted only by the active, audited consumer.
const installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('paper_mixed_parameters_unresolved:'+why);};
export function createPaperMixedQueue(swogi,game,stream,order,facts,owners){
 check(!installed.has(game),'already_installed');
 check(Array.isArray(stream)&&stream.length>0&&stream.length<=256&&stream.every(x=>Number.isSafeInteger(x)&&x>=-1&&x<=2147483647),'invalid_stream');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(x=>x===0||x===1),'invalid_order');
 const values=[...stream],cards=new Map(facts.cards.map(c=>[swogi[c.runtime_id],c]));
 check(!cards.has(undefined),'missing_card_identity');
 const fields=facts.debuff_fields,seats=new Map(game.players.map((p,i)=>[p,order[i]])),events=[];
 const snap=p=>Object.fromEntries(['hp','max_hp','qi','def','hexagram','triggered_hexagram_count',...Object.values(fields)].map(k=>[k,p[k]]));
 let cursor=0,active=null,post=null,readersInstalled=false;
 check(Array.isArray(owners)&&owners.length===2&&owners.every(x=>typeof x==='boolean')&&owners.some(Boolean),'invalid_owners');
 const states=new Map(game.players.map((p,i)=>[p,{owned:owners[order[i]],index:order[i],opened:false}])),pending=[];
 const opened=()=>[...states.values()].every(s=>!s.owned||s.opened);
 const plants=game.do_plant_start_permanent_buffs.bind(game);
 // The bridge installs this before 3011 and after 7069: execution is
 // 3011 -> 16024 -> 7069 -> permanent plants, matching frozen v45/v46.
 game.do_plant_start_permanent_buffs=function(...args){
  const p=this.players[0],s=states.get(p);noOther();
  check(readersInstalled,'readers_not_installed');
  if(s.owned&&!s.opened){
   check(cursor<values.length,'parameter_underflow:falling_paper');
   const value=values[cursor];check(value>=0&&value<=3,'opening_branch_out_of_range');
   const e={kind:'falling_paper',type:'opening_branch',phase:'opening',strategy_id:16024,player_index:s.index,queue_index:cursor++,value,before:snap(p),forced_by_hexagram:false};
   events.push(e);s.opened=true;
   if(value===0||value===1)check(Number.isInteger(p.hp)&&p.hp>=0&&p.hp*10<=2147483647,'unsupported_hp_or_int32_overflow');
   if(value===0){e.requested=Math.floor(p.hp*10/100);this.increase_idx_max_hp(0,e.requested);this.increase_idx_hp(0,e.requested);}
   else if(value===1){e.requested=Math.floor(p.hp*10/100);this.increase_idx_def(0,e.requested);}
   else if(value===2)pending.push({player_index:s.index,kind:'exchange_chance',amount:1,authoritative_credit_applied:false});
   else this.increase_idx_debuff(0,'weaken',1);
   e.after=snap(p);
  }
  return plants(...args);
 };
 const noOther=()=>check(!game.used_randomness,'other_random_consumer');
 const context=()=>{
  noOther();check(opened(),'card_before_openings');check(active!==null,'read_outside_audited_card');
  const {config,p}=active;
  check(game.players[0]===p&&p.currently_triggering_card_id===config.runtime_id,'active_card_identity');
  check(Object.entries(p).every(([k,v])=>!k.startsWith('resonance_')||v===0),'resonance_context');
  check(cursor<values.length,'parameter_underflow:'+config.kind);
  return {config,p};
 };
 function installReaders(){
 check(!readersInstalled,'readers_already_installed');readersInstalled=true;
 const trigger=game.trigger_hexagram.bind(game);
 const take=(type,args)=>{
  const {config,p}=context();
  const expected=post?{type:'probability',threshold:1}:config.reads[active.reads];
  if(post)check(post.active===active&&config.kind==='underhand_moon'&&post.reads===0&&p.act_underhand_stacks>0,'unsupported_post_action_read');
  check(expected?.type===type,'consumer_type_or_count:'+config.kind);
  check(type==='range'?args[0]===expected.lo&&args[1]===expected.hi:args[0]===expected.threshold,'consumer_arguments:'+config.kind);
  const before=snap(p),forced=trigger(0);noOther();const value=values[cursor];
  check(value>=0,'unrestored_random_fallback');
  let result;
  if(type==='range'){
   check(value>=expected.lo&&value<=expected.hi,'magnitude_out_of_range');
   check(!forced||value===expected.hi,'forced_magnitude_mismatch');result=value;
  }else{result=value<expected.threshold;check(!forced||result,'forced_probability_mismatch');}
  events.push({kind:post?'underhand_108':config.kind,type,phase:post?'post_action':'card_body',
   raw_card_id:config.id,runtime_card_id:config.runtime_id,player_index:seats.get(p),slot:p.currently_triggering_card_idx,
   queue_index:cursor++,card_read_index:post?post.reads++:active.reads++,value,result,request:{...expected},forced_by_hexagram:forced,before,after_read:snap(p)});
  return result;
 };
 const body=game.just_do_the_card_and_nothing_else.bind(game),postAction=game.if_post_action.bind(game);
 game.just_do_the_card_and_nothing_else=function(card){
  const config=cards.get(card),saved=active;active=config?{config,p:this.players[0],reads:0,debuffReads:0}:null;
  try{
   let result;
   if(config?.kind==='qi_therapy'){
    const n=take('range',config.otherParams.slice(0,2));
    this.increase_idx_max_hp(0,config.otherParams[0]);this.increase_idx_hp(0,n);
   }else result=body(card);
   if(config){
    check(active.reads===config.reads.length,'missing_card_reads:'+config.kind);
    check(active.debuffReads===(config.kind==='exorcism_elixir'?config.otherParams[0]:0),'missing_debuff_reads');
   }
   return result;
  }finally{active=saved;}
 };
 game.if_post_action=function(){
  const saved=post;post={active,reads:0};
  try{return postAction();}finally{post=saved;}
 };
 for(const method of facts.blocked_random_entrypoints){
  check(typeof game[method]==='function','missing_random_guard:'+method);
  game[method]=()=>{throw new Error('paper_mixed_parameters_unresolved:unsupported_consumer:'+method);};
 }
 game.rand_range=(lo,hi)=>take('range',[lo,hi]);game.if_c_pct=c=>take('probability',[c]);
 game.rng=()=>{throw new Error('paper_mixed_parameters_unresolved:other_random_consumer');};
 game.reduce_idx_random_debuff_by_c_n_times=function(idx,c,n){
  const {config,p}=context();
  check(!post&&config.kind==='exorcism_elixir'&&idx===0,'unsupported_reduction_consumer');
  check(active.debuffReads===0&&c===config.otherParams[1]&&n===config.otherParams[0],'reduction_contract_changed');
  for(let i=0;i<n;i++){
   context();const value=values[cursor],field=fields[value];
   check(value===-1||field!==undefined,'unknown_buff_id');
   if(value!==-1)check(Number.isSafeInteger(p[field])&&p[field]>0,'selected_debuff_not_present');
   const e={kind:config.kind,type:'debuff_id',phase:'card_body',raw_card_id:config.id,runtime_card_id:config.runtime_id,
    player_index:seats.get(p),slot:p.currently_triggering_card_idx,queue_index:cursor++,card_read_index:active.debuffReads++,value,
    field:field??null,amount:c,explicit_noop:value===-1,forced_by_hexagram:false,before:snap(p)};
   if(value!==-1)this.reduce_idx_x_by_c(0,field,c);
   e.after_read=snap(p);events.push(e);
  }
 };
 }
 installed.add(game);
 return {installReaders,verifyTerminal:()=>{noOther();check(readersInstalled&&opened()&&active===null&&post===null&&cursor===values.length,'unused_parameters_or_missing_opening');},
  metadata:()=>({events:structuredClone(events),consumed:cursor,total_parameters:values.length,reader_mode:'falling_paper_mixed',pending_match_rewards:structuredClone(pending),authoritative_exchange_credit_applied:false,
   record_conditioned:true,other_rng_allowed:false,recorded_action_log:false,random_distribution_verified:false,
   probability_producer_domain_verified:false,counterfactual_reuse_allowed:false,training_label_allowed:false})};
}
