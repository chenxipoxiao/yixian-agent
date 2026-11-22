import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='c3f97a4e9021fc0a86b64eb61806e5e9d201a1498239dfa99f224eb9b1098e34',installed=new WeakSet();
const check=(v,m)=>{if(!v)throw new Error('regen_opening_unresolved:'+m);};
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const nonnegative=(x,m)=>check(Number.isSafeInteger(x)&&x>=0&&x<=2147483647,m);
export function createRegenOpening(root,game,value,order=[0,1]) {
 if(value===undefined)return null;
 check(object(value)&&Object.keys(value).length===1&&Array.isArray(value.players)&&value.players.length===2,'explicit_players_required');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 check(value.players.every(a=>Array.isArray(a)&&new Set(a.map(e=>e?.strategy_id)).size===a.length
  &&a.every(e=>object(e)&&[7103,7135].includes(e.strategy_id)&&(e.strategy_id===7103?Object.keys(e).length===1:Object.keys(e).length===2&&typeof e.enabled==='boolean'))),'explicit_ownership_and_switch_required');
 check(value.players.some(a=>a.length),'empty_ownership');check(!installed.has(game),'already_installed');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-regen-opening-v73.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');const facts=JSON.parse(raw);
 for(const [p,h] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 const states=new Map(game.players.map((p,i)=>[p,{index:order[i],entries:new Map(value.players[order[i]].map(e=>[e.strategy_id,e])),opened:new Set(),marker477:0}]));
 const events=[],boundaries=new Set();
 const emit=(p,id,phase,extra)=>events.push({player_index:states.get(p).index,strategy_id:id,phase,...extra});
 const normalRegen=game.do_regen.bind(game);
 game.do_regen=function(...args){
  const p=this.players[0],s=states.get(p);
  if(s.marker477===0)return normalRegen(...args);
  nonnegative(p.regen,'invalid_regeneration');
  if(p.regen===0)return normalRegen(...args);
  const base=p.regen,amount=base*2;nonnegative(amount,'regeneration_overflow');const before=p.hp;
  this.heal(amount);
  emit(p,7135,'turn_start_regeneration',{buff_id:248,marker477:s.marker477,base,requested:amount,before,after:p.hp});
 };
 const normalInjury=game.do_internal_injury.bind(game);
 game.do_internal_injury=function(idx,isStart){
  const p=this.players[idx],s=states.get(p);
  if(!s||s.marker477===0||isStart!==true)return normalInjury(idx,isStart);
  nonnegative(p.internal_injury,'invalid_internal_injury');
  if(p.internal_injury===0)return normalInjury(idx,isStart);
  check(p.resonance_indomitable_will_stacks===0,'selected_resonance_not_supported');
  nonnegative(p.m_endless_entanglement_stacks,'invalid_injury_repeats');
  const base=p.internal_injury,amount=base*2;nonnegative(amount,'internal_injury_overflow');
  // Preserve native repetition/consumption and ordinary HP callbacks. Only the
  // direct calls of this tick are multiplied; nested callback damage is not.
  const previous=this.reduce_idx_hp;let direct=true;
  this.reduce_idx_hp=function(target,n,...rest){
   if(!direct)return previous.call(this,target,n,...rest);
   check(target===idx&&n===base,'unexpected_internal_injury_call');
   const before=p.hp;direct=false;
   try{return previous.call(this,target,amount,...rest);}
   finally{direct=true;emit(p,7135,'turn_start_internal_injury',{buff_id:100,marker477:s.marker477,base:n,requested:amount,before,after:p.hp});}
  };
  try{return normalInjury(idx,isStart);}finally{this.reduce_idx_hp=previous;}
 };
 installed.add(game);
 return {
  installOpening(id){
   check([7103,7135].includes(id)&&!boundaries.has(id),'duplicate_or_unknown_boundary');boundaries.add(id);
   const previous=game.do_plant_start_permanent_buffs.bind(game);
   game.do_plant_start_permanent_buffs=function(...args){
    check(boundaries.size===2,'incomplete_opening_boundaries');
    const p=this.players[0],s=states.get(p),entry=s.entries.get(id);
    if(entry){
     check(!s.opened.has(id),'opening_repeated');
     if(id===7103){
      check(Number.isSafeInteger(p.hp)&&p.hp>0&&p.hp<=2147483647,'opening_hp_outside_supported_range');
      const before={hp:p.hp,max_hp:p.max_hp},amount=Math.trunc(p.hp/10);s.opened.add(id);
      this.increase_idx_max_hp(0,amount);this.increase_idx_hp(0,amount);
      emit(p,id,'season_opening_before7105',{before,requested:amount,after:{hp:p.hp,max_hp:p.max_hp}});
     }else{
      s.opened.add(id);const before=this.players.map(q=>states.get(q).marker477);
      if(entry.enabled)for(const q of this.players)states.get(q).marker477+=1;
      emit(p,id,'season_opening_before11002',{enabled:entry.enabled,target_order:this.players.map(q=>states.get(q).index),before,after:this.players.map(q=>states.get(q).marker477)});
     }
    }
    return previous(...args);
   };
  },
  metadata:()=>({evidence_sha256:digest,events:structuredClone(events),training_label_allowed:false})
 };
}
