// Diagnostic-only observer. Forward every original call unchanged; never edit game state.
export function observeHpCallbacks(game, originalPlayers, order) {
  const fields = [
    'hp', 'max_hp', 'qi', 'def', 'hp_lost', 'hp_gained', 'hp_gained_this_turn',
    'physique', 'max_physique', 'next_card_index', 'currently_triggering_card_idx',
    'elusive_footwork_stacks', 'elusive_footwork_triggered',
    'styx_night_footwork_stacks', 'styx_night_footwork_triggered',
    'birdie_wind_stacks', 'frozen_snow_lotus_stacks', 'bad_omen_stacks',
    'xuanming_forceage_formation_stacks', 'dream_earth_spirit_steep_stacks',
    'guard_up', 'covert_shift_stacks', 'leaf_shield_flower_stacks',
    'dream_motionless_tutelary_formation_stacks', 'god_opportunity_conform_stacks',
    'appetite', 'indigestion', 'vitality_blossom_stacks', 'prevent_gain_hp_stacks',
    'metal_spirit_chokehold_stacks', 'got_void_split_speared',
    'regen', 'internal_injury', 'wound', 'increase_atk', 'agility', 'next_turn_def',
  ];
  const owner = p => order[originalPlayers.indexOf(p)];
  const snapshot = p => Object.fromEntries(fields.filter(k => Object.hasOwn(p, k)).map(k => [k, p[k]]));
  const events = [], stack = [];
  let turn = 0;
  const methods = ['reduce_idx_hp', 'increase_idx_hp', 'increase_idx_max_hp',
    'reduce_idx_max_hp', 'increase_idx_qi', 'increase_idx_def', 'reduce_idx_def',
    'increase_idx_x_by_c', 'reduce_idx_x_by_c', 'increase_idx_debuff', 'trigger_card', 'sim_turn'];
  for (const method of methods) {
    const original = game[method];
    if (typeof original !== 'function') throw new Error('hp_observer_missing_method:' + method);
    game[method] = function(...args) {
      if (method === 'sim_turn') turn++;
      const index = method === 'trigger_card' || method === 'sim_turn' ? 0 : args[0];
      const player = this.players[index];
      const event = {
        id: events.length, parent: stack.length ? stack.at(-1) : null, turn,
        method, args: args.map(x => x === undefined ? {undefined: true} : x),
        actor: owner(this.players[0]), target: owner(player),
        before: snapshot(player), log_start: this.output.length,
      };
      events.push(event); stack.push(event.id);
      try {
        const value = Reflect.apply(original, this, args);
        event.return_value = value === undefined ? {undefined: true} : value;
        return value;
      } catch (error) {
        event.error = String(error.message);
        throw error;
      } finally {
        event.after = snapshot(player); event.log_end = this.output.length;
        stack.pop();
      }
    };
  }
  return () => ({schema: 'hp_callback_observer_v1', events,
    scope: 'simulator call boundaries, not client-recorded actions',
    limits: ['Bound methods captured before installation can run below the observer.',
      'Direct assignments inside a call are represented by before/after, not individual writes.',
      'No opening calls executed before installation are claimed observed.',
      'Absent watched properties are omitted, never filled with zero.'],
    training_label_allowed: false});
}
