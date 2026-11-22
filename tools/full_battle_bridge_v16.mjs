import {registerCurrentSeasonCards} from './current_season_cards_v16.mjs';
import {installCurrentQiPayment} from './current_qi_payment_v15.mjs';
import {registerCurrentAnimalCards,installCurrentAnimalLedger} from './current_animal_cards_v14.mjs';
// Versioned, batched full-battle diagnostics. The pinned reference is unmodified.
// No replay winner, terminal HP or recorded damage is accepted by this process.
import fs from 'node:fs';
import {registerCurrentChainCards,installCurrentChainMethods} from './current_chain_cards_v11.mjs';
import {installCurrentVineDivination} from './current_vine_divination_v10.mjs';
import {installCurrentClearHeart} from './current_clear_heart_v9.mjs';
import {installCurrentWindCards} from './current_wind_cards_v8.mjs';
import {installCurrentStartStates} from './current_start_states_v7.mjs';
import {registerCurrentSectCards} from './current_sect_cards_v6.mjs';
import {registerCurrentCloudCards} from './current_cloud_cards_v5.mjs';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {validateSeasonRuntime, installSeasonRuntime} from './season_runtime.mjs';
import {installCurrentCards} from './current_battle_patches.mjs';
import {registerCurrentSwordCards, installCurrentSwordMethods} from './current_sword_cards.mjs';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const directory = path.join(root, 'external', 'yisim');
process.chdir(directory);
const {GameState, ready, CHARACTER_ID_TO_NAME} = await import(pathToFileURL(path.join(directory, 'gamestate_full.js')));
await ready;
const {swogi} = await import(pathToFileURL(path.join(directory, 'card_info.js')));
const currentSwordCards=registerCurrentSwordCards(root,swogi);
const currentCloudCards=registerCurrentCloudCards(root,swogi);
const currentSectCards=registerCurrentSectCards(root,swogi);
const currentChainCards=registerCurrentChainCards(root,swogi);
registerCurrentAnimalCards(root,swogi);
registerCurrentSeasonCards(root,swogi);
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const object = v => v !== null && typeof v === 'object' && !Array.isArray(v);

