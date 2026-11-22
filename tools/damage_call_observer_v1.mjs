// Observation only: retain call arguments, ordering and return values.
export function observeDamageCalls(game, originals, order) {
  const events=[],stack=[];
  let turn=0;
  const fields=new Set([
    'hp','max_hp','qi','def','hp_lost','physique','max_physique','cultivation',
    'currently_playing_card_idx','currently_triggering_card_idx','currently_triggering_card_id',
    'cards','is_star_point','star_power','bonus_star_power_multiplier','sword_intent',
    'ignore_sword_intent','sword_intent_to_lose','increase_atk','decrease_atk','weaken','flaw',
    'force','max_force','wound','internal_injury','agility','stance',
    'indomitable_will_stacks','nothing_is_appropriate_stacks','exercise_bones_stacks',
    'star_sky_forge_bone_stacks','lonely_night_wolf_stacks','bonus_atk_amt',
    'crash_fist_stygian_night_stacks','next_attack_deals_extra',
    'next_attack_double_sword_intent_and_increase_atk','craze_dance_tune_stacks',
    'heavenly_will_seizing_stacks','majestic_qi_stacks','dream_majestic_qi_permanent',
    'debuffs_count_as_force','this_card_crash_fist_inch_force_stacks','ignore_decrease_atk',
    'metal_spirit_iron_bone_stacks','dream_revitalized_doublings','water_spirit_dive_stacks',
    'ignore_weaken','jade_scroll_of_yin_symbol_stacks','thunder_citta_dharma_stacks',
    'm_sinking_qi_stacks','everything_goes_way_stacks','counter_move_stacks',
    'dream_repel_citta_dharma_stacks','guard_up','ignore_guard_up','ignore_def','smash_def',
    'leaf_blade_flower_stacks','this_card_crash_fist_blitz_stacks','fraccide_formation_stacks',
    'penetrate','apparition_confusion_stacks','wood_thorn','wood_spirit_spring_breeze_stacks',
    'branch_break_acupressure_turns','dream_wood_spirit_formation_attack_steal_hp_stacks',
    'resonance_indomitable_will_stacks','resonance_coral_sword_stacks',
  ]);
  const owner=p=>order[originals.indexOf(p)];
  const snap=()=>originals.map(p=>({input_player:owner(p),
    state:Object.fromEntries([...fields].filter(k=>Object.hasOwn(p,k)).map(k=>[k,structuredClone(p[k])]))}));
  for(const method of ['deal_damage_inner','atk','reduce_idx_hp','reduce_idx_def','trigger_card','sim_turn']) {
    const original=game[method];
    if(typeof original!=='function')throw new Error('damage_observer_missing:'+method);
    game[method]=function(...args){
      if(method==='sim_turn')turn++;
      const event={id:events.length,parent:stack.length?stack.at(-1):null,turn,method,
        args:args.map(v=>v===undefined?{undefined:true}:v),actor:owner(this.players[0]),
        runtime_player_order:this.players.map(owner),before:snap(),log_start:this.output.length};
      events.push(event);stack.push(event.id);
      try {
        const value=Reflect.apply(original,this,args);
        event.return_value=value===undefined?{undefined:true}:value;return value;
      } catch(error){event.error=String(error.message);throw error;}
      finally {event.after=snap();event.log_end=this.output.length;stack.pop();}
    };
  }
  return ()=>({schema:'damage_call_observer_v1',events,
    observed_fields:[...fields],training_label_allowed:false,
    limits:['Only listed fields and captured method boundaries are observed.',
      'Previously captured bound methods and internal assignments can be below these wrappers.',
      'These are simulator inputs and outputs, not independent client action logs.',
      'Missing fields are omitted, never replaced with zero.']});
}
