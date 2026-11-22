import {applyCurrentFanQiDamage} from './current_fan_qi_v60.mjs';
// Current seasonal startup and positive-Qi callbacks. Frozen nonowners delegate.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='9c8ab01d4ce43fdbc344d315d512b55c03a935ef0ae591731b98ed2cd431e18a',installed=new WeakSet();
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const check=(v,m)=>{if(!v)throw new Error('opening_qi_unresolved:'+m);};
export function createOpeningQi(root,game,value,order=[0,1]) {
 if(value===undefined)return null;
 check(object(value)&&Object.keys(value).length===1&&Array.isArray(value.players)&&value.players.length===2,'explicit_players_required');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 check(value.players.every(a=>Array.isArray(a)&&new Set(a).size===a.length&&a.every(id=>[7005,7059,7109].includes(id))),'invalid_ownership');
 check(value.players.some(a=>a.length),'empty_ownership');check(!installed.has(game),'already_installed');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-opening-qi-v56.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');const facts=JSON.parse(raw);
 for(const [p,h] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 const states=new Map(game.players.map((p,i)=>[p,{index:order[i],ids:new Set(value.players[order[i]]),opened:new Set(),wings:0,wine:0}]));
 const events=[],boundaries=new Set();
 const snapshot=p=>({qi:p.qi,hp:p.hp,max_hp:p.max_hp,agility:p.agility,physique:p.physique,
  cloud_chain:p.cloud_sword_chain_count,cloud_used:p.cloud_sword_used_count,cloud_sea:p.cloud_sea});
 const emit=(p,id,phase,extra={})=>{const e={strategy_id:id,player_index:states.get(p).index,phase,...extra};events.push(e);return e;};
 // Installed before the fixed v7 current-cap wrapper and3011 Qi bonus. The
 // copied native body retains its five-point threshold; v7 supplies the offset.
 const native=game.increase_idx_qi.bind(game);
 game.increase_idx_qi=function(idx,amount){
  const p=this.players[idx],s=states.get(p);check(s!==undefined,'invalid_target');
  if(!s.ids.has(7059)&&!s.ids.has(7109))return native(idx,amount);
  check(Number.isSafeInteger(amount)&&amount>=0&&amount<=2147483647,'nonnegative_int32_gain_required');
  return currentGain.call(this,idx,amount,()=>{
   if(s.wine>0){
    s.wine--;const e=emit(p,7109,'positive_qi_after_earlier_callbacks_before267',{remaining:s.wine,before:snapshot(p)});
    // Client767 consumes before both requests, then reads legacy407 parameter0.
    this.increase_idx_max_hp(idx,facts.effects['7109'].heal);
    this.increase_idx_hp(idx,facts.effects['7109'].heal);e.after=snapshot(p);
   }
  },()=>{
   if(s.wings>0){
    const amount=s.wings;s.wings=0;const e=emit(p,7059,'positive_qi_after267',{amount,before:snapshot(p)});
    this.increase_idx_x_by_c(idx,'agility',amount);e.after=snapshot(p);
   }
  });
 };
 installed.add(game);
 return {
  installBoundary(id){
   check([7005,7059,7109].includes(id)&&!boundaries.has(id),'duplicate_or_unknown_boundary');boundaries.add(id);
   const previous=game.do_plant_start_permanent_buffs.bind(game);
   game.do_plant_start_permanent_buffs=function(...args){
    check(boundaries.size===3,'incomplete_boundary_installation');
    const p=this.players[0],s=states.get(p);
    if(s.ids.has(id)&&!s.opened.has(id)){
     s.opened.add(id);const e=emit(p,id,'owner_season_start',{before:snapshot(p)});
     if(id===7005){
      const n=facts.effects['7005'].chain;
      p.cloud_sword_chain_count+=n;p.cloud_sword_used_count+=n;
      this.increase_idx_x_by_c(0,'cloud_sea',facts.effects['7005'].sea);
     }else if(id===7059)s.wings=facts.effects['7059'].agility;
     else s.wine=facts.effects['7109'].charges;
     e.after=snapshot(p);e.pending={wings:s.wings,wine:s.wine};
    }
    return previous(...args);
   };
  },
  metadata:()=>({evidence_sha256:digest,events:structuredClone(events),
   remaining:[...states.values()].map(s=>({player_index:s.index,wings:s.wings,wine:s.wine,opened:[...s.opened]})),
   acquisition_rewards_reapplied:false,training_label_allowed:false})
 };
}

// Generated below from the pinned native body, changing only the267 position
// and adding767/751 at the source-established boundaries. No eval is used.
function currentGain(idx, amt, before267, after267) {
        if (amt === 0) {
            return;
        }
        const me = this.players[idx];
        if (me.mixed_grain_zongzi_stacks > 0) {
            amt += 1;
            this.increase_idx_hp(idx, me.mixed_grain_zongzi_stacks);
        }
        if (me.colorful_spirit_crane_stacks > 0) {
            amt *= 2;
        }
        if (me.dream_nine_evil_ruptsprite_stacks > 0) {
            amt = Math.floor(amt / 2);
            if (amt === 0) {
                return;
            }
        }
        if (me.mortal_body_stacks > 0) {
            this.increase_idx_physique(idx, amt);
            return;
        }
        if (me.m_dotted_around_stacks > 0) {
            const star_power_amt = Math.min(amt, me.m_dotted_around_stacks);
            this.increase_idx_star_power(idx, star_power_amt);
            this.reduce_idx_x_by_c(idx, "m_dotted_around_stacks", star_power_amt);
        }
        me.qi += amt;
        me.total_qi_gained += amt;
        this.log("gained " + amt + " qi. Now have " + me.qi + " qi");

        if (me.stillness_citta_dharma_stacks > 0) {
            this.increase_idx_hp(idx, amt * me.stillness_citta_dharma_stacks);
        }
        if (me.spiritstat_tune_stacks > 0) {
            this.increase_idx_x_by_c(idx, "def", amt * me.spiritstat_tune_stacks);
        }
        if (me.spirit_command_citta_dharma_qi_gain_def_stacks > 0) {
            this.increase_idx_def(idx, amt * me.spirit_command_citta_dharma_qi_gain_def_stacks);
        }
        if (me.dream_yin_yang_formation_hp_stacks > 0) {
            this.increase_idx_hp(idx, amt * me.dream_yin_yang_formation_hp_stacks);
        }
        if (me.dream_yin_yang_formation_def_stacks > 0) {
            this.increase_idx_def(idx, amt * me.dream_yin_yang_formation_def_stacks);
        }
        if (me.dream_consonance_qi_gives_def_stacks > 0) {
            this.increase_idx_def(idx, amt * me.dream_consonance_qi_gives_def_stacks);
        }
        if (me.spiritual_divination_stacks > 0) {
            const hexagram_amt = amt * me.spiritual_divination_stacks;
            this.increase_idx_hexagram(idx, hexagram_amt);
        }
        applyCurrentFanQiDamage(this,idx,amt);
        if (me.wild_crossing_seal_stacks > 0 && idx === 0) {
            this.do_wild_crossing_seal_chase();
        }
        if (me.spirit_hexagram_evolves_stacks > 0) {
            me.spirit_hexagram_evolves_triggered = true;
        }
        before267();
        if (me.wind_spirit_forging_stacks > 0 && me.wind_spirit_forging_gained < 5) {
            const physique_amt = Math.min(amt, 5 - me.wind_spirit_forging_gained);
            me.wind_spirit_forging_gained += physique_amt;
            this.increase_idx_physique(idx, physique_amt);
        }
        after267();
}
