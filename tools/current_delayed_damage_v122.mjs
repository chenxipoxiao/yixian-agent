// Pinned native damage body with one client779 hook, before return damage.
import {swogi,FIST_STANCE,STICK_STANCE} from '../external/yisim/card_info.js';
const is_thunder=card_id=>swogi[card_id].is_thunder;
export function installCurrentDelayedDamage(game) {
    game.deal_damage_inner=function(dmg, is_atk, my_idx, is_extra, this_atk_smash_def) {
        const enemy_idx = 1 - my_idx;
        let ignore_def = false;
        let smash_def = this_atk_smash_def;
        let pct_multiplier = 100;
        let dream_repel_reflect = 0;
        let min_dmg = is_atk ? 1 : 0;
        const me = this.players[my_idx];
        const enemy = this.players[enemy_idx];
        if (!is_atk && enemy.metal_spirit_iron_bone_stacks > 0) {
            dmg -= 5;
            if (dmg < 1) {
                dmg = 1;
            }
            min_dmg = 1;
        }
        if (is_atk) {
            me.this_atk_injured = false;
            if (me.trigger_depth <= 1) {
                me.this_card_directly_attacked = true;
            }
            me.this_trigger_directly_attacked = true;
            me.this_card_attacked = true;
            me.this_turn_attacked = true;
            if (me.sword_intent > 0
                    && !me.ignore_sword_intent
            ) {
                if (me.sword_intent_to_lose < me.sword_intent) {
                    me.sword_intent_to_lose = me.sword_intent;
                }
            }
            if (me.is_star_point[me.currently_playing_card_idx]) {
                dmg += (me.star_power
                    * (1 + me.bonus_star_power_multiplier)
                );
            }
            if (me.leaf_blade_flower_stacks > 0) {
                smash_def = true;
            }
            if (me.this_card_crash_fist_blitz_stacks > 0) {
                smash_def = true;
            }
            if (me.smash_def > 0 && !smash_def) {
                this.reduce_idx_x_by_c(my_idx, "smash_def", 1);
                smash_def = true;
            }
            // BUG: other ways of having smash def cause an attack to not consume the smash_def bug, but not fraccide formation
            if (me.fraccide_formation_stacks > 0) {
                this.reduce_idx_x_by_c(my_idx, "fraccide_formation_stacks", 1);
                smash_def = true;
                dmg += 3;
            }
            if (me.ignore_def > 0) {
                this.reduce_idx_x_by_c(my_idx, "ignore_def", 1);
                ignore_def = true;
                if (me.resonance_coral_sword_stacks > 0) {
                    dmg += 1;
                }
            }
            dmg += this.do_lonely_night_wolf();
            dmg += this.do_exercise_bones();
            dmg += this.do_star_sky_forge_bone();
            dmg += this.do_nothing_is_appropriate();
            dmg += this.do_indomitable_will();
            dmg += me.bonus_atk_amt;
            if (!is_extra && me.crash_fist_stygian_night_stacks > 0 &&
                    this.is_crash_fist(me.currently_triggering_card_id)) {
                const debuff_amt = this.get_debuff_count(0);
                dmg += Math.min(debuff_amt, me.crash_fist_stygian_night_stacks);
            }
            if (typeof this.current_shadow_adjacency_attack==='function') {
                dmg += this.current_shadow_adjacency_attack(me,my_idx);
            } else {
            if (!is_extra) {
                const next_idx = this.get_next_idx(me.currently_triggering_card_idx);
                const next_card = me.cards[next_idx];
                if (next_card === "D14094" || next_card === "D14095") {
                    dmg += Math.floor(this.get_debuff_count(0) * 0.5);
                }
            }
            }
            if (me.next_attack_deals_extra > 0) {
                dmg += me.next_attack_deals_extra;
                me.next_attack_deals_extra = 0;
            }
            if (
                    !me.ignore_sword_intent
            ) {
                dmg += me.sword_intent;
            }
            dmg += me.increase_atk;
            if (me.next_attack_double_sword_intent_and_increase_atk > 0) {
                me.next_attack_double_sword_intent_and_increase_atk -= 1;
                dmg += me.sword_intent;
                dmg += me.increase_atk;
            }
            dmg += me.craze_dance_tune_stacks;
            if (me.heavenly_will_seizing_stacks > 0) {
                this.reduce_idx_x_by_c(my_idx, "heavenly_will_seizing_stacks", 1);
                let transferred = 0;
                if (enemy.internal_injury > 0) {
                    const amt = enemy.internal_injury;
                    transferred += amt;
                    this.reduce_idx_x_by_c(enemy_idx, "internal_injury", amt);
                    this.increase_idx_debuff(my_idx, "internal_injury", amt);
                }
                if (enemy.decrease_atk > 0) {
                    const amt = enemy.decrease_atk;
                    transferred += amt;
                    this.reduce_idx_x_by_c(enemy_idx, "decrease_atk", amt);
                    this.increase_idx_debuff(my_idx, "decrease_atk", amt);
                }
                if (enemy.weaken > 0) {
                    const amt = enemy.weaken;
                    transferred += amt;
                    this.reduce_idx_x_by_c(enemy_idx, "weaken", amt);
                    this.increase_idx_debuff(my_idx, "weaken", amt);
                }
                if (enemy.flaw > 0) {
                    const amt = enemy.flaw;
                    transferred += amt;
                    this.reduce_idx_x_by_c(enemy_idx, "flaw", amt);
                    this.increase_idx_debuff(my_idx, "flaw", amt);
                }
                if (enemy.entangle > 0) {
                    const amt = enemy.entangle;
                    transferred += amt;
                    this.reduce_idx_x_by_c(enemy_idx, "entangle", amt);
                    this.increase_idx_debuff(my_idx, "entangle", amt);
                }
                if (enemy.wound > 0) {
                    const amt = enemy.wound;
                    transferred += amt;
                    this.reduce_idx_x_by_c(enemy_idx, "wound", amt);
                    this.increase_idx_debuff(my_idx, "wound", amt);
                }
                if (enemy.styx > 0) {
                    const amt = enemy.styx;
                    transferred += amt;
                    this.reduce_idx_x_by_c(enemy_idx, "styx", amt);
                    this.increase_idx_debuff(my_idx, "styx", amt);
                }
                dmg += transferred;
                this.log("Heavenly Will - Seizing transferred " + transferred + " debuffs, bonus ATK: " + transferred);
            }
            if (me.majestic_qi_stacks > 0) {
                this.reduce_idx_x_by_c(my_idx, "majestic_qi_stacks", 1);
                this.increase_idx_force(my_idx, 1);
            }
            if (me.dream_majestic_qi_permanent > 0) {
                this.increase_idx_force(my_idx, 1);
            }
            let force = me.force;
            if (me.debuffs_count_as_force) {
                force += this.get_debuff_count(my_idx);
                me.debuffs_count_as_force = false;
            }
            if (me.this_card_crash_fist_inch_force_stacks > 0) {
                force *= 2;
            }
            this.reduce_c_of_x(1, "force");
            if (this.has_dream_gather_intense_force(my_idx)) {
                dmg += force;
            } else
            {
                pct_multiplier += 10 * force;
            }
            if (!me.ignore_decrease_atk) {
                dmg -= me.decrease_atk;
            }
            me.ignore_decrease_atk = false;
            if (dmg < 1) {
                dmg = 1;
            }
            if (enemy.metal_spirit_iron_bone_stacks > 0) {
                dmg -= 5;
                if (dmg < 1) {
                    dmg = 1;
                }
                min_dmg = 1;
            }
            for (let i = 0; i < me.dream_revitalized_doublings; i++) {
                dmg *= 2;
            }
            me.dream_revitalized_doublings = 0;
            if (enemy.water_spirit_dive_stacks > 0) {
                pct_multiplier -= 40;
            }
            if (me.weaken > 0
                && !me.ignore_weaken
            ) {
                pct_multiplier -= 40;
                if (me.jade_scroll_of_yin_symbol_stacks > 0) {
                    pct_multiplier -= 10;
                }
                if (me.resonance_indomitable_will_stacks > 0 &&
                    me.stance === STICK_STANCE
                ) {
                    pct_multiplier += 20;
                }
            }
            me.ignore_weaken = false;
            if (enemy.flaw > 0) {
                pct_multiplier += 40;
                if (enemy.jade_scroll_of_yin_symbol_stacks > 0) {
                    pct_multiplier += 10;
                }
                if (enemy.resonance_indomitable_will_stacks > 0 &&
                    enemy.stance === FIST_STANCE
                ) {
                    pct_multiplier -= 20;
                }
            }
            if (!is_extra && is_thunder(me.currently_triggering_card_id)) {
                pct_multiplier += me.thunder_citta_dharma_stacks;
            }
            if (me.m_sinking_qi_stacks > 0) {
                pct_multiplier += 10 * me.qi;
            }
            me.bonus_star_power_multiplier = 0;
            if (me.everything_goes_way_stacks > 0) {
                min_dmg = 6;
            }
        }
        if (enemy.counter_move_stacks > 0 &&
            enemy.stance === FIST_STANCE) {
            pct_multiplier -= 50;
        }
        if (enemy.dream_repel_citta_dharma_stacks > 0) {
            dream_repel_reflect = Math.ceil(dmg * 25 / 100);
            if (is_atk && dream_repel_reflect < 1) {
                dream_repel_reflect = 1;
            }
            pct_multiplier -= 25;
        }
        if (dmg > 0 && pct_multiplier < 100 && min_dmg < 1) {
            min_dmg = 1;
        }
        dmg = Math.floor(dmg * pct_multiplier / 100);
        dmg = Math.max(min_dmg, dmg);
        if (is_atk) {
            if (me.apparition_confusion_stacks > 0) {
                this.reduce_idx_hp(my_idx, me.apparition_confusion_stacks);
            }
            if (me.wood_thorn > 0) {
                this.reduce_idx_hp(enemy_idx, me.wood_thorn);
                this.increase_idx_hp(my_idx, me.wood_thorn);
            }
            if (me.dream_wood_spirit_formation_attack_steal_hp_stacks > 0) {
                me.dream_wood_spirit_formation_attack_steal_hp_stacks -= 1;
                this.reduce_idx_hp(enemy_idx, 1);
                this.increase_idx_hp(my_idx, 1);
            }
            if (me.wood_spirit_spring_breeze_stacks > 0) {
                this.increase_idx_max_hp(my_idx, 2);
                this.increase_idx_hp(my_idx, 2);
            }
            if (me.branch_break_acupressure_turns > 0) {
                this.increase_idx_debuff(enemy_idx, "internal_injury", 1);
            }
        }
        let damage_to_def = 0;
        let damage_to_hp = 0;
        if (ignore_def) {
            damage_to_def = 0;
            damage_to_hp = dmg;
        } else
        if (smash_def) {
            const effective_def = Math.floor(enemy.def * .5);
            const pre_multiplied_damage_to_def = Math.min(effective_def, dmg);
            damage_to_def = pre_multiplied_damage_to_def * 2;
            if (enemy.def % 2 === 1 && effective_def < dmg) {
                damage_to_def += 1;
            }
            damage_to_hp = dmg - pre_multiplied_damage_to_def;
        } else
        {
            damage_to_def = Math.min(enemy.def, dmg);
            damage_to_hp = dmg - damage_to_def;
        }
        this.reduce_idx_def(enemy_idx, damage_to_def);
        let ignore_guard_up = false;
        let current_fengrui = 0;
        if (is_atk) {
            let can_wound = damage_to_hp > 0;
            let usable_guard_up = enemy.guard_up;
            if (me.ignore_guard_up > 0) {
                ignore_guard_up = true;
                me.ignore_guard_up -= 1;
                usable_guard_up = 0;
            }
            can_wound = can_wound && usable_guard_up === 0;
            can_wound = can_wound && enemy.covert_shift_stacks === 0;
            can_wound = can_wound || me.fire_flame_blade_stacks > 0;
            can_wound = can_wound || me.dream_qi_perfusion_guarantee_injured > 0;
            if (can_wound) {
                me.this_atk_injured = true;
                if (me.disable_penetrate_stacks <= 0 && me.penetrate > 0) {
                    const penetrate_amt = me.penetrate;
                    current_fengrui = penetrate_amt;
                    this.log("penetrating " + penetrate_amt + " damage");
                    damage_to_hp += penetrate_amt;
                    this.reduce_c_of_x(penetrate_amt, "penetrate");
                    if (me.m_metal_spirit_needle_stacks > 0) {
                        this.reduce_idx_x_by_c(0, "m_metal_spirit_needle_stacks", 1);
                        this.increase_idx_penetrate(0, penetrate_amt);
                    }
                    if (!this.current_water_blade_active?.(me) && swogi[me.currently_triggering_card_id].name === "Metal Spirit - Returning Edge" &&
                            this.if_metal_spirit()) {
                        this.increase_idx_penetrate(0, Math.ceil(penetrate_amt * 60 / 100));
                    }
                }
                damage_to_hp += enemy.wound;
                if (me.metal_spirit_giant_tripod_stacks > 0) {
                    damage_to_hp *= 2;
                }
                if (this.current_water_blade_active?.(me)) {
                    if (me.metal_spirit_giant_tripod_stacks > 0) current_fengrui *= 2;
                    damage_to_hp = this.current_water_blade_damage(me, damage_to_hp, current_fengrui);
                }
            }
        }
        let damage_actually_dealt_to_hp = this.reduce_idx_hp(
            enemy_idx, damage_to_hp, false, ignore_guard_up);
        if (is_atk) {
            me.damage_dealt_to_hp_by_atk = damage_actually_dealt_to_hp;
            me.damage_dealt_to_hp_by_this_card_atk += damage_actually_dealt_to_hp;
            if (this.currentDreamExerciseActive) {
                this.currentDreamExerciseAfterHit(my_idx,is_extra,damage_actually_dealt_to_hp);
            } else if (!is_extra && damage_actually_dealt_to_hp > 0) {
                let dream_exercise_fist_pct = 0;
                if (me.currently_triggering_card_id === "D14194" ||
                        me.currently_triggering_card_id === "D14195") {
                    dream_exercise_fist_pct = 40;
                } else if (me.dream_exercise_fist_atk_physique_pct > 0) {
                    dream_exercise_fist_pct = me.dream_exercise_fist_atk_physique_pct;
                }
                if (dream_exercise_fist_pct > 0) {
                    this.increase_idx_physique(my_idx,
                        Math.floor(damage_actually_dealt_to_hp * dream_exercise_fist_pct / 100));
                }
            }
            this.do_water_spirit_spring();
            if (damage_actually_dealt_to_hp > 0) {
                if (!is_extra) {
                    this.do_unrestrained_sword_zero();
                }
                this.do_crystallized_merpeople_pearl();
                this.do_dark_star_bat();
            }
            if (me.heavenly_will_earth_evil_stacks > 0) {
                this.reduce_idx_x_by_c(0, "heavenly_will_earth_evil_stacks", 1);
                this.increase_idx_def(0, damage_actually_dealt_to_hp);
            }
            this.current_delayed_after_attack(my_idx, damage_actually_dealt_to_hp);
            if (me.this_atk_injured) {
                this.do_resonance_cat_paw();
            }
            if (enemy.repel_citta_dharma_stacks > 0) {
                const repel_dmg = enemy.repel_citta_dharma_stacks;
                this.deal_damage_inner(repel_dmg, false, enemy_idx);
            }
            if (me.soul_wound_curse_formation_stacks > 0) {
                this.reduce_idx_x_by_c(my_idx, "soul_wound_curse_formation_stacks", 1);
                this.increase_idx_debuff(enemy_idx, "internal_injury", 1);
            }
            if (enemy.soul_wound_curse_formation_stacks > 0) {
                this.reduce_idx_x_by_c(enemy_idx, "soul_wound_curse_formation_stacks", 1);
                this.increase_idx_debuff(my_idx, "internal_injury", 1);
            }
        }
        if (dream_repel_reflect > 0 && me.can_dream_repel_citta_dharma === 0) {
            me.can_dream_repel_citta_dharma = 1;
            this.reduce_idx_hp(my_idx, dream_repel_reflect, false);
            me.can_dream_repel_citta_dharma = 0;
        }
    };
}
