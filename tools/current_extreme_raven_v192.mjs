import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const PROOF_HASH = '1b209a40d31f12942c07506aa334e05876a94ec70b81b180a6bf72e94cfb6f07';
const cache = new Map(), registered = new WeakSet(), installed = new WeakSet();
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
const check = (ok, why) => { if (!ok) throw new Error('extreme_raven_v192:' + why); };
const int32 = n => { check(Number.isInteger(n) && n >= -2147483648 && n <= 2147483647, 'integer_range'); return n; };
export function facts192(root) {
  if (cache.has(root)) return cache.get(root);
  const raw = fs.readFileSync(path.join(root, 'data/inspection/current-extreme-raven-v192.json'));
  check(hash(raw) === PROOF_HASH, 'evidence_changed');
  const facts = JSON.parse(raw);
  for (const [p, h] of Object.entries(facts.source_sha256)) check(hash(fs.readFileSync(path.join(root, p))) === h, 'source_changed:' + p);
  cache.set(root, facts); return facts;
}
export function registerExtremeRaven192(root, swogi) {
  check(!registered.has(swogi), 'already_registered');
  for (const c of facts192(root).cards) {
    check(!Object.hasOwn(swogi, c.runtime_id), 'alias_collision');
    const flags = Object.fromEntries(Object.keys(swogi['601011']).filter(k => k.startsWith('is_')).map(k => [k, false]));
    swogi[c.runtime_id] = Object.freeze({...swogi['601011'], ...flags,
      name: c.config.name, names: [c.config.name], marking: 'sw', is_sword: true, is_spirit_sword: true, is_add_qi: true, qi_cost: 0, hp_cost: 0,
      opening: undefined, card_actions: game => game.executeExtremeRaven192(c.runtime_id)});
  }
  registered.add(swogi);
}
export function installExtremeRaven192(root, game, swogi, order = [0, 1]) {
  check(!installed.has(game), 'already_installed');
  check(Array.isArray(order) && order.length === 2 && new Set(order).size === 2 && order.every(i => i === 0 || i === 1), 'order');
  const facts = facts192(root), cards = new Map(facts.cards.map(c => [c.runtime_id, c]));
  const seats = new Map(game.players.map((p, i) => [p, order[i]])), events = [];
  game.executeExtremeRaven192 = function(id) {
    const p = this.players[0], c = cards.get(id);
    check(c && p.currently_triggering_card_id === id && swogi[id], 'card_identity');
    check(c.config.attackCount === 1 && c.config.attack === 6 && c.config.otherParams[0] === 4, 'body_parameters');
    const e = {kind: 'card_body', player_index: seats.get(p), raw_card_id: c.raw_id,
      qi_before_attack: int32(p.qi), defense_before: int32(p.def)};
    events.push(e);
    this.atk(c.config.attack);
    e.qi_after_attack = int32(p.qi);
    this.increase_idx_qi(0, c.config.anima);
    const qi = int32(p.qi);
    e.qi_after_gain_callbacks = qi;
    e.requested_defense = qi > 0 ? int32(qi * c.config.otherParams[0]) : 0;
    if (qi > 0) this.increase_idx_def(0, e.requested_defense);
    e.qi_after = int32(p.qi); e.defense_after = int32(p.def);
  };
  installed.add(game);
  return {metadata: () => events.length ? {evidence_sha256: PROOF_HASH, events: structuredClone(events),
    recorded_action_log: false, training_label_allowed: false} : null};
}
