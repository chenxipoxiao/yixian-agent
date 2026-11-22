// The complete recorded stream may contain only16024 opening branches here.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='17c530b297fff385ed1897742680bc0cb83ccef568ac208084669d7a6c31bad1';
const installed=new WeakSet();
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const check=(v,m)=>{if(!v)throw new Error('falling_paper_unresolved:'+m);};
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const canonical=v=>Array.isArray(v)?'['+v.map(canonical).join(',')+']':object(v)?'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}':JSON.stringify(v);
const snapshot=p=>({hp:p.hp,max_hp:p.max_hp,def:p.def,weaken:p.weaken});
export function installFallingPaper(root,game,value,order=[0,1],battle) {
 if(value===undefined)return null;
 check(!installed.has(game),'already_installed');
 check(object(value)&&Object.keys(value).length===3,'explicit_stream_required');
 check(Array.isArray(value.owners)&&value.owners.length===2&&value.owners.every(x=>typeof x==='boolean')&&value.owners.some(Boolean),'invalid_owners');
 check(Array.isArray(value.stream)&&value.stream.length===value.owners.filter(Boolean).length&&value.stream.every(x=>Number.isInteger(x)&&x>=0&&x<=3),'invalid_complete_stream');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 check(object(battle),'battle_binding_required');
 const projected=Object.fromEntries(Object.entries(battle).filter(([k])=>k!=='falling_paper'));
 check(hash(canonical(projected))===value.battle_sha256,'compiled_battle_binding_mismatch');
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-falling-paper-v45.json'));
 check(hash(bytes)===digest,'evidence_changed');
 const facts=JSON.parse(bytes);
 for(const [p,h] of Object.entries(facts.source_sha256))check(hash(fs.readFileSync(path.join(root,p)))===h,'source_changed:'+p);
 const states=new Map(game.players.map((p,i)=>[p,{owned:value.owners[order[i]],index:order[i],opened:false}]));
 const stream=[...value.stream],events=[],pending=[];let cursor=0;
 const plants=game.do_plant_start_permanent_buffs.bind(game);
 // Installed before3011, after7069, so execution is3011 ->16024 ->7069.
 game.do_plant_start_permanent_buffs=function(...args) {
  const p=this.players[0],s=states.get(p);
  check(!this.used_randomness,'other_random_consumer');
  if(s.owned&&!s.opened) {
   check(cursor<stream.length,'parameter_underflow');
   const branch=stream[cursor++],before=snapshot(p);
   s.opened=true;
   const event={player_index:s.index,strategy_id:16024,queue_index:cursor-1,branch,before};events.push(event);
   if(branch===0||branch===1)check(Number.isInteger(p.hp)&&p.hp>=0&&p.hp*facts.config.otherParams[branch]<=2147483647,'unsupported_hp_or_int32_overflow');
   if(branch===0) {
    const amount=Math.floor(p.hp*facts.config.otherParams[0]/100);event.requested=amount;
    this.increase_idx_max_hp(0,amount);this.increase_idx_hp(0,amount);
   } else if(branch===1) {
    const amount=Math.floor(p.hp*facts.config.otherParams[1]/100);event.requested=amount;
    this.increase_idx_def(0,amount);
   } else if(branch===2) {
    pending.push({player_index:s.index,kind:'exchange_chance',amount:facts.config.otherParams[2],authoritative_credit_applied:false});
   } else this.increase_idx_debuff(0,'weaken',facts.config.otherParams[3]);
   event.after=snapshot(p);
  }
  return plants(...args);
 };
 // A second random source would require a distinct typed consumer adapter.
 // Never silently spend its recorded result on16024 or substitute a seeded draw.
 game.rng=()=>{throw new Error('falling_paper_unresolved:other_random_consumer');};
 installed.add(game);
 return {
  verifyTerminal:()=>{
   check(!game.used_randomness,'other_random_consumer');
   check(cursor===stream.length&&[...states.values()].every(s=>!s.owned||s.opened),'unused_parameters_or_missing_opening');
  },
  metadata:()=>({evidence_sha256:digest,events:structuredClone(events),consumed:cursor,total_parameters:stream.length,
   record_conditioned:true,other_rng_allowed:false,pending_match_rewards:structuredClone(pending),
   authoritative_exchange_credit_applied:false,counterfactual_reuse_allowed:false,recorded_action_log:false,
   distribution_verified:false,training_label_allowed:false}),
 };
}
