import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const check=(v,m)=>{if(!v)throw new Error('preparation_v77_unresolved:'+m);};
export function preparationFacts(root){
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-preparation-v77.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')==='0b0494397da547053114667c14be226237e7b5ac0a5d4701ecc7e2c966dadcc9','evidence_changed');const f=JSON.parse(raw);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 return f;
}
// Installed before existing trigger wrappers, only for an explicit13015 owner.
export function installPreparationConsumption(root,game,swogi,input,batch){
 if(!batch&&!input?.players?.some(es=>es.some(e=>e.strategy_id===13015)))return false;
 preparationFacts(root);
const is_post_action = function(card_id) {
    return swogi[card_id].is_post_action;
}
    game.trigger_card = function(card_id, idx) {
        this.indent();
        const p0 = this.players[0];
        p0.trigger_depth += 1;
        const prev_triggering_idx = p0.currently_triggering_card_idx;
        const prev_triggering_id = p0.currently_triggering_card_id;
        const prev_bonus_atk_amt = p0.bonus_atk_amt;
        p0.bonus_atk_amt = 0;
        const prev_ignore_sword_intent = p0.ignore_sword_intent;
        const prev_bonus_rep_amt = p0.bonus_rep_amt;
        const prev_this_trigger_directly_attacked = p0.this_trigger_directly_attacked;
        let card = swogi[card_id];
        p0.currently_triggering_card_idx = idx;
        p0.currently_triggering_card_id = card_id;
        p0.bonus_rep_amt = 0;
        this.do_cosmos_seal(card_id);
        const prev_damage_dealt_to_hp_by_this_card_atk = p0.damage_dealt_to_hp_by_this_card_atk;
        p0.damage_dealt_to_hp_by_this_card_atk = 0;
        p0.this_trigger_directly_attacked = false;
        const entered_unrestrained_sword_clear_heart_effect = p0.unrestrained_sword_clear_heart_stacks > 0;
        if (p0.unrestrained_sword_clear_heart_stacks > 0) {
            p0.unrestrained_sword_clear_heart_effect_depth += 1;
        }
        const entered_m_light_sword_effect = p0.m_light_sword_stacks > 0;
        if (p0.m_light_sword_stacks > 0) {
            p0.m_light_sword_effect_depth += 1;
        }
        this.check_adjacent_effects_before_card(idx, card_id);
        this.do_cloud_sword_softheart_and_friends(card_id);
        this.do_dream_cloud_sword_softheart_sword_formation_gives_cloud_sea(card_id);
        if (this.is_sword(card_id) && p0.dream_spiritage_sword_sword_qi_stacks > 0) {
            this.increase_idx_x_by_c(0, "sword_qi", p0.dream_spiritage_sword_sword_qi_stacks);
        }
        this.do_astral_divination_hexagram(card_id);
        this.do_sword_formation_guard(idx);
        this.do_regenerating_body(idx);
        this.do_crash_citta_dharma(card_id);
        this.do_pre_crash_fist(card_id);
        this.do_cycle_of_five_elements_and_friends(card_id);
        this.do_wood_spirit_formation(card_id);
        this.do_wood_spirit_forceage_formation(card_id);
        this.do_fire_spirit_formation(card_id);
        this.do_earth_spirit_formation(card_id);
        this.do_metal_spirit_formation(card_id);
        this.do_water_spirit_formation(card_id);
        this.do_alkaline_water_zongzi(card_id);
        this.do_resonance_store_qi(idx);
        this.do_resonance_inheritance_of_spirit_sword(card_id);
        if (p0.dream_exercise_fist_physique_stacks > 0 && p0.trigger_depth === 1) {
            const amt = p0.dream_exercise_fist_physique_stacks;
            p0.dream_exercise_fist_physique_stacks = 0;
            this.increase_idx_physique(0, amt);
        }
        this.do_herbs_flourish(card_id);
        this.do_flying_brush_chase();
        if (p0.consume_next_card_played_stacks > 0 && p0.trigger_depth === 1) {
            this.reduce_idx_x_by_c(0, "consume_next_card_played_stacks", 1);
            this.consumption();
            this.current_preparation_consumed?.(p0, idx);
        }
        this.just_do_the_card_and_nothing_else(card);
        //card_actions[card_id](this);
        //this.do_action(card.actions);
        this.do_dream_heavenly_marrow_agility(card_id);
        this.do_god_luck_avoid(card_id);
        if (p0.dream_exercise_fist_atk_physique_pct > 0 && p0.this_trigger_directly_attacked) {
            p0.dream_exercise_fist_atk_physique_pct = 0;
        }
        p0.dream_exercise_fist_physique_stacks += p0.later_dream_exercise_fist_physique_stacks;
        p0.later_dream_exercise_fist_physique_stacks = 0;
        p0.dream_exercise_fist_atk_physique_pct += p0.later_dream_exercise_fist_atk_physique_pct;
        p0.later_dream_exercise_fist_atk_physique_pct = 0;
        p0.dream_qi_perfusion_guarantee_injured = 0;
        this.do_record_musician_card_played_for_chord_in_tune(card_id);
        p0.bonus_atk_amt = 0;
        // expire crash fist buffs - they don't apply to extra attacks
        this.do_post_crash_fist(card_id);
        this.currentSeasonAfterBody?.(card_id);


        // Extra attacks zone
        if (p0.trigger_depth <= 1) {
            this.do_emptiness_sword_formation(card_id);
            this.do_cloud_sword_endless(card_id);
            this.do_endless_sword_formation();
            this.do_observe_body();
            this.do_beast_spirit_sword_formation(card_id);
            this.do_sword_qi(card_id);
            this.do_stance_of_fierce_attack(card_id);
            this.do_god_luck_approach(card_id);
            this.do_hunter_hunting_hunter(card_id);
            if (p0.spiritual_hunter_stacks > 0 && is_post_action(card_id)) {
                this.log("Attacking for " + p0.spiritual_hunter_stacks + " from spiritual hunter.");
                this.atk(p0.spiritual_hunter_stacks, true);
            }
            this.do_m_shifting_stars(card_id);
        }
        // More extra attack zone
        this.do_crash_fist_shocked(card_id);
        this.do_m_crash_fist_entangle(card_id);
        if (p0.this_card_dream_crash_fist_continue_count > 0) {
            const count = p0.this_card_dream_crash_fist_continue_count;
            p0.this_card_dream_crash_fist_continue_count = 0;
            for (let i = 0; i < count; i++) {
                this.atk(2, true);
            }
        }

        this.check_adjacent_effects_after_card(idx);
        if (p0.trigger_depth === 1 && p0.dream_dotted_around_per_turn > 0 && p0.can_trigger_dream_dotted_around && !p0.is_star_point[idx]) {
            p0.can_trigger_dream_dotted_around = false;
            this.increase_idx_qi(0, p0.dream_dotted_around_per_turn);
            this.increase_idx_star_power(0, p0.dream_dotted_around_per_turn);
        }
        if (p0.trigger_depth === 1 && p0.dream_dotted_around_countdown > 0 && !p0.is_star_point[idx]) {
            p0.dream_dotted_around_countdown -= 1;
            this.increase_idx_qi(0, 1);
            this.increase_idx_star_power(0, 1);
        }
        if ((p0.cards.includes("D12204") || p0.cards.includes("D12205")) &&
                p0.is_star_point[idx] && p0.trigger_depth === 1) {
            this.increase_idx_debuff(1, "internal_injury", 1);
        }
        this.currentSeasonAfterCard?.(card_id);
        this.do_cloud_sword_chain_count(card_id);
        this.do_unrestrained_sword_count(card_id);
        this.do_elemental_spirit_stuff(card_id);
        p0.played_card_count += 1;
        if (card.hp_cost > 0) {
            this.increase_idx_x_by_c(0, "hp_cost_card_count", 1);
        }
        if (card.is_wood_spirit || card.is_fire_spirit || card.is_earth_spirit || card.is_metal_spirit || card.is_water_spirit) {
            p0.played_five_elements_count += 1;
        }
        if (this.is_sword_formation(card_id)) {
            p0.played_sword_formation_count += 1;
        }
        if (this.is_sword(card_id)) {
            p0.played_sword_count += 1;
        }
        if (swogi[card_id].is_snake) {
            p0.snake_card_used += 1;
        }
        this.do_sweet_zongzi_count(card_id);
        if (is_post_action(card_id)) {
            p0.played_post_action_count += 1;
        }
        if (p0.chase_if_hp_gained > 0) {
            if (p0.hp_gained > 0) {
                this.chase();
            }
            p0.chase_if_hp_gained = 0;
        }
        this.do_sword_intent_end_of_card();
        p0.total_amount_injured += p0.damage_dealt_to_hp_by_this_card_atk;
        p0.damage_dealt_to_hp_by_this_card_atk = prev_damage_dealt_to_hp_by_this_card_atk;
        p0.bonus_atk_amt = prev_bonus_atk_amt;
        p0.ignore_sword_intent = prev_ignore_sword_intent;
        p0.bonus_rep_amt = prev_bonus_rep_amt;
        p0.this_trigger_directly_attacked = prev_this_trigger_directly_attacked;
        p0.currently_triggering_card_idx = prev_triggering_idx;
        p0.currently_triggering_card_id = prev_triggering_id;
        p0.sword_intent_to_lose = 0;
        p0.sword_intent_to_regain = 0;
        if (entered_unrestrained_sword_clear_heart_effect) {
            if (p0.unrestrained_sword_clear_heart_effect_depth > 0 &&
                    p0.unrestrained_sword_clear_heart_effect_depth <= p0.unrestrained_sword_clear_heart_stacks) {
                p0.unrestrained_sword_clear_heart_stacks -= 1;
            }
            p0.unrestrained_sword_clear_heart_effect_depth -= 1;
        }
        if (entered_m_light_sword_effect) {
            if (p0.m_light_sword_effect_depth > 0 &&
                    p0.m_light_sword_effect_depth <= p0.m_light_sword_stacks) {
                p0.m_light_sword_stacks -= 1;
            }
            p0.m_light_sword_effect_depth -= 1;
        }
        p0.trigger_depth -= 1;
        this.unindent();
    };

 return true;
}
