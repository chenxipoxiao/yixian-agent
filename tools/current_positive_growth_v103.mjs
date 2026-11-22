import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {requireHealingPolicy} from './current_healing_policy_v83.mjs';
const check=(v,m)=>{if(!v)throw new Error('positive_growth_unresolved:'+m);};
const installed=new WeakSet();
export function installPositiveGrowth(root,game,value,order=[0,1]) {
 if(value===undefined)return null;
 requireHealingPolicy(root);
 check(value&&Object.keys(value).length===1&&Array.isArray(value.players)&&value.players.length===2&&value.players.every(x=>typeof x==='boolean')&&value.players.some(Boolean),'explicit_ownership');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'order');
 check(!installed.has(game),'duplicate_install');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-positive-growth-v103.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')==='f2851ebda4cf6b3405bcd3a27aa74ce241629d10ccdefa7fdfa3fe9c9fa6ce71','evidence_changed');
 const facts=JSON.parse(raw);
 check(facts.strategy_id===7076&&facts.bonus===1&&facts.conform_percent===40,'invalid_facts');
 for(const [n,h] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,n))).digest('hex')===h,'source_changed:'+n);
 const states=new Map(game.players.map((p,i)=>[p,{owned:value.players[order[i]],index:order[i]}])),events=[];
 const owned=p=>states.get(p)?.owned;
 const emit=(p,kind,extra)=>events.push({kind,player_index:states.get(p).index,...extra});
 const integer=n=>check(Number.isSafeInteger(n)&&n>=0&&n<=2147483647,'nonnegative_int32');
 const conform=(p,n)=>{
  integer(n);
  if(p.god_opportunity_conform_stacks>0){check(n*40<=2147483647,'percentage_int32_overflow');n+=Math.ceil(Math.fround(Math.fround(n*40)/Math.fround(100)));}
  integer(n);return n;
 };
 const maxHp=game.increase_idx_max_hp.bind(game);
 game.increase_idx_max_hp=function(idx,n){
  const p=this.players[idx];if(!owned(p))return maxHp(idx,n);
  integer(n);if(n===0)return maxHp(idx,n);
  const actual=conform(p,n+1),before=p.max_hp;integer(before+actual);
  p.max_hp+=actual;this.log('gained '+actual+' max_hp. Now have '+p.max_hp);
  emit(p,'positive_max_hp',{requested:n,bonus:1,actual,before,after:p.max_hp});
 };
 let attached=false;
 installed.add(game);
 return {
  attachHealing(spiritOutburst){
   check(!attached&&spiritOutburst&&typeof spiritOutburst.forPlayer==='function','healing_attachment');
   const heal=game.increase_idx_hp.bind(game);
   game.increase_idx_hp=function(idx,n){
    const p=this.players[idx];if(!owned(p))return heal(idx,n);
    integer(n);if(n===0)return 0;
    // Client268/612 and577 execute before7076,392/393,371 and120.
    if(p.prevent_gain_hp_stacks>0||p.got_void_split_speared&&p.hp<=0||p.metal_spirit_chokehold_stacks>0)return 0;
    if(p.m_metal_spirit_seal_stacks>0){this.increase_idx_penetrate(idx,n);emit(p,'heal_converted_before_bonus',{requested:n,bonus:0});return 0;}
    let amount=Math.max(1,n+1+p.appetite-p.indigestion);amount=conform(p,amount);
    const e={requested:n,bonus:1,adjusted:amount,before:{hp:p.hp,max_hp:p.max_hp}};
    emit(p,'positive_healing',e);const event=events[events.length-1];
    // One client call for the sum, so7076's maxHP bonus fires once.
    const rejuvenation=3*p.p2_rejuvenation_stacks+4*p.p3_rejuvenation_stacks+5*p.p4_rejuvenation_stacks+6*p.p5_rejuvenation_stacks;
    if(rejuvenation>0)this.increase_idx_max_hp(idx,rejuvenation);
    if(p.wild_crossing_seal_stacks>0&&idx===0)this.do_wild_crossing_seal_chase();
    const beforeHp=p.hp;check(Number.isSafeInteger(beforeHp+amount)&&beforeHp+amount<=2147483647,'hp_overflow');
    p.hp+=amount;p.hp_gained+=amount;p.hp_gained_this_turn+=amount;
    let overflow=0;
    if(p.hp>p.max_hp){
     if(p.vitality_blossom_stacks>0)this.increase_idx_max_hp(idx,p.hp-p.max_hp);
     else overflow=p.hp-p.max_hp;
     if(p.hp>p.max_hp)p.hp=p.max_hp;
    }
    if(p.hp!==beforeHp)for(let i=0;i<p.birdie_wind_stacks;i++)this.increase_idx_def(idx,1);
    this.log('healed '+amount+' hp. Went from '+beforeHp+' to '+p.hp);
    if(p.god_opportunity_reversal_stacks>0){const damage=Math.floor(amount/2);if(damage>0)this.deal_damage_inner(damage,false,idx);}
    if(overflow>0&&spiritOutburst.forPlayer(p).remaining>0)this.current_spirit_outburst_damage(idx,overflow);
    if(p.dream_standing_firm_def_hp_damage_pct>0&&!p.dream_standing_firm_triggering){
     p.dream_standing_firm_triggering=1;const damage=Math.floor(amount*p.dream_standing_firm_def_hp_damage_pct/100);
     if(damage>0)this.deal_damage_inner(damage,false,idx);p.dream_standing_firm_triggering=0;
    }
    event.after={hp:p.hp,max_hp:p.max_hp};event.overflow=overflow;
   };
   attached=true;
  },
  metadata:()=>({strategy_id:7076,events:structuredClone(events),opening_hp_preadded:false,acquisition_rewards_reapplied:false,training_label_allowed:false})
 };
}
