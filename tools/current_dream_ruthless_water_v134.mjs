// Fixed current-client level3 values. Preserve the pinned reference and older entries.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const digest = '6a937699f20b787ec05fc2d487cbd100b90ea03585a2655bb551246b230025f6';
const registered = new WeakSet();
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
const check = (ok, reason) => {if (!ok) throw new Error('dream_ruthless_water_v134:' + reason);};

export function registerDreamRuthlessWater(root, swogi) {
  check(!registered.has(swogi), 'already_registered');
  const raw = fs.readFileSync(path.join(root, 'data/inspection/current-dream-ruthless-water-v134.json'));
  check(hash(raw) === digest, 'evidence_changed');
  const facts = JSON.parse(raw);
  for (const [name, expected] of Object.entries(facts.source_sha256)) {
    check(hash(fs.readFileSync(path.join(root, name))) === expected, 'source_changed:' + name);
  }
  const c = facts.cards.find(x => x.raw_id === 20266);
  check(c?.runtime_id === '724043' && c.config.anima === 0 &&
        JSON.stringify(c.config.otherParams) === '[3,1]', 'configuration_contract');
  const old = swogi[c.runtime_id];
  check(old?.qi_cost === 1 && typeof old.card_actions === 'function', 'reference_contract');
  swogi[c.runtime_id] = {...old, qi_cost: -c.config.anima, card_actions: game => {
    game.add_enemy_c_of_x(c.config.otherParams[0], 'internal_injury');
    game.continuous();
    game.increase_idx_x_by_c(1, 'm_ruthless_water_stacks', c.config.otherParams[1]);
  }};
  registered.add(swogi);
  return {evidence_sha256: digest, changed_raw_card_ids: [20266]};
}
