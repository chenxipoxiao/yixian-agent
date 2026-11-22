// Frozen native sim_turn with only the current 153 payment branch changed.
import {swogi,format_card,STICK_STANCE} from '../external/yisim/card_info.js';
const is_post_action=id=>swogi[id].is_post_action;
export function installChasePayment(game,reduceCost) {
    game.sim_turn=function() {
        const me = this.players[0];
        const enemy = this.players[1];
        let tutelary_can_heal = true;
        me.hp_gained_this_turn = 0;
        me.xuanming_recurring_hp = me.next_xuanming_recurring_hp;
        me.next_xuanming_recurring_hp = me.hp;
        this.do_resonance_rejuvenation();
        me.chases = 0;
        me.this_turn_attacked = false;
        if (me.dream_craze_dance_tune_pending_stacks > 0) {
            const pending = me.dream_craze_dance_tune_pending_stacks;
            this.reduce_idx_x_by_c(0, "dream_craze_dance_tune_pending_stacks", pending);
            this.increase_idx_x_by_c(0, "dream_craze_dance_tune_stacks", pending);
        }
        enemy.elusive_footwork_triggered = enemy.elusive_footwork_stacks > 0;
        me.dream_elusive_footwork_trigger_count = 0;
        me.styx_night_footwork_triggered = false;
        enemy.styx_night_footwork_triggered = false;
        me.surge_of_qi_gain_agility_triggered = false;
        me.spirit_hexagram_evolves_triggered = false;
        me.dream_thunder_hexagram_rhythm_triggered = 0;
        me.triggered_beast_spirit_sword_formation = false;
        me.can_trigger_resonance_cat_paw = true;
        me.can_trigger_dream_dotted_around = true;
        this.reduce_idx_x_by_c(0, "everything_goes_way_stacks", 1);
        this.reduce_idx_x_by_c(0, "god_opportunity_conform_stacks", 1);
        this.reduce_idx_x_by_c(0, "god_opportunity_reversal_stacks", 1);
        this.reduce_idx_x_by_c(0, "metal_spirit_iron_bone_stacks", 1);
        this.reduce_idx_x_by_c(0, "water_spirit_dive_stacks", 1);
        this.reduce_idx_x_by_c(0, "dream_repel_citta_dharma_stacks", 1);
        this.reduce_idx_x_by_c(0, "counter_move_stacks", 1);
        if (me.dream_earth_spirit_steep_stacks > 0) {
            me.dream_earth_spirit_steep_stacks -= 1;
        }
        this.do_def_decay();
        this.do_illusion_tune();
        this.do_heartbroken_tune();
        this.do_meditation_of_xuan();
        this.do_cacopoisonous_formation();
        this.do_break_sky_eagle();
        this.do_scarlet_eye_the_sky_consumer();
        this.do_next_turn_def();
        this.do_spirit_gather_citta_dharma();
        this.do_spiritage_formation();
        this.do_force_spiritage_formation();
        this.do_qi_gathering_merpeople_pearl();
        this.do_dream_cloud_elixir();
        this.do_apex_sword_citta_dharma();
        this.do_heavenly_spirit_forceage_formation();
        this.do_fat_immortal_raccoon();
        this.do_regen();
        this.do_nuwa_stone();
        this.do_dream_great_recover_elixir();
        this.do_ultimate_hexagram_base();
        this.do_ultimate_polaris_hexagram_base();
        this.do_water_spirit_spring_rain();
        let dream_billows_extra_fow = 0;
        let dream_billows_extra_qi = 0;
        if (me.dream_water_spirit_billows_double > 0) {
            dream_billows_extra_fow = me.force_of_water * me.dream_water_spirit_billows_double;
            dream_billows_extra_qi = me.qi * me.dream_water_spirit_billows_double;
            this.increase_idx_x_by_c(0, "force_of_water", dream_billows_extra_fow);
            this.increase_idx_qi(0, dream_billows_extra_qi);
            me.dream_water_spirit_billows_double = 0;
        }
        this.do_dream_cloud_sword_softheart_gain_def();
        this.do_wood_spirit_all_things_grow();
        this.do_internal_injury(0, true);
        this.do_void_the_spirit_consumer();
        if (this.check_for_death()) {
            return;
        }
        let action_idx = 0;
        let can_act = true;
        if (me.cannot_act_stacks > 0) {
            this.reduce_idx_x_by_c(0, "cannot_act_stacks", 1);
            can_act = false;
        }
        while (action_idx <= me.chases && action_idx <= me.max_chases && can_act) {
            me.just_revived = false;
            this.do_shadow_owl_rabbit_lose_hp(action_idx);
            this.do_octgates_lock_formation(action_idx);
            this.do_devouring_ancient_vine(action_idx);
            if (action_idx > 0 && me.surge_of_qi_stacks > 0 && me.stance === STICK_STANCE) {
                this.increase_idx_qi(0, 1);
                this.increase_idx_hp(0, 2);
            }
            if (action_idx > 0 && me.gain_ignore_def_on_chase_stacks > 0) {
                this.increase_idx_x_by_c(0, "ignore_def", 1);
            }
            if (action_idx > 0 && me.gain_penetrate_on_chase_stacks > 0) {
                this.increase_idx_penetrate(0, me.gain_penetrate_on_chase_stacks);
            }
            if (action_idx > 0 && me.dream_fire_formation_stacks > 0) {
                this.reduce_idx_hp(1, me.dream_fire_formation_stacks);
                this.reduce_idx_max_hp(1, me.dream_fire_formation_stacks);
                this.increase_idx_def(0, me.dream_fire_formation_stacks);
            }
            if (this.check_for_death()) {
                return;
            }
            if (action_idx > 0) {
                this.log("chase!!");
            }
            action_idx += 1;
            this.do_skip_next_card();
            while (me.next_card_index === me.cards.length - 1 &&
                   swogi[me.cards[me.next_card_index]].name === "Five Elements Spiritual Field") {
                this.advance_next_card_index();
                this.do_skip_next_card();
            }
            while (this.do_nameless_white_deer_skip()) {
                this.do_skip_next_card();
            }
            let card_id = me.cards[me.next_card_index];
            let card = swogi[card_id];
            let qi_cost = card.qi_cost;
            if (card.decrease_qi_cost_by_x !== undefined) {
                let x = card.decrease_qi_cost_by_x;
                let reduce_amt = 0;
                if (x === "food") {
                    reduce_amt = me.internal_injury +
                                me.indigestion +
                                me.appetite +
                                me.regen;
                } else
                if (x === "debuff") {
                    reduce_amt = this.get_debuff_count(0);
                } else if (x === "different_five_elements") {
                    reduce_amt = this.get_n_different_five_elements(0);
                } else {
                    reduce_amt = me[x];
                }
                if (reduce_amt) {
                    qi_cost = Math.max(0, qi_cost - reduce_amt);
                }
            }
            if (me.centibird_spirit_sword_rhythm_stacks > 0 &&
                this.is_spirit_sword(card_id)) {
                qi_cost = Math.max(0, qi_cost - me.centibird_spirit_sword_rhythm_stacks);
            }
            qi_cost = reduceCost(card_id,me.next_card_index,qi_cost);
            if (me.spiritual_hunter_stacks > 0 && is_post_action(card_id)) {
                qi_cost = Math.max(0, qi_cost - 2);
            }
            if (card.water_spirit_cost_0_qi && this.if_water_spirit()) {
                qi_cost = 0;
            }
            if (card.cloud_hit_cost_0_qi && this.if_cloud_hit()) {
                qi_cost = 0;
            }
            if (me.is_star_point[me.next_card_index]) {
                qi_cost = Math.max(0, qi_cost - me.reduce_qi_cost_on_star_point_stacks);
            }
            qi_cost = Math.max(0, qi_cost - me.inspiration_stacks);
            let hp_cost = card.hp_cost;
            const orig_hp_cost = hp_cost;
            // BUG: arguably we should check dream - crash footwork here because of bounce
            if (hp_cost === 4) {
                if (card_id.startsWith("14105")) {
                    let reduce_amt = Math.floor(me.physique / 2);
                    hp_cost = Math.max(0, hp_cost - reduce_amt);
                }
            }
            if (me.unbounded_qi_stacks > 0) {
                if (me.qi < qi_cost) {
                    const excess_qi = qi_cost - me.qi;
                    if (me.hp > 3 * excess_qi) {
                        qi_cost -= excess_qi;
                        let unbounded_qi_hp_cost = 3 * excess_qi;
                        this.log("player 0 is spending " + unbounded_qi_hp_cost + " hp to play " + format_card(card_id));
                        this.reduce_idx_hp(0, unbounded_qi_hp_cost, true);
                    }
                }
            }
            if (me.qi < qi_cost && me.qi + me.sword_qi >= qi_cost) {
                const sword_qi_spent = qi_cost - me.qi;
                this.reduce_idx_x_by_c(0, "sword_qi", sword_qi_spent);
                qi_cost = me.qi;
            }
            if (me.qi < qi_cost) {
                this.gain_qi_to_afford_card(card.gather_qi);
                this.log("player 0 gained qi instead of playing " + format_card(card_id) + ". They now have " + me.qi + "/" + qi_cost + " qi");
            } else {
                me.inspiration_stacks = 0;
                if (qi_cost > 0) {
                    this.reduce_idx_x_by_c(0, "qi", qi_cost);
                    this.log("player 0 spent " + qi_cost + " qi to play " + format_card(card_id));
                }
                if (hp_cost !== undefined) {
                    if (hp_cost > 0) {
                        if (me.cracking_fist_stacks > 0) {
                            this.reduce_idx_max_hp(0, hp_cost);
                        } else
                        {
                            this.reduce_idx_hp(0, hp_cost, true);
                        }
                    }
                    this.log("player 0 spent " + hp_cost + " hp to play " + format_card(card_id));
                    if (orig_hp_cost > 0 && me.blood_shadow_escape_stacks > 0) {
                        this.reduce_idx_x_by_c(0, "blood_shadow_escape_stacks", 1);
                        this.increase_idx_x_by_c(0, "agility", orig_hp_cost);
                    }
                    // bounce is consumed by spending 0 hp to play mountain cleaving palms
                    // but it is not used when paying hp via unbounded qi
                    let refund_hp = false;
                    refund_hp ||= me.crash_fist_bounce_stacks > 0;
                    refund_hp ||= me.crash_fist_return_to_xuan_stacks > 0;
                    if (refund_hp) {
                        if (this.is_crash_fist(card_id)) {
                            if (me.crash_fist_bounce_stacks > 0) {
                                this.heal(orig_hp_cost);
                                this.log("player 0 healed " + orig_hp_cost + " hp from crash fist bounce");
                                if (!swogi[card_id].is_crash_fist_continue)
                                {
                                    me.crash_fist_bounce_stacks -= 1;
                                }
                            }
                            if (me.crash_fist_return_to_xuan_stacks > 0) {
                                this.heal(orig_hp_cost);
                                this.log("player 0 healed " + orig_hp_cost + " hp from crash fist return to xuan");
                            }
                        }
                    }
                    if (orig_hp_cost > 0 && me.dream_crash_fist_bounce_permanent > 0) {
                        this.increase_idx_def(0, orig_hp_cost);
                    }
                    if (orig_hp_cost > 0 && me.dream_crash_fist_bounce_stacks > 0) {
                        me.dream_crash_fist_bounce_stacks--;
                        this.increase_idx_def(0, orig_hp_cost);
                    }
                    if (orig_hp_cost > 0 && card_id.startsWith("14509")) {
                        this.deal_damage(orig_hp_cost);
                    }
                    if (orig_hp_cost > 0 && me.crash_fist_shatter_stacks > 0 && this.is_crash_fist(card_id)) {
                        this.deal_damage(orig_hp_cost);
                        if (!swogi[card_id].is_crash_fist_continue)
                        {
                            this.reduce_idx_x_by_c(0, "crash_fist_shatter_stacks", 1);
                        }
                    }
                }
                if (hp_cost === undefined && qi_cost === 0) {
                    this.log("player 0 is playing " + format_card(card_id));
                }
                const card_idx = me.next_card_index;
                this.do_xiaoyao_reproduction(card_idx);
                this.do_continuous_tune(card_idx);
                this.do_nether_void_canine(card_idx);
                this.do_kongtong_seal(card_idx);
                this.do_mutual_growth(card_idx);
                this.do_salted_egg_yolk_zongzi(card_idx);
                this.do_finishing_touch(card_idx);
                this.do_dream_unrestrained_sword_zero_upgrade(card_idx);
                this.do_spirit_fusion_pot(card_idx);
                card_id = me.cards[card_idx];
                this.play_card(card_id, card_idx);
                if (this.check_for_death()) {
                    return;
                }
                this.log("player 0 finished playing " + card.name);
                if (me.prevent_next_auto_advance) {
                    me.prevent_next_auto_advance = false;
                } else {
                    this.advance_next_card_index();
                }
                if (this.players[0].predicament_for_immortals_stacks > 0
                    && this.players[0].prevent_anti_chase === 0
                ) {
                } else
                {
                this.do_heavenly_marrow_dance_tune_chase();
                this.do_shadow_owl_rabbit_chase();
                this.do_five_elements_heavenly_marrow_rhythm_chase();
                this.do_heavenly_marrow_gourd_chase();
                tutelary_can_heal = this.process_this_card_chases() && tutelary_can_heal;
                }
            }
        }
        if (this.check_for_death()) {
            return;
        }
        this.do_sword_in_sheathed();
        this.do_resonance_sword_formation_guard();
        this.do_regen_tune();
        this.do_xuanming_regen_tune();
        this.do_m_vitality_blossom();
        this.do_thunderphilia_formation();
        this.do_scutturtle_formation();
        // BUG: motionless tutelary formation thinks you chased if your chase was prevented by entangle or dream predicament
        this.do_motionless_tutelary_formation(tutelary_can_heal);
        this.do_yin_yang_tutelary_formation();
        this.do_thunderbolt_tune();
        this.do_anthomania_formation();
        this.do_dream_unrestrained_sword_two();
        this.do_toxin_immunity();
        this.do_force_of_water();
        this.do_m_earth_spirit_formation();
        this.reduce_idx_x_by_c(0, "force_of_water", dream_billows_extra_fow);
        this.reduce_idx_x_by_c(0, "qi", dream_billows_extra_qi);
        this.do_hard_bamboo();
        this.do_three_tailed_cat();
        this.reduce_idx_x_by_c(0, "metal_spirit_chokehold_stacks", 1);
        this.reduce_idx_x_by_c(0, "weaken", 1);
        this.reduce_idx_x_by_c(0, "prevent_gain_hp_stacks", 1);
        this.reduce_idx_x_by_c(0, "wood_spirit_spring_breeze_stacks", 1);
        this.reduce_idx_x_by_c(0, "prevent_gain_def_stacks", 1);
        this.reduce_idx_x_by_c(0, "dream_motionless_tutelary_formation_stacks", 1);
        this.reduce_idx_x_by_c(0, "flaw", 1);
        this.reduce_idx_x_by_c(0, "entangle", 1);
        this.reduce_idx_x_by_c(0, "m_flower_sentient_stacks", 1);
        this.reduce_idx_x_by_c(0, "m_fire_spirit_seal_stacks", 1);
        this.reduce_idx_x_by_c(0, "m_metal_spirit_seal_stacks", 1);
        if (me.branch_break_acupressure_turns > 0) {
            this.reduce_idx_x_by_c(0, "branch_break_acupressure_turns", 1);
        }
        me.elusive_footwork_triggered = false;
        enemy.elusive_footwork_triggered = false;
        if (me.spirit_hexagram_evolves_triggered) {
            me.spirit_hexagram_evolves_triggered = false;
            this.increase_idx_hexagram(0, 1);
        }
        me.surge_of_qi_gain_agility_triggered = false;
        // Client572 cleanup precedes the owner death-guard18 cleanup.
        this.current_temporary_chase_cleanup?.();
        me.not_dead_yet = 0;
        if (this.check_for_death()) {
            return;
        }
    };
}
