import {installDragonQi} from './current_dragon_qi_v40.mjs';
import {registerCivet,installCivet} from './current_civet_v38.mjs';
import {installSevenStars} from './current_seven_stars_v39.mjs';
import {installKillingSound} from './current_killing_sound_v36.mjs';
import {installCloudsRain} from './current_clouds_rain_v39.mjs';
import {installHeavenSpirit} from './current_heaven_spirit_v34.mjs';
import {registerDragonTail,installDragonTail} from './current_dragon_tail_v33.mjs';
import {registerDreamEcho,installDreamEcho} from './current_dream_echo_v32.mjs';
import {installCurrentEcho} from './current_echo_formation_v31.mjs';
import {registerSpiritOutburst,installSpiritOutburst} from './current_spirit_outburst_v30.mjs';
import {registerCurrentStillness,installStillnessObserver} from './current_stillness_v29.mjs';
import {installCurrentNormalAttack} from './current_normal_attack_v28.mjs';
import {installCurrentSeasonContext} from './current_season_context_v27.mjs';
import {installCurrentYanChen} from './current_yan_chen_cards_v26.mjs';
import {installCurrentFullMoon} from './current_full_moon_v24.mjs';
import {installCurrentOnlyTraces} from './current_only_traces_v23.mjs';
import {installCurrentEngravings} from './current_engraving_effects_v21.mjs';
import {registerCurrentDelayedCards,installCurrentDelayedEffects} from './current_delayed_effects_v17.mjs';
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
registerCurrentDelayedCards(root,swogi);
registerCurrentStillness(root,swogi);
registerSpiritOutburst(root,swogi);
registerDreamEcho(root,swogi);
registerDragonTail(root,swogi);
registerCivet(root,swogi);
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const object = v => v !== null && typeof v === 'object' && !Array.isArray(v);

