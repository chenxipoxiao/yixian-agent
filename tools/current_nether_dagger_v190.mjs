import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
// Filled from the immutable evidence file by the versioned preparation script.
const PROOF_HASH = 'c67faef4916597f8a0204ee43834b736367ba5240d19cd811605b00584a56fb1';
const cache = new Map(), registered = new WeakSet(), installed = new WeakSet();
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const check = (ok, reason) => { if (!ok) throw new Error('nether_dagger_v190:' + reason); };
const int32 = n => { check(Number.isSafeInteger(n) && n >= -2147483648 && n <= 2147483647, 'integer_range'); return n; };

export function facts190(root) {
  if (cache.has(root)) return cache.get(root);
  const bytes = fs.readFileSync(path.join(root, 'data/inspection/current-nether-dagger-v190.json'));
  check(hash(bytes) === PROOF_HASH, 'evidence_changed');
  const facts = JSON.parse(bytes);
  for (const [name, expected] of Object.entries(facts.source_sha256)) {
    check(hash(fs.readFileSync(path.join(root, name))) === expected, 'source_changed:' + name);
  }
  cache.set(root, facts);
  return facts;
}

export function registerNetherDagger190(root, swogi) {
  check(!registered.has(swogi), 'already_registered');
  for (const c of facts190(root).cards) {
    check(!Object.hasOwn(swogi, c.runtime_id), 'alias_collision');
    const flags = Object.fromEntries(Object.keys(swogi['601011']).filter(k => k.startsWith('is_')).map(k => [k, false]));
    swogi[c.runtime_id] = Object.freeze({...swogi['601011'], ...flags,
      name: c.config.name, names: [c.config.name], marking: 'none',
      qi_cost: 0, hp_cost: 0, opening: undefined,
      card_actions: game => game.executeNetherDagger190(c.runtime_id)});
  }
  registered.add(swogi);
}

const snapshot = p => Object.fromEntries(['hp', 'max_hp', 'def', 'internal_injury', 'hexproof'].map(k => [k, p[k]]));
export function installNetherDagger190(root, game, swogi, order = [0, 1]) {
  check(!installed.has(game), 'already_installed');
  check(Array.isArray(order) && order.length === 2 && new Set(order).size === 2 && order.every(i => i === 0 || i === 1), 'order');
  const cards = new Map(facts190(root).cards.map(c => [c.runtime_id, c]));
  const seats = new Map(game.players.map((p, i) => [p, order[i]])), events = [];
  game.executeNetherDagger190 = function(id) {
    const p = this.players[0], q = this.players[1], c = cards.get(id);
    check(c && p.currently_triggering_card_id === id && swogi[id], 'card_identity');
    check(typeof this.currentHasCardInjury303 === 'function', 'card_injury_reader_required');
    const event = {kind: 'card_body', raw_card_id: c.raw_id, player_index: seats.get(p),
      before: snapshot(p), opponent_before: snapshot(q)};
    events.push(event);
    // Client Card_99000215: own100 +=1; Attack; HasBuff303; read current100.
    this.increase_idx_debuff(0, 'internal_injury', 1);
    event.after_own_injury = snapshot(p);
    this.atk(c.config.attack);
    event.injured_card = this.currentHasCardInjury303(p);
    event.own_injury_after_attack = int32(p.internal_injury);
    if (event.injured_card) {
      event.requested_opponent_injury = int32(c.config.otherParams[0] + event.own_injury_after_attack);
      this.increase_idx_debuff(1, 'internal_injury', event.requested_opponent_injury);
    }
    event.after = snapshot(p);
    event.opponent_after = snapshot(q);
  };
  installed.add(game);
  return {metadata: () => events.length ? {evidence_sha256: PROOF_HASH, events: structuredClone(events),
    recorded_action_log: false, training_label_allowed: false} : null};
}
