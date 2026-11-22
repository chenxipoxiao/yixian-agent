import {FIST_STANCE} from '../external/yisim/card_info.js';
export function installSeasonDebuff(game){
game.increase_idx_debuff=function(idx, x, amt) {
        if (amt === 0) {
            return;
        }
        const me = this.players[idx];
        if (x !== "styx")
        {
            amt += me.gain_extra_debuff;
            me.gain_extra_debuff = 0;
        }
        amt=this.currentSeasonDebuffBefore?.(idx,x,amt)??amt;
        if (me.m_flower_sentient_stacks > 0 && x === "internal_injury") {
            amt += 2;
        }
        if (me.snake_shadow > 0 && (x === "internal_injury" || x === "wound")) {
            amt += me.snake_shadow;
        }
        if (me.indomitable_will_stacks > 0) {
            if (me.stance === FIST_STANCE) {
                if (x === "wound") {
                    amt -= 1;
                }
            } else {
                if (x === "decrease_atk") {
                    amt -= 1;
                }
            }
        }
        if (me.fresh_fruit_zongzi_stacks > 0 &&
            (x === "internal_injury" || x === "indigestion")) {
            this.reduce_idx_x_by_c(idx, "fresh_fruit_zongzi_stacks", 1);
            this.increase_idx_x_by_c(idx, "regen", amt);
            return;
        }
        if (amt <= 0) {
            return;
        }
        const to_sub = Math.min(amt, me.hexproof);
        if (to_sub > 0) {
            this.reduce_idx_x_by_c(idx, "hexproof", to_sub);
            amt -= to_sub;
        }
        if (amt === 0) {
            return;
        }
        me[x] += amt;
        this.log("gained " + amt + " " + x + ". Now have " + me[x] + " " + x);
        for (let i=0; i<me.unwavering_soul_stacks; i++) {
            this.increase_idx_hp(idx, amt);
        }
        if (me.mystic_snowdrop_stacks > 0) {
            this.reduce_idx_x_by_c(idx, "mystic_snowdrop_stacks", 1);
            this.increase_idx_x_by_c(1 - idx, x, amt);
        }
        if (idx === 0
            && me.dream_elusive_footwork_stacks > 0
            && me.dream_elusive_footwork_trigger_count < me.dream_elusive_footwork_stacks) {
            me.dream_elusive_footwork_trigger_count += 1;
            const reflect_amt = Math.min(amt, me.dream_elusive_footwork_reflect_cap);
            this.increase_idx_debuff(1, x, reflect_amt);
        }
        if (me.m_ruthless_water_stacks > 0
            && x !== "internal_injury"
            && x !== "styx"
        ) {
            const ii_amt = amt * me.m_ruthless_water_stacks;
            this.increase_idx_x_by_c(idx, "internal_injury", ii_amt);
        }
        if (x === "styx") {
            if (me.character === "dx3" || this.currentSeasonStyxHeals?.(me)) {
                this.increase_idx_hp(idx, amt * 3);
            } else {
                this.reduce_idx_hp(idx, amt * 3, false);
            }
        }
        this.currentSeasonDebuffAccepted?.(idx,x,amt);
    };
}
