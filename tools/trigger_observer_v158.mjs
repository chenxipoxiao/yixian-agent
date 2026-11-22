// Observation only: each wrapped call receives the original arguments and receiver.
// No RNG, state assignment, card registration, or outcome input is added.
export function observeTriggers(game, originalPlayers, order) {
  const fields = [
    'hp','max_hp','qi','def','hp_gained','hp_gained_this_turn','hp_lost',
    'max_hp_lost','times_max_hp_reduced','increase_atk','wood_thorn',
    'stillness_citta_dharma_stacks','ultimate_world_formation_stacks',
    'activate_wood_spirit_stacks','activate_fire_spirit_stacks',
    'activate_earth_spirit_stacks','activate_metal_spirit_stacks','activate_water_spirit_stacks',
    'five_elements_gather_qi_stacks','herbs_flourish_stacks',
    'next_card_index','currently_playing_card_idx','currently_triggering_card_idx',
    'currently_triggering_card_id','trigger_depth','chases','max_chases','this_card_chases',
    'repel_citta_dharma_stacks','finishing_touch_stacks','repeat_next_card_stacks',
    'kun_wu_molten_ring_stacks','dream_motionless_tutelary_formation_stacks',
    'xuanming_forceage_formation_stacks','birdie_wind_stacks','frozen_snow_lotus_stacks',
    'prevent_gain_hp_stacks','metal_spirit_chokehold_stacks','appetite','indigestion',
    'vitality_blossom_stacks','elusive_footwork_stacks','styx_night_footwork_stacks',
  ];
  const snapshot = () => {
    const out=[null,null];
    originalPlayers.forEach((p,i)=>{
      out[order[i]]=Object.fromEntries(fields.filter(k=>Object.hasOwn(p,k)).map(k=>[k,p[k]]));
      out[order[i]].cards=[...p.cards];
    });
    return out;
  };
  const methods = ['sim_turn','start_of_game_setup','trigger_card','just_do_the_card_and_nothing_else',
    'increase_idx_hp','reduce_idx_hp','increase_idx_max_hp','reduce_idx_max_hp',
    'increase_idx_qi','increase_idx_activate','increase_idx_x_by_c','reduce_idx_x_by_c',
    'do_herbs_flourish','do_ultimate_world_formation','do_five_elements_circulation',
    'do_fire_spirit_blazing_praerie','chase','atk'];
  const events=[], stack=[]; let turn=0;
  for (const method of methods) {
    const original=game[method];
    if(typeof original!=='function') throw new Error('trigger_observer_missing:'+method);
    game[method]=function(...args) {
      if(method==='sim_turn') turn++;
      const e={id:events.length,parent:stack.length?stack.at(-1):null,turn,method,
        actor:order[originalPlayers.indexOf(this.players[0])],
        args:args.map(x=>x===undefined?{undefined:true}:x!==null&&typeof x==='object'?{object:true,name:x.name??null}:x),
        current_card:this.players[0].currently_triggering_card_id,
        trigger_depth:this.players[0].trigger_depth,before:snapshot(),log_start:this.output.length};
      events.push(e);stack.push(e.id);
      try { return Reflect.apply(original,this,args); }
      catch(error) { e.error=String(error.message);throw error; }
      finally { e.after=snapshot();e.log_end=this.output.length;stack.pop(); }
    };
  }
  return ()=>({schema:'trigger-observer-v158',events,
    recorded_game_action_log:false,training_label_allowed:false,
    limits:['Simulator calls are observed, not real intermediate game states.',
      'Calls bound before installation may bypass a wrapper.',
      'Initialization completed before installation is outside observation.',
      'Direct assignments are represented only by before/after snapshots.',
      'Missing properties are omitted rather than invented.']});
}