function execute(input) {
  assert(object(input), 'Battle must be an object');
  assert(Object.keys(input).every(k => ['players','seed','first_player','max_turns','include_trace','season_runtime','current_rules_context','season_engraving','season_transform_cards','season_full_moon','season_current_context','season_normal_attack','dream_echo','heaven_spirit','clouds_rain','killing_sound','seven_stars','civet','dragon_qi'].includes(k)), 'Unknown battle field');
  assert(Number.isSafeInteger(input.seed) || typeof input.seed === 'string' && input.seed.length, 'Explicit seed required');
  assert([0,1].includes(input.first_player), 'Explicit first player required');
  assert(Number.isSafeInteger(input.max_turns) && input.max_turns >= 1 && input.max_turns <= 1000, 'Invalid turn budget');
  assert(typeof input.include_trace === 'boolean', 'Explicit trace choice required');
  assert(Array.isArray(input.players) && input.players.length === 2, 'Exactly two players required');
  const runtime = validateSeasonRuntime(input.season_runtime, assert);
  assert(!runtime?.some(e=>e.ids.includes(3011)), 'dragon_qi_unresolved:legacy_runtime3011_not_admitted');
  const game = new GameState(undefined, undefined, String(input.seed));
  const currentPatches=installCurrentCards(root,swogi,game);
  installCurrentOnlyTraces(root,swogi,game);
  installCurrentYanChen(root,swogi,game);
  installCurrentQiPayment(game);
  installCurrentSwordMethods(game);
  installCurrentChainMethods(game,swogi);
  installCurrentDelayedEffects(root,game,swogi);
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
  installCurrentFullMoon(root,game,input.season_full_moon,order);
  installCurrentEngravings(root,game,input.season_engraving,order,input.season_transform_cards,swogi);
  const currentNormalAttack=installCurrentNormalAttack(root,game,input.season_normal_attack,order);
  const sevenStars=installSevenStars(root,game,input.seven_stars,order,input.civet!==undefined);
  const cloudsRain=installCloudsRain(root,game,input.clouds_rain,order);
  const dragonQi=installDragonQi(root,game,input.dragon_qi,order);
  const currentSeasonContext=installCurrentSeasonContext(root,game,swogi,input.season_current_context,order);
  const originals=[...game.players];
  const stillness=installStillnessObserver(game,swogi,order);
  const animalLedger=installCurrentAnimalLedger(game);
  const civet=installCivet(root,game,input.civet,order);
  const season=installSeasonRuntime(game,runtime,order,root,swogi,assert);
  const spiritOutburst=installSpiritOutburst(root,game,order);
  const currentEcho=installCurrentEcho(root,game,order);
  const dreamEcho=installDreamEcho(root,game,swogi,input.dream_echo,order);
  const dragonTail=installDragonTail(root,game,order);
  const killingSound=installKillingSound(root,game,input.killing_sound,order);
  const heavenSpirit=installHeavenSpirit(root,game,input.heaven_spirit,order);
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
  civet.verifyTerminal();
  const deathTerminal=game.game_over===true && players.some(p=>p.hp<=0);
  const officialLimitTerminal=turns===currentWindCards.official_turn_limit;
  const terminated=deathTerminal || officialLimitTerminal;
  const terminationReason=deathTerminal?'death':officialLimitTerminal?'official_64_action_limit':'diagnostic_budget_exhausted';
  let winner=null;
  if(terminated) winner=players[0].hp===players[1].hp ? input.first_player : players[0].hp>players[1].hp ? 0 : 1;
  const pending=order.map((_,i)=>animalLedger.forPlayer(originals[order.indexOf(i)]));
  return {...(dragonQi?{dragon_qi_v40:dragonQi.metadata()}:{}),...(civet.metadata()?{civet_v38:civet.metadata()}:{}),...(sevenStars?{seven_stars_v37:sevenStars.metadata()}:{}),...(killingSound?{killing_sound_v36:killingSound.metadata()}:{}),...(cloudsRain?{clouds_rain_v35:cloudsRain.metadata()}:{}),...(heavenSpirit?{heaven_spirit_v34:heavenSpirit.metadata()}:{}),...(dragonTail.metadata()?{dragon_tail_v33:dragonTail.metadata()}:{}),...(dreamEcho?.metadata()?{dream_echo_v32:dreamEcho.metadata()}:{}),...(currentEcho.metadata()?{echo_formation_v31:currentEcho.metadata()}:{}),...(spiritOutburst.metadata()?{spirit_outburst_v30:spiritOutburst.metadata()}:{}),...(stillness.metadata()?{stillness_v29:stillness.metadata()}:{}),...(currentNormalAttack?{normal_attack_v28:currentNormalAttack.metadata()}:{}),...(currentSeasonContext?{season_context_v27:currentSeasonContext.metadata()}:{}),...(pending.some(p=>p.length)?{pending_animal_match_effects:pending}:{}),terminated,truncated:!terminated,winner,turns,players,
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
  for(const battle of input) {
    try {output.push(execute(battle));}
    catch(error) {
      if(!error.message.startsWith('dragon_qi_unresolved:')&&!error.message.startsWith('civet_unresolved:')&&!error.message.startsWith('seven_stars_unresolved:')&&!error.message.startsWith('killing_sound_unresolved:')&&!error.message.startsWith('clouds_rain_unresolved:')&&!error.message.startsWith('dragon_tail_unresolved:')&&!error.message.startsWith('dream_echo_unresolved:')&&!error.message.startsWith('echo_formation_unresolved:')&&!error.message.startsWith('spirit_outburst_unresolved:')&&error.message!=='normal_attack_card_identity_unresolved:5011'&&error.message!=='engraving_temporary_card_identity_unresolved:13006'&&!error.message.startsWith('engraving_transform_unresolved:'))throw error;
      output.push({unresolved_reason:error.message,training_label_allowed:false});
    }
  }
  process.stdout.write(JSON.stringify(output));
} catch(error) {
  process.stderr.write(JSON.stringify({error:error.message}));process.exitCode=1;
}
