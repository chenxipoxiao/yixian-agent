import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const PROOF_HASH = 'ad7087b733a5b2da84808edce834685ca5bd0e8a39fc413f757cf36fdf4e3202';
const cache = new Map(), registered = new WeakSet(), installed = new WeakSet();
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
const check = (ok, why) => { if (!ok) throw new Error('quicksand_seal_v191:' + why); };
const int32 = n => { check(Number.isInteger(n) && n >= -2147483648 && n <= 2147483647, 'integer_range'); return n; };
export function facts191(root) {
  if (cache.has(root)) return cache.get(root);
  const raw = fs.readFileSync(path.join(root, 'data/inspection/current-quicksand-seal-v191.json'));
  check(hash(raw) === PROOF_HASH, 'evidence_changed');
  const facts = JSON.parse(raw);
  for (const [p, h] of Object.entries(facts.source_sha256)) check(hash(fs.readFileSync(path.join(root, p))) === h, 'source_changed:' + p);
  cache.set(root, facts); return facts;
}
export function registerQuicksandSeal191(root, swogi) {
  check(!registered.has(swogi), 'already_registered');
  for (const c of facts191(root).cards) {
    check(!Object.hasOwn(swogi, c.runtime_id), 'alias_collision');
    const flags = Object.fromEntries(Object.keys(swogi['601011']).filter(k => k.startsWith('is_')).map(k => [k, false]));
    swogi[c.runtime_id] = Object.freeze({...swogi['601011'], ...flags,
      name: c.config.name, names: [c.config.name], marking: 'none', qi_cost: 0, hp_cost: 0,
      opening: undefined, card_actions: game => game.executeQuicksandSeal191(c.runtime_id)});
  }
  registered.add(swogi);
}
export function installQuicksandSeal191(root, game, swogi, order = [0, 1]) {
  check(!installed.has(game), 'already_installed');
  check(Array.isArray(order) && order.length === 2 && new Set(order).size === 2 && order.every(i => i === 0 || i === 1), 'order');
  const facts = facts191(root), cards = new Map(facts.cards.map(c => [c.runtime_id, c]));
  const divisor = facts.cards.find(c => c.raw_id === 441).config.otherParams[0];
  check(divisor === 4, 'base_parameter');
  const seats = new Map(game.players.map((p, i) => [p, order[i]])), events = [];
  game.executeQuicksandSeal191 = function(id) {
    const p = this.players[0], c = cards.get(id);
    check(c && p.currently_triggering_card_id === id && swogi[id], 'card_identity');
    const e = {kind: 'card_body', player_index: seats.get(p), raw_card_id: c.raw_id,
      defense_before: int32(p.def), earth_before: int32(p.activate_earth_spirit_stacks)};
    events.push(e);
    this.increase_idx_def(0, c.config.def);
    this.increase_idx_activate(0, 'activate_earth_spirit_stacks', 1);
    this.chase();
    e.defense_after = int32(p.def); e.earth_after = int32(p.activate_earth_spirit_stacks);
  };
  // All four frozen schedulers call hard bamboo immediately before cat365.
  // HasCardInDeck reads the current battle deck, regardless of whether played.
  const bamboo = game.do_hard_bamboo.bind(game);
  game.do_hard_bamboo = function(...args) {
    const result = bamboo(...args), p = this.players[0], q = this.players[1];
    const present = p.cards.filter(id => cards.has(id));
    if (present.length) {
      const defense = int32(p.def), damage = Math.trunc(defense / divisor);
      const e = {kind: 'turn_end_after282_before365', player_index: seats.get(p),
        raw_cards_present: present.map(id => cards.get(id).raw_id), defense,
        requested_damage: damage > 0 ? damage : 0, opponent_hp_before: int32(q.hp), opponent_def_before: int32(q.def)};
      events.push(e);
      if (damage > 0) this.deal_damage(damage);
      e.opponent_hp_after = int32(q.hp); e.opponent_def_after = int32(q.def);
    }
    return result;
  };
  installed.add(game);
  return {metadata: () => events.length ? {evidence_sha256: PROOF_HASH, events: structuredClone(events),
    recorded_action_log: false, training_label_allowed: false} : null};
}
