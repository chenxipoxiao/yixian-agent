// Isolated diagnostic. Forward calls and preserve values of existing scalar
// fields, while observing assignments even inside previously bound functions.
export function observeQiWrites(game, originals, order) {
  const events=[], stack=[], tracked=[];
  let turn=0;
  const owner=p=>order[originals.indexOf(p)];
  const values=p=>Object.fromEntries(Object.entries(p).filter(([k,v])=>
    v===null || ['number','string','boolean'].includes(typeof v) ||
    ['cards','is_star_point'].includes(k)).map(([k,v])=>[k,structuredClone(v)]));
  const initial=originals.map(p=>({input_player:owner(p),state:values(p)}));
  const fields=['qi','sword_qi','total_qi_gained','physique','max_physique','hp','max_hp','def',
    'mortal_body_stacks','mixed_grain_zongzi_stacks','colorful_spirit_crane_stacks',
    'dream_nine_evil_ruptsprite_stacks','m_dotted_around_stacks','wind_spirit_forging_stacks',
    'wind_spirit_forging_gained','stillness_citta_dharma_stacks','spiritstat_tune_stacks',
    'spirit_command_citta_dharma_qi_gain_def_stacks','spirit_command_citta_dharma_qi_loss_def_stacks',
    'dream_yin_yang_formation_hp_stacks','dream_yin_yang_formation_def_stacks',
    'dream_consonance_qi_gives_def_stacks','spiritual_divination_stacks',
    'star_moon_hexagram_fan_stacks','wild_crossing_seal_stacks','spirit_hexagram_evolves_stacks',
    'centibird_spirit_sword_rhythm_stacks','spiritual_hunter_stacks','inspiration_stacks',
    'reduce_qi_cost_on_star_point_stacks','unbounded_qi_stacks',
    'p2_regenerating_body_stacks','p3_regenerating_body_stacks','p4_regenerating_body_stacks',
    'p5_regenerating_body_stacks','mind_body_resonance_stacks',
    'm_exercise_bones_heal_stacks','m_exercise_bones_damage_stacks','resonance_firmness_body_stacks'];
  const context=()=>({turn,actor:owner(game.players[0]),
    runtime_player_order:game.players.map(owner),
    parent:stack.length?stack.at(-1):null,
    card:game.players[0].currently_triggering_card_id,
    slot:game.players[0].currently_triggering_card_idx,
    log_index:game.output.length});
  for(const p of originals)for(const field of fields) {
    const desc=Object.getOwnPropertyDescriptor(p,field);
    if(!desc)continue;
    if(!Object.hasOwn(desc,'value')||!desc.writable||!desc.configurable)
      throw new Error('qi_write_observer_descriptor:'+field);
    let value=desc.value;
    const get=()=>value;
    const set=next=>{
      const previous=value;value=next;
      if(Object.is(previous,next))return;
      events.push({id:events.length,kind:'write',...context(),player:owner(p),field,
        before:previous,after:next,...(['qi','sword_qi'].includes(field)?
        {source_stack:new Error().stack.split('\n').slice(2,9)}:{})});
    };
    Object.defineProperty(p,field,{enumerable:desc.enumerable,configurable:desc.configurable,get,set});
    tracked.push({p,field,get,set});
  }
  const methods=['increase_idx_qi','reduce_idx_qi','increase_idx_physique',
    'increase_idx_x_by_c','reduce_idx_x_by_c','exhaust_x_to_add_y',
    'trigger_card','do_sword_qi','sim_turn','start_of_game_setup'];
  for(const method of methods) {
    const original=game[method];
    if(typeof original!=='function')throw new Error('qi_write_observer_method:'+method);
    game[method]=function(...args) {
      if(method==='sim_turn')turn++;
      const event={id:events.length,kind:'call',...context(),method,
        args:args.map(v=>v===undefined?{undefined:true}:v)};
      events.push(event);stack.push(event.id);
      try {
        const result=Reflect.apply(original,this,args);
        event.return_value=result===undefined?{undefined:true}:result;return result;
      }catch(error){event.error=String(error.message);throw error;}
      finally{event.end_event=events.length;event.log_end=this.output.length;stack.pop();}
    };
  }
  return ()=>({schema:'qi_write_observer_v1',events,initial,
    final:originals.map(p=>({input_player:owner(p),state:values(p)})),
    observed_fields:fields,observed_methods:methods,
    descriptor_integrity:tracked.every(({p,field,get,set})=>{
      const d=Object.getOwnPropertyDescriptor(p,field);return d?.get===get&&d?.set===set;}),
    limits:['Assignments to listed existing properties only; new or replaced properties are not silently inferred.',
      'Callbacks captured before installation can bypass call wrappers, but their assignments to watched properties are observed.',
      'Observation starts after installers and before start_of_game_setup; earlier installer assignments are not observed.',
      'Simulator observations, not recorded client intermediate states or independent validation.'],
    training_label_allowed:false});
}
