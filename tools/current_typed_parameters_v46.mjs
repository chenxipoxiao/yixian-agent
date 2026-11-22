// Replay-only FIFO: consumers declare their operation before taking a value.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='0930869a19a33277d9d0bed409e23388a016c0a6f5761d07bb7aaad91379f457';
const installed=new WeakSet();
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const check=(v,m)=>{if(!v)throw new Error('typed_parameters_unresolved:'+m);};
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const canonical=v=>Array.isArray(v)?'['+v.map(canonical).join(',')+']':object(v)?'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}':JSON.stringify(v);
const snap=p=>({hp:p.hp,max_hp:p.max_hp,def:p.def,weaken:p.weaken,hexagram:p.hexagram,triggered_hexagram_count:p.triggered_hexagram_count});

export function installTypedParameters(root,swogi,game,value,order=[0,1],battle) {
 if(value===undefined)return null;
 check(!installed.has(game),'already_installed');
 check(object(value)&&Object.keys(value).length===3,'explicit_stream_required');
 check(Array.isArray(value.owners)&&value.owners.length===2&&value.owners.every(x=>typeof x==='boolean')&&value.owners.some(Boolean),'invalid_owners');
 check(Array.isArray(value.stream)&&value.stream.length>value.owners.filter(Boolean).length&&value.stream.length<=256&&value.stream.every(Number.isSafeInteger),'invalid_complete_stream');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 check(object(battle)&&battle.first_player===order[0]&&battle.falling_paper===undefined,'exclusive_bound_initiative_required');
 check(hash(canonical(Object.fromEntries(Object.entries(battle).filter(([k])=>k!=='typed_parameters'))))===value.battle_sha256,'compiled_battle_binding_mismatch');
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-typed-parameters-v46.json'));
 check(hash(bytes)===digest,'evidence_changed');
 const facts=JSON.parse(bytes);
 for(const [p,h] of Object.entries(facts.source_sha256))check(hash(fs.readFileSync(path.join(root,p)))===h,'source_changed:'+p);
 const states=new Map(game.players.map((p,i)=>[p,{owned:value.owners[order[i]],index:order[i],opened:false}]));
 const stream=[...value.stream],events=[],pending=[];let cursor=0;
 const noOtherRandom=()=>check(!game.used_randomness,'other_random_consumer');
 const take=(kind,p,lo,hi,extra={})=>{
  noOtherRandom();check(cursor<stream.length,'parameter_underflow:'+kind);
  const value=stream[cursor];check(value>=lo&&value<=hi,'parameter_out_of_range:'+kind);
  const event={kind,player_index:states.get(p).index,queue_index:cursor++,value,...extra};events.push(event);return event;
 };
 const plants=game.do_plant_start_permanent_buffs.bind(game);
 game.do_plant_start_permanent_buffs=function(...args) {
  const p=this.players[0],s=states.get(p);noOtherRandom();
  if(s.owned&&!s.opened) {
   const event=take('falling_paper',p,0,3,{strategy_id:16024,before:snap(p)}),branch=event.value;s.opened=true;
   if(branch===0||branch===1)check(Number.isInteger(p.hp)&&p.hp>=0&&p.hp*10<=2147483647,'unsupported_hp_or_int32_overflow');
   if(branch===0) {
    const amount=Math.floor(p.hp*10/100);event.requested=amount;
    this.increase_idx_max_hp(0,amount);this.increase_idx_hp(0,amount);
   } else if(branch===1) {event.requested=Math.floor(p.hp*10/100);this.increase_idx_def(0,event.requested);}
   else if(branch===2)pending.push({player_index:s.index,kind:'exchange_chance',amount:1,authoritative_credit_applied:false});
   else this.increase_idx_debuff(0,'weaken',1);
   event.after=snap(p);
  }
  return plants(...args);
 };
 const therapy=new Map(facts.cards.map(c=>[swogi[c.runtime_id],c]));
 check(!therapy.has(undefined),'missing_card_identity');
 const cardBody=game.just_do_the_card_and_nothing_else.bind(game);
 const triggerHexagram=game.trigger_hexagram.bind(game);
 game.just_do_the_card_and_nothing_else=function(card) {
  const config=therapy.get(card);
  if(!config)return cardBody(card);
  const p=this.players[0];noOtherRandom();
  check([...states.values()].every(s=>!s.owned||s.opened),'card_before_openings');
  check(Object.entries(p).every(([k,v])=>!k.startsWith('resonance_')||v===0),'resonance_context');
  const before=snap(p),[lo,hi]=config.otherParams;
  // Client GetNextRandomValue(true) spends ordinary hexagram before dequeuing.
  // Even a guaranteed outcome has a queue item. Buff773 is outside admission.
  const forced=triggerHexagram(0);
  const event=take('qi_therapy',p,lo,hi,{raw_card_id:config.id,runtime_card_id:config.runtime_id,before,forced_by_hexagram:forced});
  check(!forced||event.value===hi,'forced_hexagram_result_mismatch');
  this.increase_idx_max_hp(0,lo);this.increase_idx_hp(0,event.value);
  event.after=snap(p);
 };
 // Intercept typed entry points too: some guaranteed branches never call rng().
 for(const method of facts.blocked_random_entrypoints) {
  check(typeof game[method]==='function','missing_random_guard:'+method);
  game[method]=()=>{throw new Error('typed_parameters_unresolved:unsupported_consumer:'+method);};
 }
 game.rng=()=>{throw new Error('typed_parameters_unresolved:other_random_consumer');};
 installed.add(game);
 return {
  verifyTerminal:()=>{
   noOtherRandom();check(cursor===stream.length&&[...states.values()].every(s=>!s.owned||s.opened),'unused_parameters_or_missing_opening');
  },
  metadata:()=>({evidence_sha256:digest,events:structuredClone(events),consumed:cursor,total_parameters:stream.length,
   record_conditioned:true,other_rng_allowed:false,pending_match_rewards:structuredClone(pending),
   authoritative_exchange_credit_applied:false,counterfactual_reuse_allowed:false,recorded_action_log:false,
   distribution_verified:false,training_label_allowed:false}),
 };
}
