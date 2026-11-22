// Current-client clear-heart effects; native attack, damage and scheduler are reused.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
export function installCurrentClearHeart(root,game) {
  const raw=fs.readFileSync(path.join(root,'data/inspection/current-clear-heart-v9.json'));
  const digest=crypto.createHash('sha256').update(raw).digest('hex');
  if(digest!=='f007aeb00b607f349ccd115287399a9e962b78b5d72c55a57243d82d4f779346')throw new Error('Clear-heart evidence changed');
  const facts=JSON.parse(raw);
  for(const [p,h] of Object.entries(facts.source_sha256)) {
    if(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')!==h)throw new Error('Clear-heart source changed');
  }
  game.do_clear_heart=function() {
        const ult = (0
            + this.players[0].quench_of_sword_heart_ultimate_stacks
        );
        const ult_damage = ult;
        let first_atk_damage = 7;
        // The stored bonus already includes preparation growth/acquisition.
        // Only seasonal owners use the newly admitted unbounded stored value.
        const uncapped=this.currentSeasonBatchHas?.(this.players[0],7012)||this.currentSeasonBatchHas?.(this.players[0],7134);
        first_atk_damage += uncapped?this.players[0].swordsmith_stacks:Math.min(this.players[0].swordsmith_stacks, 18);
        first_atk_damage += 3 * this.players[0].blade_forging_sharpness_stacks;
        first_atk_damage -= 2 * this.players[0].blade_forging_stable_stacks;
        first_atk_damage -= 2 * this.players[0].sword_pattern_carving_intense_stacks;
        first_atk_damage += 3 * this.players[0].quench_of_sword_heart_unrestrained_stacks;
        first_atk_damage -= 7 * this.players[0].quench_of_sword_heart_cloud_stacks;
        first_atk_damage += ult_damage;
        // do the first atk
        this.atk(Math.max(1,first_atk_damage));
        // gain def from blade_forging_stable
        const blade_forging_stable_def = 9 + ult;
        for (let i=0; i<this.players[0].blade_forging_stable_stacks; i++) {
            this.increase_idx_def(0, blade_forging_stable_def);
        }
        // attack for chain_attack
        const chain_attack_atk = 6 + ult_damage;
        for (let i=0; i<this.players[0].sword_pattern_carving_chain_attack_stacks; i++) {
            this.atk(chain_attack_atk);
        }
        // gain increase_atk from charge
        const charge_increase_atk = 1 + ult;
        for (let i=0; i<this.players[0].sword_pattern_carving_charge_stacks; i++) {
            this.increase_idx_x_by_c(0, "increase_atk", charge_increase_atk);
        }
        // gain sword_intent from intense
        const intense_sword_intent = 4 + ult;
        for (let i=0; i<this.players[0].sword_pattern_carving_intense_stacks; i++) {
            this.increase_idx_x_by_c(0, "sword_intent", intense_sword_intent);
        }
        // gain qi from spiritage
        const spiritage_qi = 2 + ult;
        for (let i=0; i<this.players[0].qi_forging_spiritage_stacks; i++) {
            this.increase_idx_qi(0, spiritage_qi);
        }
        // gain def from spiritstat
        const spiritstat_def = 3 + ult;
        for (let i=0; i<this.players[0].qi_forging_spiritstat_stacks; i++) {
            this.for_each_x_add_c_y("qi", spiritstat_def, "def");
        }
        // pay qi to make attacks from spiritual_power
        const spiritual_power_qi_cost = 1 + ult;
        const spiritual_power_rep = 2 + ult;
        const spiritual_power_atk = 4 + ult_damage;
        for (let i=0; i<this.players[0].qi_forging_spiritual_power_stacks; i++) {
            if (this.players[0].qi >= spiritual_power_qi_cost) {
                this.reduce_c_of_x(spiritual_power_qi_cost, "qi");
                for (let j=0; j<spiritual_power_rep; j++) {
                    this.atk(spiritual_power_atk);
                }
            }
        }
        // next card counts as unrestrained sword if we picked unrestrained
        if (this.players[0].quench_of_sword_heart_unrestrained_stacks > 0) {
            this.players[0].unrestrained_sword_clear_heart_stacks += this.players[0].quench_of_sword_heart_unrestrained_stacks;
        }
        // next cloud sword chases if we picked cloud
        this.players[0].cloud_sword_clear_heart_stacks += this.players[0].quench_of_sword_heart_cloud_stacks;
  };
  return {evidence_sha256:digest,native_scheduler_reused:true,training_label_allowed:false};
}
