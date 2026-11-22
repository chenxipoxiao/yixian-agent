// Local JSON bridge to an unmodified, pinned external research simulator.
// This is a single-battle reference, not a verified current-season match engine.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import readline from 'node:readline';
import {validateSeasonRuntime,installSeasonRuntime} from './season_runtime.mjs';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const engineDirectory = path.join(root, 'external', 'yisim');

class InputValidationError extends Error {}

function assert(condition, message) {
  if (!condition) throw new InputValidationError(message);
}

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

async function execute(input) {
  assert(isObject(input), 'Battle input must be a JSON object.');
  const allowed = new Set(['seed', 'max_turns', 'first_player', 'players', 'include_log','season_runtime']);
  for (const key of Object.keys(input)) assert(allowed.has(key), `Unknown battle field: ${key}`);
  assert((typeof input.seed === 'string' && input.seed.length > 0) || Number.isSafeInteger(input.seed),
    'An explicit string or integer seed is required.');
  assert(Number.isInteger(input.max_turns) && input.max_turns >= 1 && input.max_turns <= 1000,
    'max_turns must be an integer from 1 to 1000.');
  assert(input.first_player === 0 || input.first_player === 1, 'first_player must explicitly be 0 or 1.');
  assert(Array.isArray(input.players) && input.players.length === 2, 'Exactly two players are required.');
  assert(input.include_log === undefined || typeof input.include_log === 'boolean', 'include_log must be boolean.');
  const seasonRuntimeInput=validateSeasonRuntime(input.season_runtime,assert);

  // Upstream's JSON loader resolves its data files relative to the working directory.
  process.chdir(engineDirectory);
  const { GameState, ready, CHARACTER_ID_TO_NAME } = await import(pathToFileURL(path.join(engineDirectory, 'gamestate_full.js')));
  await ready;
  const { swogi } = await import(pathToFileURL(path.join(engineDirectory, 'card_info.js')));
  const game = new GameState(undefined, undefined, String(input.seed));
  const order = input.first_player === 0 ? [0, 1] : [1, 0];

  for (let seat = 0; seat < 2; seat++) {
    const source = input.players[order[seat]];
    const target = game.players[seat];
    assert(isObject(source), `players[${order[seat]}] must be an object.`);
    for (const field of ['hp', 'max_hp', 'cultivation', 'round_number', 'destiny']) {
      assert(Number.isSafeInteger(source[field]) && source[field] >= (field === 'hp' || field === 'max_hp' || field === 'round_number' ? 1 : 0),
        `Player ${order[seat]} requires a valid integer ${field}.`);
    }
    assert(source.hp <= source.max_hp, 'Starting hp cannot exceed max_hp.');
    // Restrict this first adapter to explicit full eight-slot fixtures. Empty-slot and
    // early-round semantics require separate validation against the actual game.
    assert(Array.isArray(source.cards) && source.cards.length === 8, 'This reference adapter requires exactly eight explicit card slots.');
    for (const [field, value] of Object.entries(source)) {
      assert(!['__proto__', 'prototype', 'constructor'].includes(field), `Invalid player field: ${field}`);
      if (field === 'character') {
        assert(typeof value === 'string' && Object.hasOwn(CHARACTER_ID_TO_NAME, value), `Unknown character: ${value}`);
      } else if (field === 'cards' || field === 'hand_cards') {
        assert(Array.isArray(value) && value.length <= 100, `${field} must be a card-id array.`);
        for (const id of value) {
          assert(typeof id === 'string' && Object.hasOwn(swogi, id), `Unknown card id: ${id}`);
          assert(typeof swogi[id].card_actions === 'function', `Card has no implementation: ${id}`);
        }
      } else {
        assert(Object.hasOwn(target, field), `Unsupported player field: ${field}`);
        assert(typeof target[field] === 'number' || typeof target[field] === 'boolean', `Unsupported player field type: ${field}`);
        assert(typeof value === typeof target[field], `Incorrect type for player field: ${field}`);
        if (typeof value === 'number') assert(Number.isFinite(value) && Math.abs(value) <= 1e6, `Invalid numeric player field: ${field}`);
      }
    }
    Object.assign(target, structuredClone(source));
  }

  const seasonRuntime=installSeasonRuntime(game,seasonRuntimeInput,order,root,swogi,assert);
  let turns = 0;
  const simTurn = game.sim_turn.bind(game);
  game.sim_turn = function () { turns++; return simTurn(); };
  // Upstream settles even after a turn-limit truncation. Guard this method so a
  // capped rollout never invents a win or applies terminal destiny side effects.
  const settle = game.apply_destiny_damage.bind(game);
  game.apply_destiny_damage = function () {
    const alive = game.players.map(player => player.hp > 0);
    if (game.game_over === true && alive[0] !== alive[1]) settle();
  };
  game.sim_n_turns(input.max_turns);
  const terminated = game.game_over === true && game.players.some(player => player.hp <= 0);
  const alive = game.players.map(player => player.hp > 0);
  let winner = terminated && alive[0] !== alive[1] ? order[alive[0] ? 0 : 1] : null;
  const bothNegative=terminated&&game.players.every(player=>player.hp<0);
  if(bothNegative) winner=order[game.players[0].hp>=game.players[1].hp?0:1];
  const players = [null, null];
  const fields = ['hp', 'max_hp', 'qi', 'def', 'destiny', 'cultivation', 'cards', 'next_card_index'];
  for (let seat = 0; seat < 2; seat++) {
    players[order[seat]] = Object.fromEntries(fields.map(field => [field, game.players[seat][field]]));
    for (const field of fields.filter(field => field !== 'cards')) {
      if (!Number.isFinite(players[order[seat]][field])) throw new Error(`Nonfinite simulation result: ${field}`);
    }
  }
  const result = {
    schema_version: 1,
    engine: 'sharpobject/yisim',
    engine_revision: 'c24e891283bf0e9e310ae2ba41993280ab328535',
    fidelity: 'legacy_unverified',
    current_season_verified: false,
    seed: input.seed,
    first_player: input.first_player,
    turns,
    terminated,
    truncated: !terminated,
    outcome: !terminated ? 'truncated' : winner === null ? 'simultaneous_death_unresolved' : 'win',
    winner,
    used_randomness: Boolean(game.used_randomness),
    players,
    simultaneous_negative_hp_rule_applied:bothNegative,
    simultaneous_negative_hp_legacy_settlement_skipped:bothNegative,
  };
  if(seasonRuntime) result.season_runtime=seasonRuntime.metadata();
  if (input.include_log) {
    // The upstream prints a winner even for capped rollouts; remove that assertion.
    result.log = game.output.filter(line => !/^player \d .* wins$/.test(line));
    result.log_player_order = order;
  }
  return result;
}

if (process.argv.includes('--serve')) {
  // One game at a time keeps mutable simulator state and request boundaries isolated.
  const lines = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
  for await (const line of lines) {
    try {
      let input;
      try { input = JSON.parse(line); }
      catch { throw new InputValidationError('Battle input must be valid JSON.'); }
      const result = await execute(input);
      process.stdout.write(JSON.stringify({ ok: true, result }) + '\n');
    } catch (error) {
      // Rejected input never reaches simulation; an engine failure can leave its
      // module state uncertain, so that process cannot service another battle.
      const recoverable = error instanceof InputValidationError;
      process.stdout.write(JSON.stringify({ ok: false, error: error.message, recoverable }) + '\n');
      if (!recoverable) { process.exitCode = 1; break; }
    }
  }
} else {
  try {
    const result = await execute(JSON.parse(fs.readFileSync(0, 'utf8')));
    process.stdout.write(JSON.stringify(result) + '\n');
  } catch (error) {
    process.stderr.write(JSON.stringify({ error: error.message }) + '\n');
    process.exitCode = 1;
  }
}
