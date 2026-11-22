import {installCurrentFanQi as original,applyCurrentFanQiDamage} from './current_fan_qi_v79r2.mjs';
export function installCurrentFanQi(...args){const result=original(...args);args[1].increase_idx_qi=currentGain;return result;}
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
        if (me.mortal_body_stacks > 0 && !this.currentSeasonBatchHas?.(me,17071)) {
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
        if (!this.current_hexagram_fates_owns195?.(idx) && me.wind_spirit_forging_stacks > 0 && me.wind_spirit_forging_gained < 5) {
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
        this.current_hexagram_fates_qi_gain?.(idx, amt);
        if (this.current_hexagram_fates_owns195?.(idx) && me.wind_spirit_forging_stacks > 0 && me.wind_spirit_forging_gained < 5) {
            const physique_amt = Math.min(amt, 5 - me.wind_spirit_forging_gained);
            me.wind_spirit_forging_gained += physique_amt;
            this.increase_idx_physique(idx, physique_amt);
        }

        if (me.spirit_hexagram_evolves_stacks > 0) {
            me.spirit_hexagram_evolves_triggered = true;
        }
    }
