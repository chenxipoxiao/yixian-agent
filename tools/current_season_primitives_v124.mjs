// Versioned native bodies with source-positioned optional season callbacks.
import {swogi,FIST_STANCE,STICK_STANCE} from '../external/yisim/card_info.js';
const is_debuff=x=>["internal_injury","decrease_atk","weaken","flaw","entangle","wound","styx","indigestion"].includes(x);
const is_activate=x=>["wood","fire","earth","metal","water"].some(e=>x==="activate_"+e+"_spirit_stacks");
export function installSeasonPrimitives(game){
game.increase_idx_force=function(idx, amt) {
        if (amt === 0) {
            return;
        }
        const me = this.players[idx];
        amt=this.currentSeasonForceGain?.(idx,amt)??amt;
        me.force += amt;
        if (me.resonance_full_of_force_stacks > 0 &&
            me.force > me.max_force) {
            me.max_force += 1;
        }
        if (me.force > me.max_force) {
            const excess_amt = me.force - me.max_force;
            me.force = me.max_force;
            this.increase_idx_def(idx, excess_amt);
            if (me.overwhelming_power_stacks > 0) {
                const dmg = me.overwhelming_power_stacks * excess_amt;
                this.deal_damage_inner(dmg, false, idx);
            }
        }
        me.total_force_gained += amt;
        if (me.surge_of_qi_stacks > 0 && me.stance === FIST_STANCE && !me.surge_of_qi_gain_agility_triggered) {
            me.surge_of_qi_gain_agility_triggered = true;
            this.increase_idx_x_by_c(idx, "agility", 2);
        }
        this.log("gained " + amt + " force. Now have " + me.force + " force");
    };
game.increase_idx_physique=function(idx, amt) {
        if (amt === 0) {
            return;
        }
        const me = this.players[idx];
        const prev = me.physique;
        me.physique += amt;
        me.physique_gained += amt;
        this.log("gained " + amt + " physique. Now have " + me.physique + " physique");
        if (me.mind_body_resonance_stacks > 0) {
            this.increase_idx_def(idx, Math.min(amt, 5));
        }
        this.currentSeasonPhysiqueGain?.(idx,amt);
        this.increase_idx_max_hp(idx, amt);
        if (me.m_exercise_bones_heal_stacks > 0) {
            this.increase_idx_hp(idx, amt * me.m_exercise_bones_heal_stacks);
        }
        if (me.max_physique < me.physique) {
            if (me.m_exercise_bones_damage_stacks > 0) {
                this.deal_damage(amt * me.m_exercise_bones_damage_stacks, false, idx);
            }
            let heal_amt = amt;
            if (prev < me.max_physique) {
                heal_amt -= me.max_physique - prev;
            }
            if (me.resonance_firmness_body_stacks > 0) {
                heal_amt *= 2;
            }
            this.increase_idx_hp(idx, heal_amt);
        }
    };
game.increase_idx_hexagram=function(idx, amt) {
        if (amt === 0) {
            return;
        }
        const me = this.players[idx];
        amt=this.currentSeasonHexagramGain?.(idx,amt)??amt;
        me.hexagram += amt;
        if (me.astrology_stacks > 0 && me.star_power === 0) {
            this.increase_idx_star_power(idx, 1);
        }
        if (me.hexagram_formacide_stacks > 0) {
            const dmg = amt * me.hexagram_formacide_stacks;
            this.deal_damage_inner(dmg, false, idx);
        }
        if (me.dream_yin_yang_formation_hp_stacks > 0) {
            this.increase_idx_hp(idx, amt * me.dream_yin_yang_formation_hp_stacks);
        }
        if (me.dream_yin_yang_formation_def_stacks > 0) {
            this.increase_idx_def(idx, amt * me.dream_yin_yang_formation_def_stacks);
        }
        if (me.star_moon_hexagram_fan_stacks > 0) {
            const dmg = amt * me.star_moon_hexagram_fan_stacks;
            this.deal_damage_inner(dmg, false, idx);
        }
        this.log("gained " + amt + " hexagram. Now have " + me.hexagram + " hexagram");
    };
game.increase_idx_star_power=function(idx, amt) {
        if (amt === 0) {
            return;
        }
        const me = this.players[idx];
        if(this.currentSeasonConvertStar?.(idx,amt))return;
        me.star_power += amt;
        if (me.star_moon_hexagram_fan_stacks > 0) {
            const dmg = amt * me.star_moon_hexagram_fan_stacks;
            this.deal_damage_inner(dmg, false, idx);
        }
        this.log("gained " + amt + " star_power. Now have " + me.star_power + " star_power");
    };
game.increase_idx_activate=function(idx, x, amt) {
        if (amt === 0) {
            return;
        }
        const me = this.players[idx];
        let can_uwf = true;
        if (me.predicament_for_immortals_stacks > 0
            && me.prevent_anti_chase === 0 && !this.currentSeasonBatchHas?.(me,28001)
        ) {
            can_uwf = false;
        }
        if (can_uwf && me.ultimate_world_formation_stacks > 0 && idx === 0
            && me.this_card_chases === 0
            && me.chases < me.max_chases) {
            this.reduce_idx_x_by_c(0, "ultimate_world_formation_stacks", 1);
            this.chase();
        }
        for (let i=0; i < me.five_elements_explosion_stacks; i++) {
            const enemy_idx = 1 - idx;
            this.reduce_idx_hp(enemy_idx, 3, false);
            this.reduce_idx_max_hp(enemy_idx, 3);
        }
        if (me.seal_suppression_citta_dharma_stacks > 0) {
            this.deal_damage(me.seal_suppression_citta_dharma_stacks);
        }
        const prev_amt = me[x];
        if (prev_amt === 0 && me.five_elements_anima_stacks > 0) {
            const enemy_idx = 1 - idx;
            switch (x) {
                case "activate_wood_spirit_stacks":
                    this.increase_idx_x_by_c(idx, "increase_atk", 1);
                    break;
                case "activate_fire_spirit_stacks":
                    this.reduce_idx_hp(enemy_idx, 7, false);
                    this.reduce_idx_max_hp(enemy_idx, 7);
                    break;
                case "activate_earth_spirit_stacks":
                    this.increase_idx_def(idx, 12);
                    break;
                case "activate_metal_spirit_stacks":
                    this.increase_idx_penetrate(idx, 4);
                    break;
                case "activate_water_spirit_stacks":
                    this.increase_idx_x_by_c(idx, "force_of_water", 2);
                    break;
            }
        }
        if (me.herbs_flourish_stacks > 0) {
            if (x === "activate_wood_spirit_stacks") {
                this.increase_idx_max_hp(idx, 2);
            }
        }
        if (me.five_elements_gather_qi_stacks > 0) {
            let gather_qi_flag = null;
            if (x === "activate_wood_spirit_stacks") gather_qi_flag = "five_elements_gather_qi_wood";
            else if (x === "activate_fire_spirit_stacks") gather_qi_flag = "five_elements_gather_qi_fire";
            else if (x === "activate_earth_spirit_stacks") gather_qi_flag = "five_elements_gather_qi_earth";
            else if (x === "activate_metal_spirit_stacks") gather_qi_flag = "five_elements_gather_qi_metal";
            else if (x === "activate_water_spirit_stacks") gather_qi_flag = "five_elements_gather_qi_water";
            if (me[gather_qi_flag] > 0) {
                me[gather_qi_flag] = 0;
                this.increase_idx_qi(idx, me.five_elements_gather_qi_stacks);
            }
        }
        me[x] += amt;
        this.currentSeasonReactivation?.(idx,x,amt);
        this.log("gained " + amt + " " + x + ". Now have " + me[x] + " " + x);
    };
game.increase_idx_x_by_c=function(idx, x, c) {
        if (c === 0) {
            return;
        }
        const me = this.players[idx];
        if (c < 0) {
            this.log("error: c is negative: " + c);
            this.crash();
        }
        if (x === "hp") {
            return this.increase_idx_hp(idx, c);
        }
        if (x === "max_hp") {
            return this.increase_idx_max_hp(idx, c);
        }
        if (x === "def") {
            return this.increase_idx_def(idx, c);
        }
        if (x === "qi") {
            return this.increase_idx_qi(idx, c);
        }
        if (x === "force") {
            return this.increase_idx_force(idx, c);
        }
        if (x === "penetrate") {
            return this.increase_idx_penetrate(idx, c);
        }
        if (x === "physique") {
            return this.increase_idx_physique(idx, c);
        }
        if (is_activate(x)) {
            return this.increase_idx_activate(idx, x, c);
        }
        if (x === "hexagram") {
            return this.increase_idx_hexagram(idx, c);
        }
        if (x === "star_power") {
            return this.increase_idx_star_power(idx, c);
        }
        if (is_debuff(x)) {
            return this.increase_idx_debuff(idx, x, c);
        }
        if (x === "sword_intent" && me.dream_consonance_sword_intent_gives_def_stacks > 0) {
            this.increase_idx_def(idx, c * me.dream_consonance_sword_intent_gives_def_stacks);
        }
        if (x === "increase_atk" && me.convert_increase_atk_to_wood_thorn > 0) {
            const convert = Math.min(c, me.convert_increase_atk_to_wood_thorn);
            me.wood_thorn += convert;
            c -= convert;
            this.log("converted " + convert + " increase_atk to wood_thorn. Now have " + me.wood_thorn + " wood_thorn");
        }
        me[x] += c;
        this.currentSeasonBuffAdded?.(idx,x,c);
        if (x === "force_of_water") {
            me.total_force_of_water_gained += c;
        }
        this.log("gained " + c + " " + x + ". Now have " + me[x] + " " + x);
    };
game.reduce_idx_x_by_c=function(idx, x, c) {
        if (c === 0) {
            return;
        }
        const me = this.players[idx];
        if (x === "hp") {
            return this.reduce_idx_hp(idx, c, false);
        }
        if (x === "def") {
            return this.reduce_idx_def(idx, c);
        }
        if (x === "max_hp") {
            return this.reduce_idx_max_hp(idx, c);
        }
        if (x === "qi") {
            return this.reduce_idx_qi(idx, c);
        }
        if (x === "hexagram") {
            return this.reduce_idx_hexagram(idx, c);
        }
        if (x === "force") {
            return this.reduce_idx_force(idx, c);
        }
        if (x === "styx") {
            c = Math.min(c, me.styx);
            if ((me.character === "dx3" || this.currentSeasonStyxHeals?.(me))) {
                this.increase_idx_hp(idx, c * 3);
            } else {
                this.reduce_idx_hp(idx, c * 3, false);
            }
        }
        if (c < 0) {
            this.log("error: c is negative: " + c);
            this.crash();
        }
        const prev_x = me[x];
        me[x] -= c;
        if (me[x] < 0) {
            me[x] = 0;
        }
        if (x === "destiny") {
            me.direct_destiny_lost += prev_x - me[x];
        }
        if (idx === 0 && is_debuff(x)) {
            me.total_debuff_lost += prev_x - me[x];
        }
        if (x === "flaw" && prev_x > me[x] && me.drunken_fist_stance_stacks > 0) {
            this.increase_idx_x_by_c(idx, "increase_atk", (prev_x - me[x]) * me.drunken_fist_stance_stacks);
        }
        if (prev_x !== me[x] || c !== 1) {
            this.log("lost " + c + " " + x + ". Now have " + me[x] + " " + x);
        }
    };
game.increase_idx_def=function(idx, amt) {
        const me = this.players[idx];
        if (amt === 0) {
            return;
        }
        if (me.prevent_gain_def_stacks > 0) {
            this.log("prevented " + amt + " def gain");
            return;
        }
        amt += me.kun_wu_metal_ring_stacks;
        amt += me.kun_wu_molten_ring_stacks;
        amt=this.currentSeasonDefGain?.(idx,amt)??amt;
        if (me.god_opportunity_conform_stacks > 0) {
            amt = Math.ceil(amt * 14 / 10);
        }
        me.def += amt;
        this.log("gained " + amt + " def. Now have " + me.def + " def");
        if (me.god_opportunity_reversal_stacks > 0) {
            const dmg_amt = Math.floor(amt / 2);
            if (dmg_amt > 0) {
                this.deal_damage_inner(dmg_amt, false, idx);
            }
        }
        if (me.dream_standing_firm_def_hp_damage_pct > 0 && !me.dream_standing_firm_triggering) {
            me.dream_standing_firm_triggering = 1;
            const dmg = Math.floor(amt * me.dream_standing_firm_def_hp_damage_pct / 100);
            if (dmg > 0) {
                this.deal_damage_inner(dmg, false, idx);
            }
            me.dream_standing_firm_triggering = 0;
        }
        if (me.dream_standing_firm_def_damage > 0) {
            this.deal_damage_inner(me.dream_standing_firm_def_damage, false, idx);
        }
        me.total_def_gained += amt;
    };
game.atk=function(dmg, is_extra, this_atk_smash_def) {
        this.currentSeasonBeforeAttack?.(0);
        this.do_drift_ice_blade();
        const me = this.players[0];
        me.attack_count += 1;
        const enemy = this.players[1];
        if (me.throw_petals_stacks > 0) {
            const amt = me.throw_petals_stacks;
            this.increase_idx_debuff(1, "internal_injury", amt);
        }
        if (enemy.throw_petals_stacks > 0) {
            const amt = enemy.throw_petals_stacks;
            this.increase_idx_debuff(0, "internal_injury", amt);
        }
        if (me.face_isolation_stacks > 0) {
            this.increase_idx_debuff(0, "weaken", 1);
            me.face_isolation_stacks -= 1;
        }
        if (enemy.strike_vacuity_stacks > 0) {
            this.increase_idx_debuff(1, "flaw", 1);
            enemy.strike_vacuity_stacks -= 1;
        }
        this.do_fire_flame_blade();
        this.deal_damage_inner(dmg, true, 0, is_extra, this_atk_smash_def);
        if (enemy.counter_move_stacks > 0 &&
            enemy.stance === STICK_STANCE) {
            this.deal_damage_inner(6, false, 1);
        }
    };
game.do_sword_qi=function(card_id) {
        const me = this.players[0];
        if (me.sword_qi <= 0) {
            return;
        }
        let triggers = false;
        triggers |= this.is_sword(card_id) && this.has_dharma_spirit_sword_in_deck();
        triggers |= this.is_spirit_sword(card_id);
        triggers |= !!this.currentSeasonSwordQiQualifies?.(card_id);
        if (triggers) {
            this.log("Dealing " + me.sword_qi + " damage from sword qi.");
            this.deal_damage(me.sword_qi);
        }
    };
game.do_cloud_sword_chain_count=function(card_id) {
        const me = this.players[0];
        // if this card has "Cloud Sword" in the name, increment cloud_sword_chain_count
        if (this.is_cloud_sword(card_id)) {
            me.cloud_sword_chain_count += 1;
            me.cloud_sword_used_count += 1;
            this.do_step_moon_into_cloud(card_id);
        } else {
            if (me.cloud_sea > 0) {
                me.cloud_sea -= 1;
                me.cloud_sword_chain_count += 1;
                this.log("consumed 1 cloud_sea, incremented cloud_sword_chain_count to " + me.cloud_sword_chain_count);
                me.cloud_sword_used_count += 1;
                this.currentSeasonCloudSeaConsumed?.();
            } else
            if (me.endurance_as_cloud_sea_stacks > 0) {
            } else
            if (me.cloud_sword_chain_count > 0) {
                me.cloud_sword_chain_count = 0;
            }
        }
    };
game.process_this_card_chases=function() {
        const me = this.players[0];
        let prevent_anti_chase = !!this.currentSeasonBatchHas?.(me,28001);
        // if we chased 1 or more times during this card, let's regard that as 1 chase for now...
        if (me.dream_craze_dance_tune_stacks > 0 && me.chases < me.max_chases) {
            this.reduce_idx_x_by_c(0, "dream_craze_dance_tune_stacks", 1);
            if (me.this_card_chases <= 0) {
                me.this_card_chases += 1;
            }
        }
        if (me.this_card_chases <= 0) {
            if (me.agility >= 10 && me.chases < me.max_chases) {
                me.this_card_chases += 1;
                me.agility -= 10;
                this.log("Spent 10 agility to chase. Agility is now " + me.agility);
            }
        }
        if (me.this_card_chases > 0 && me.prevent_anti_chase > 0) {
            prevent_anti_chase = true;
            me.prevent_anti_chase -= 1;
        }
        if (me.this_card_chases > 0 && me.chases < me.max_chases) {
            let do_entangle = (me.entangle > 0
                && !prevent_anti_chase
            );
            if (do_entangle &&
                me.resonance_indomitable_will_stacks > 0 &&
                me.stance === STICK_STANCE
            ) {
                do_entangle = false;
                this.reduce_idx_hp(0, 15);
            }
            if (do_entangle) {
                this.reduce_idx_x_by_c(0, "entangle", 1);
                this.for_each_x_add_y("entangling_ancient_vine_stacks", "wound");
                return false;
            } else {
            if (me.dream_predicament_for_immortals_stacks > 0
                && !prevent_anti_chase
            ) {
                me.this_card_chases = 0;
                return false;
            }
                me.chases += 1;
                this.log("incremented chases to " + me.chases);
                return false;
            }
        }
        return true;
    };
}
