// Current chain-classification and next-crash effects, retaining native scheduling.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
function factsAt(root) {
  const raw=fs.readFileSync(path.join(root,'data/inspection/current-chain-cards-v11.json'));
  const digest=crypto.createHash('sha256').update(raw).digest('hex');
  if(digest!=='b139e068c4a154d28d1eeaf97aa1a6ec986207eda6c8087eaf259665fcb3b452')throw new Error('Chain card evidence changed');
  const facts=JSON.parse(raw);
  for(const [p,h] of Object.entries(facts.source_sha256)) {
    if(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')!==h)throw new Error('Chain card source changed');
  }
  return facts;
}
export function registerCurrentChainCards(root,swogi) {
  const facts=factsAt(root);
  for(const f of facts.families)f.cards.forEach((c,g)=>{
    const id=f.runtime_ids[g],dragon=f.kind==='hidden_dragon';
    if(Object.hasOwn(swogi,id))throw new Error('Chain card alias collision');
    swogi[id]=Object.freeze({...swogi['601011'],name:f.engine_name,names:[f.engine_name,c.name],
      qi_cost:Math.max(0,-c.anima),hp_cost:c.hpCost,marking:dragon?'sw':'dx',
      is_sword:dragon,is_cloud_sword:dragon,is_crash_fist:!dragon,opening:undefined,
      card_actions:game=>{
        game.atk_replay_count_or_default(c.attack,Math.max(1,c.attackCount));
        if(dragon)game.add_c_of_x(c.otherParams[game.if_cloud_hit()?1:0],'m_light_sword_stacks');
        else {
          game.add_c_of_x(c.otherParams[0],'agility');
          game.current_gain_elbow(c.otherParams[1]);
        }
      }});
  });
  return {evidence_sha256:'b139e068c4a154d28d1eeaf97aa1a6ec986207eda6c8087eaf259665fcb3b452',training_label_allowed:false};
}
export function installCurrentChainMethods(game,swogi) {
  const elbowStacks=new WeakMap(game.players.map(p=>[p,0]));
  game.current_gain_elbow=amount=>elbowStacks.set(game.players[0],elbowStacks.get(game.players[0])+amount);
  game.do_pre_crash_fist=function(card_id) {
        if (!this.is_crash_fist(card_id)) {
            return;
        }
        const me = this.players[0];
        this.for_each_x_add_y("crash_fist_poke_stacks", "bonus_atk_amt");
        this.for_each_x_add_y("crash_fist_block_stacks", "def");
        this.for_each_x_add_y("crash_fist_shake_stacks", "force");
        const wound_amt = me.crash_fist_entangle_stacks;
        this.increase_idx_debuff(1, "wound", wound_amt);
        this.for_each_x_add_y("crash_fist_blitz_stacks", "this_card_crash_fist_blitz_stacks");
        const elbow=elbowStacks.get(me);
        if(elbow>0) {
            this.increase_idx_debuff(1,'flaw',elbow);
            if(!swogi[card_id].is_crash_fist_continue)elbowStacks.set(me,0);
        }
        if (me.crash_fist_truncate_stacks > 0) {
            this.transfer_random_debuff();
        }
        this.for_each_x_add_y("crash_fist_inch_force_stacks", "this_card_crash_fist_inch_force_stacks");
        this.for_each_x_add_y("crash_fist_star_seizing_stacks", "this_card_crash_fist_star_seizing_stacks");
        this.for_each_x_add_y("crash_fist_blink_stacks", "agility");
        this.for_each_x_add_y("crash_fist_shocked_stacks", "this_card_crash_fist_shocked_stacks");
        this.for_each_x_add_y("m_crash_fist_entangle_stacks", "this_card_m_crash_fist_entangle_stacks");
        me.this_card_dream_crash_fist_continue_count += me.dream_crash_fist_continue_count;
        if (!swogi[card_id].is_crash_fist_continue)
        {
            me.crash_fist_block_stacks = 0;
            me.crash_fist_shake_stacks = 0;
            me.crash_fist_entangle_stacks = 0;
            me.crash_fist_blitz_stacks = 0;
            me.crash_fist_truncate_stacks = 0;
            me.crash_fist_inch_force_stacks = 0;
            me.crash_fist_blink_stacks = 0;
            me.crash_fist_shocked_stacks = 0;
            me.m_crash_fist_entangle_stacks = 0;
            me.crash_fist_star_seizing_stacks = 0;
            me.dream_crash_fist_continue_count = 0;
        }
  };
}
