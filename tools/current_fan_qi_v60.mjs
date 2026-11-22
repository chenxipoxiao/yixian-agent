// Source-anchored fan Qi damage at the original callback, in both gain paths.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='d22785980cc144b9a43e6f13318c6e3523081cc06beee8ef88c3c401a2460512',installed=new WeakMap();
const check=(v,m)=>{if(!v)throw new Error('fan_qi_unresolved:'+m);};
const snapshot=p=>({hp:p.hp,def:p.def,guard_up:p.guard_up});
export function applyCurrentFanQiDamage(game,idx,amount) {
 const me=game.players[idx];
 if(!(me.star_moon_hexagram_fan_stacks>0))return;
 const state=installed.get(game),stacks=me.star_moon_hexagram_fan_stacks;
 check(state!==undefined,'installer_required');
 check(Number.isSafeInteger(amount)&&amount>0&&Number.isSafeInteger(stacks)&&stacks>0&&amount*stacks<=2147483647,'positive_int32_product_required');
 const target=game.players[1-idx],damage=amount*stacks;
 const event={player_index:state.indices.get(me),target_index:state.indices.get(target),qi_delta:amount,stacks,damage,before:snapshot(target)};
 state.events.push(event);
 game.deal_damage_inner(damage,false,idx);
 event.after=snapshot(target);
}
export function installCurrentFanQi(root,game,order=[0,1]) {
 check(!installed.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-fan-qi-v60.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');
 for(const [p,h] of Object.entries(JSON.parse(raw).source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 const state={indices:new Map(game.players.map((p,i)=>[p,order[i]])),events:[]};installed.set(game,state);
 game.increase_idx_qi=currentGain;
 return {metadata:()=>state.events.length?{evidence_sha256:digest,events:structuredClone(state.events),training_label_allowed:false}:null};
}
// Generated from the pinned native body; only the fan callback is replaced.
function currentGain(idx, amt) {
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
        if (me.wind_spirit_forging_stacks > 0 && me.wind_spirit_forging_gained < 5) {
            const physique_amt = Math.min(amt, 5 - me.wind_spirit_forging_gained);
            me.wind_spirit_forging_gained += physique_amt;
            this.increase_idx_physique(idx, physique_amt);
        }
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
    }