function execute(input) {
  assert(object(input), 'Battle must be an object');
  assert(Object.keys(input).every(k => ['players','seed','first_player','max_turns','include_trace','season_runtime','current_rules_context'].includes(k)), 'Unknown battle field');
  assert(Number.isSafeInteger(input.seed) || typeof input.seed === 'string' && input.seed.length, 'Explicit seed required');
  assert([0,1].includes(input.first_player), 'Explicit first player required');
  assert(Number.isSafeInteger(input.max_turns) && input.max_turns >= 1 && input.max_turns <= 1000, 'Invalid turn budget');
  assert(typeof input.include_trace === 'boolean', 'Explicit trace choice required');
  assert(Array.isArray(input.players) && input.players.length === 2, 'Exactly two players required');
  const runtime = validateSeasonRuntime(input.season_runtime, assert);
  const game = new GameState(undefined, undefined, String(input.seed));
  const currentPatches=installCurrentCards(root,swogi,game);
  installCurrentQiPayment(game);
  installCurrentSwordMethods(game);
  installCurrentChainMethods(game,swogi);
  const currentStartStates=installCurrentStartStates(root,game);
  const currentClearHeart=installCurrentClearHeart(root,game);
  const currentVineDivination=installCurrentVineDivination(root,swogi,game);
  const order = input.first_player === 0 ? [0,1] : [1,0];
  const ctx=input.current_rules_context;
  if(ctx!==undefined)assert(object(ctx)&&Object.keys(ctx).length===1&&Array.isArray(ctx.realms)&&ctx.realms.length===2&&ctx.realms.every(r=>Number.isInteger(r)&&r>=1&&r<=6),'Explicit two start realms required');
  const currentWindCards=installCurrentWindCards(root,swogi,game,ctx?order.map(i=>ctx.realms[i]):undefined);
  const initial = [];
  for (let seat=0; seat<2; seat++) {
    const source=input.players[order[seat]], target=game.players[seat];
    assert(object(source), 'Invalid player');
    for (const field of ['hp','max_hp','cultivation','round_number','destiny','qi','def','physique','max_physique','hand_count']) {
      assert(Number.isSafeInteger(source[field]) && source[field] >= (['hp','max_hp','round_number'].includes(field) ? 1 : 0), `Explicit ${field} required`);
    }
    assert(source.hp <= source.max_hp, 'HP exceeds maximum');
    assert(Object.hasOwn(CHARACTER_ID_TO_NAME, source.character), 'Unknown character');
    assert(Array.isArray(source.cards) && source.cards.length >= 1 && source.cards.length <= 8, 'Require 1–8 explicit unlocked slots; never pad decks');
    for (const [field,value] of Object.entries(source)) {
      assert(!['__proto__','constructor','prototype'].includes(field), 'Invalid field');
      if (field === 'character') continue;
      if (field === 'cards') {
        assert(value.every(id => typeof id === 'string' && Object.hasOwn(swogi,id) && typeof swogi[id].card_actions === 'function'), 'Unimplemented card');
      } else if (field === 'swordplay_talent_cards') {
        assert(Array.isArray(value) && value.length<=64 && value.every(v=>typeof v==='string' && Object.hasOwn(swogi,v+'1')), 'Invalid learned families');
      } else if (field === 'five_elements_pure_vase_cards') {
        assert(Array.isArray(value) && [0,3].includes(value.length) && value.every(v=>v===null || typeof v==='string' && Object.hasOwn(swogi,v)), 'Invalid vase slots');
      } else {
        assert(Object.hasOwn(target,field) && ['number','boolean'].includes(typeof target[field]), `Unsupported field ${field}`);
        assert(typeof target[field] === typeof value && (typeof value !== 'number' || Number.isFinite(value) && Math.abs(value) <= 1e6), `Invalid ${field}`);
        assert(!field.startsWith('resonance_') || value === 0, 'Current ranked season has no resonance');
      }
    }
    Object.assign(target,structuredClone(source));
    initial[order[seat]]=structuredClone(source);
  }
  const originals=[...game.players];
  const animalLedger=installCurrentAnimalLedger(game);
  const season=installSeasonRuntime(game,runtime,order,root,swogi,assert);
  const snapshot = () => {
    const output=[null,null];
    originals.forEach((p,seat) => {
      const fields=['hp','max_hp','qi','def','cultivation','next_card_index','kindness_tune_stacks','direct_destiny_lost'];
      output[order[seat]]=Object.fromEntries(fields.map(k=>[k,p[k]]));
      output[order[seat]].cards=[...p.cards];
      assert(fields.every(k=>Number.isFinite(p[k])), 'Non-finite battle state');
    });
    return output;
  };
  const trace=[];let turns=0;
  const simTurn=game.sim_turn.bind(game);
  game.sim_turn=()=>{
    const actor=order[originals.indexOf(game.players[0])];
    const before=input.include_trace ? snapshot() : null;
    simTurn();turns++;
    if(input.include_trace) trace.push({turn:turns,actor,before,after:snapshot()});
  };
  // Only our explicit settlement may later charge destiny, and only once.
  game.apply_destiny_damage=()=>{};
  // A terminal during setup needs its own client death/turn-count boundary.
  // Keep it unresolved instead of inventing an extra action or winner.
  const setup=game.start_of_game_setup.bind(game);
  game.start_of_game_setup=()=>{
    setup();
    assert(game.players.every(p=>p.hp>0),'opening_terminal_pending');
  };
  game.sim_n_turns(Math.min(input.max_turns,currentWindCards.official_turn_limit));
  const players=snapshot();
  const deathTerminal=game.game_over===true && players.some(p=>p.hp<=0);
  const officialLimitTerminal=turns===currentWindCards.official_turn_limit;
  const terminated=deathTerminal || officialLimitTerminal;
  const terminationReason=deathTerminal?'death':officialLimitTerminal?'official_64_action_limit':'diagnostic_budget_exhausted';
  let winner=null;
  if(terminated) winner=players[0].hp===players[1].hp ? input.first_player : players[0].hp>players[1].hp ? 0 : 1;
  const pending=order.map((_,i)=>animalLedger.forPlayer(originals[order.indexOf(i)]));
  return {...(pending.some(p=>p.length)?{pending_animal_match_effects:pending}:{}),terminated,truncated:!terminated,winner,turns,players,
    hp_delta:terminated ? players[0].hp-players[1].hp : null,
    used_randomness:Boolean(game.used_randomness),initial,trace,
    log:input.include_trace ? game.output.filter(line=>!/^player \d .* wins$/.test(line)) : [],
    log_player_order:order,season_runtime:season?.metadata() ?? null,
    legacy_destiny_settlement_applied:false,current_server_verified:false,current_patches:currentPatches,current_sword_cards:currentSwordCards,current_cloud_cards:currentCloudCards,current_sect_cards:currentSectCards,current_start_states:currentStartStates,current_chain_cards:currentChainCards,current_vine_divination:currentVineDivination,current_clear_heart:currentClearHeart,current_wind_cards:currentWindCards,termination_reason:terminationReason,
    training_label_allowed:false,scope:'complete_reference_battle_with_current_snapshot_inputs'};
}

try {
  const input=JSON.parse(fs.readFileSync(0,'utf8'));
  assert(Array.isArray(input) && input.length<=1000, 'Bounded battle batch required');
  const output=[];
  for(const battle of input) output.push(execute(battle));
  process.stdout.write(JSON.stringify(output));
} catch(error) {
  process.stderr.write(JSON.stringify({error:error.message}));process.exitCode=1;
}
