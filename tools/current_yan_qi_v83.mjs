import {requireHealingPolicy} from './current_healing_policy_v83.mjs';
//7053 arms one744 at the owner's seasonal opening. Actual recovery or a
// positive maxHP change consumes it before recursively requesting healing.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='8d757956598ee76cfb4b6dde23213d6d34b81b74b284bff02f27a69cd4791636';
const installed=new WeakSet();
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const check=(v,m)=>{if(!v)throw new Error('yan_qi_unresolved:'+m);};
const gain=v=>check(Number.isSafeInteger(v)&&v>=0&&v<=2147483647,'nonnegative_int32_gain_required');

export function installYanQi(root,game,value,order=[0,1]) {
 if(value===undefined)return null;
 requireHealingPolicy(root);
 check(object(value)&&Object.keys(value).length===1&&Array.isArray(value.players)&&value.players.length===2
  &&value.players.every(e=>e===null||object(e)&&Object.keys(e).length===1&&e.strategy_id===7053),'explicit_ownership_required');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 check(!installed.has(game),'already_installed');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-yan-qi-v42.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');
 const facts=JSON.parse(raw);
 for(const [p,h] of Object.entries(facts.source_sha256))
  check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 check(value.players.some(e=>e!==null),'owner_required');
 const states=new Map(game.players.map((p,i)=>[p,{index:order[i],owned:value.players[order[i]]!==null,opened:false,remaining:0}]));
 const events=[];let attached=false;
 const plants=game.do_plant_start_permanent_buffs.bind(game);
 // Install after7069 and before3011: seasonal wrappers execute outside-in.
 game.do_plant_start_permanent_buffs=function(...args) {
  check(attached,'healing_adapter_not_attached');
  const s=states.get(this.players[0]);
  if(s.owned&&!s.opened){s.opened=true;s.remaining=facts.pending_uses;events.push({kind:'owner_season_start',player_index:s.index,client_buff:744,remaining:s.remaining});}
  return plants(...args);
 };
 const trigger=(idx,kind,positive)=>{
  const p=game.players[idx],s=states.get(p);
  if(!s.remaining||positive<=0)return;
  check(Number.isSafeInteger(p.max_hp)&&p.max_hp>=0&&p.max_hp*facts.healing_percent<=2147483647,'int32_percentage_overflow');
  const amount=Math.trunc(p.max_hp*facts.healing_percent/100);
  s.remaining=0;
  const e={kind,player_index:s.index,trigger_value:positive,requested_bonus:amount,
   before:{hp:p.hp,max_hp:p.max_hp},remaining:0,consumed_before_callbacks:true};events.push(e);
  //744 is consumed before recovery; OpenConfig74 permits nonpositive HP.
  game.increase_idx_hp(idx,amount);
  e.after={hp:p.hp,max_hp:p.max_hp};
 };
 const maxHp=game.increase_idx_max_hp.bind(game);
 game.increase_idx_max_hp=function(idx,amount) {
  const s=states.get(this.players[idx]);check(s!==undefined,'invalid_target');
  if(!s.remaining)return maxHp(idx,amount);
  gain(amount);
  const result=maxHp(idx,amount);
  trigger(idx,'positive_max_hp',amount);
  return result;
 };
 installed.add(game);
 return {
  // Attach after787's wrapper, preserving its independent remaining state and
  // placing744 before373/787/716, rather than after the whole healing call.
  attachHealing(spiritOutburst) {
   check(!attached,'healing_already_attached');
   check(spiritOutburst&&typeof spiritOutburst.forPlayer==='function','spirit_outburst_state_required');
   const heal=game.increase_idx_hp.bind(game);
   game.increase_idx_hp=function(idx,amount) {
    const s=states.get(this.players[idx]);check(s!==undefined,'invalid_target');
    if(!s.remaining)return heal(idx,amount);
    gain(amount);
    return healWithYanQi.call(this,idx,amount,trigger,spiritOutburst);
   };
   attached=true;
  },
  metadata:()=>({evidence_sha256:digest,events:structuredClone(events),
   remaining:[...states.values()].map(s=>({player_index:s.index,owned:s.owned,opened:s.opened,pending_uses:s.remaining})),
   acquisition_rewards_reapplied:false,training_label_allowed:false})
 };
}

function healWithYanQi(idx,amt,trigger,spiritOutburst) {
 const me=this.players[idx];
 if(amt===0)return 0;
 amt=Math.max(1,amt-me.indigestion+me.appetite);
 if(me.prevent_gain_hp_stacks>0||me.got_void_split_speared&&me.hp<=0||me.metal_spirit_chokehold_stacks>0)return 0;
 if(me.m_metal_spirit_seal_stacks>0){this.increase_idx_penetrate(idx,amt);return 0;}
 // OpenConfig74 is enabled; keep612/anti-heal/conversion checks above.
 if(me.god_opportunity_conform_stacks>0)amt=Math.ceil(amt*14/10);
 // Client sums all four talent120 tiers into one ModifyMaxHp call (0x480–4c9).
 const rejuvenation=3*me.p2_rejuvenation_stacks+4*me.p3_rejuvenation_stacks+5*me.p4_rejuvenation_stacks+6*me.p5_rejuvenation_stacks;
 if(rejuvenation>0)this.increase_idx_max_hp(idx,rejuvenation);
 if(me.wild_crossing_seal_stacks>0&&idx===0)this.do_wild_crossing_seal_chase();
 const prevHp=me.hp;
 me.hp+=amt;me.hp_gained+=amt;me.hp_gained_this_turn+=amt;
 let overflow=0;
 if(me.hp>me.max_hp) {
  if(me.vitality_blossom_stacks>0)this.increase_idx_max_hp(idx,me.hp-me.max_hp);
  else overflow=me.hp-me.max_hp;
  if(me.hp>me.max_hp)me.hp=me.max_hp;
 }
 const actual=amt-overflow;
 if(actual!==0)for(let i=0;i<me.birdie_wind_stacks;i++)this.increase_idx_def(idx,1);
 this.log('healed '+amt+' hp. Went from '+prevHp+' to '+me.hp);
 trigger(idx,'positive_actual_healing',actual);
 if(me.god_opportunity_reversal_stacks>0) {
  const damage=Math.floor(amt/2);if(damage>0)this.deal_damage_inner(damage,false,idx);
 }
 if(overflow>0&&spiritOutburst.forPlayer(me).remaining>0)this.current_spirit_outburst_damage(idx,overflow);
 if(me.dream_standing_firm_def_hp_damage_pct>0&&!me.dream_standing_firm_triggering) {
  me.dream_standing_firm_triggering=1;
  const damage=Math.floor(amt*me.dream_standing_firm_def_hp_damage_pct/100);
  if(damage>0)this.deal_damage_inner(damage,false,idx);
  me.dream_standing_firm_triggering=0;
 }
}
