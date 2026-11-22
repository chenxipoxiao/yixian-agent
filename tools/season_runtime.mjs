// Audited seasonal components attached to a single unmodified yisim instance.
// No input code or arbitrary method names are accepted. Full current-server
// interactions and the order relative to ordinary talent setup remain unverified.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export const IMPLEMENTED_SEASON_RUNTIME_IDS = Object.freeze([1005,1007,1008,1009,3004,3011,3012]);
const TOGGLEABLE = new Set([1005,1007,1008,1009]);
const CARD_HASH = '5f999faf2e59c6f46d816582354829397b84088e021eccba22360de9d69dd641';
const SEASON_HASH = '74c5a493f01ceef50a2bbf8038dc73e88df0869391a1b9edf6d81c4aaee41ea1';

export function validateSeasonRuntime(value, assert) {
  if (value === undefined) return null;
  assert(Array.isArray(value) && value.length === 2, 'season_runtime requires two explicit player entries.');
  return value.map((entry, index) => {
    assert(entry !== null && typeof entry === 'object' && !Array.isArray(entry), `Invalid season_runtime player ${index}.`);
    assert(Object.keys(entry).every(key => ['ids','disabled_ids'].includes(key)), 'Unknown season_runtime field.');
    assert(Array.isArray(entry.ids) && Array.isArray(entry.disabled_ids), 'season_runtime ids and disabled_ids must be arrays.');
    assert(entry.ids.every(id => Number.isSafeInteger(id) && IMPLEMENTED_SEASON_RUNTIME_IDS.includes(id)),
      'Unsupported season runtime ID; 1010 needs an independent additive percentage hook and is not implemented.');
    assert(new Set(entry.ids).size === entry.ids.length, 'Duplicate season runtime ID.');
    assert(new Set(entry.disabled_ids).size === entry.disabled_ids.length, 'Duplicate disabled season runtime ID.');
    assert(entry.disabled_ids.every(id => Number.isSafeInteger(id) && TOGGLEABLE.has(id) && entry.ids.includes(id)),
      'Only owned, toggleable season runtime IDs can be disabled.');
    return {ids:[...entry.ids],disabled_ids:[...entry.disabled_ids]};
  });
}

function readSnapshot(root, relative, expected) {
  const raw=fs.readFileSync(path.join(root,relative));
  if (crypto.createHash('sha256').update(raw).digest('hex') !== expected) {
    throw new Error(`Season runtime snapshot changed: ${relative}`);
  }
  return JSON.parse(raw);
}

export function installSeasonRuntime(game, entries, order, root, swogi, assert) {
  if (entries === null) return null;
  const configs = new Map(readSnapshot(root,'data/local/2026-11-06/season/XianMoStrategyConfig.json',SEASON_HASH).map(row=>[row.id,row]));
  const cards = new Map(readSnapshot(root,'data/local/2026-11-06/tables/CardConfig.json',CARD_HASH).map(row=>[row.id,row]));
  const names = JSON.parse(fs.readFileSync(path.join(root,'external/yisim/names.json'),'utf8'));
  const localCards = new Map();
  for (const row of names) {
    const id=String(row.id);
    if (!/^\d+1$/.test(id) || !Number.isSafeInteger(row.other_id) || row.other_id<0 || row.non_playable) continue;
    for (let grade=0;grade<3;grade++) {
      const candidate=cards.get(row.other_id+grade*10000);
      if (candidate && candidate.rarity===grade) localCards.set(String(Number(id)+grade),candidate);
    }
  }
  const events=[];
  const originalPlayers=[...game.players];
  const states=originalPlayers.map((player,seat)=>({
    input_index:order[seat], ids:new Set(entries[order[seat]].ids.filter(id=>!entries[order[seat]].disabled_ids.includes(id))),
    turn:0, no_chase:0, first_qi_bonus:0, first_attack_dive:false,
    original_cards:[...player.cards],
  }));
  const stateMap=new Map(originalPlayers.map((p,i)=>[p,states[i]]));
  const emit=(state,id,phase,details={})=>events.push({player_index:state.input_index,effect_id:id,phase,...details});
  const either=id=>states.some(state=>state.ids.has(id));
  const p0=id=>configs.get(id).otherParams[0];
  const upgradeEligible=id=>localCards.has(id) && !localCards.get(id).noUpgrade;
  if (either(1007)||either(1009)) {
    for (const player of originalPlayers) for (const id of player.cards) {
      assert(localCards.has(id), `Season upgrade requires an explicit local card classification: ${id}`);
    }
  }
  // 1009 is checked once for either owner in BeforeBattleStarted; it does not
  // double its slot count when both players own the effect.
  if (either(1009)) {
    for (let seat=0;seat<2;seat++) {
      const player=originalPlayers[seat];
      for(let slot=Math.max(0,player.cards.length-p0(1009));slot<player.cards.length;slot++) {
        const before=player.cards[slot], row=localCards.get(before);
        if(row.hidden||row.noUpgrade||row.rarity===2) continue;
        const after=String(Number(before)+(2-row.rarity));
        assert(Object.hasOwn(swogi,after)&&typeof swogi[after].card_actions==='function','Missing upgraded card implementation.');
        player.cards[slot]=after;
        emit(states[seat],1009,'battle_start',{slot,before,after});
      }
    }
  }
  for(let seat=0;seat<2;seat++) {
    const state=states[seat];
    for(const id of state.ids) {
      if([1005,1007,1008].includes(id)) {
        for(let target=0;target<2;target++) {
          const player=originalPlayers[target];
          if(id===1005) {
            states[target].no_chase+=p0(id);
            player.predicament_for_immortals_stacks+=p0(id);
          } else if(id===1007) player.finishing_touch_stacks+=p0(id);
          else player.apparition_confusion_stacks+=p0(id);
          emit(states[target],id,'battle_start',{source_player_index:state.input_index,amount:p0(id)});
        }
      } else if(id===3004) state.first_attack_dive=true;
      else if(id===3011) state.first_qi_bonus=p0(id);
    }
  }
  // Buff 281 consumes one charge only when CanUpgrade succeeds. The native
  // finishing-touch stage upgrades the copied battle deck, not persistent cards.
  const upgrade=game.try_upgrade_card.bind(game);
  game.try_upgrade_card=function(playerIdx,cardIdx) {
    const player=game.players[playerIdx], before=player.cards[cardIdx];
    if(either(1007) && !upgradeEligible(before)) return false;
    const result=upgrade(playerIdx,cardIdx);
    if(result && either(1007)) emit(stateMap.get(player),1007,'battle_card_upgrade',{slot:cardIdx,before,after:player.cards[cardIdx],attribution:'shared_buff_281_or_other_upgrade_hook'});
    return result;
  };
  const gainQi=game.increase_idx_qi.bind(game);
  game.increase_idx_qi=function(idx,amount) {
    const state=stateMap.get(game.players[idx]);
    if(amount>0 && state.first_qi_bonus>0) {
      const bonus=state.first_qi_bonus;state.first_qi_bonus=0;
      emit(state,3011,'qi_gain',{base:amount,bonus});amount+=bonus;
    }
    return gainQi(idx,amount);
  };
  const play=game.play_card.bind(game);
  game.play_card=function(...args) {
    const player=game.players[0], state=stateMap.get(player);
    const value=play(...args);
    // Client Execute checks buff 561 before the chase decision and removes
    // buff 315 even when present. It cannot bypass this temporary prohibition.
    if(state.no_chase>0) player.prevent_anti_chase=0;
    return value;
  };
  const damage=game.deal_damage_inner.bind(game);
  game.deal_damage_inner=function(amount,isAttack,sourceIdx,...rest) {
    const target=game.players[1-sourceIdx], state=stateMap.get(target);
    if(isAttack && state.first_attack_dive) {
      state.first_attack_dive=false;
      target.water_spirit_dive_stacks+=p0(3004);
      emit(state,3004,'before_first_received_attack',{dive_turns:p0(3004)});
    }
    return damage(amount,isAttack,sourceIdx,...rest);
  };
  // Native defense decay occurs before the turn-start defense grant. Further
  // ordering against other turn-start effects has not been server-calibrated.
  const decay=game.do_def_decay.bind(game);
  game.do_def_decay=function() {
    const value=decay(), state=stateMap.get(game.players[0]);
    if(state.ids.has(3012)) {
      const row=configs.get(3012);
      const amount=row.otherParams[game.players[0].round_number>=row.effectRound?1:0];
      game.increase_idx_def(0,amount);emit(state,3012,'turn_start',{turn:state.turn,amount});
    }
    return value;
  };
  const turn=game.sim_turn.bind(game);
  game.sim_turn=function() {
    const player=game.players[0], state=stateMap.get(player);state.turn++;
    try{return turn();}
    finally {
      if(state.no_chase>0) {
        state.no_chase--;
        player.predicament_for_immortals_stacks=Math.max(0,player.predicament_for_immortals_stacks-1);
        emit(state,1005,'turn_end',{turn:state.turn,remaining:state.no_chase});
      }
    }
  };
  return {metadata:()=>({
    schema_version:1,scope:'audited_season_components_with_legacy_battle',complete_effect:false,
    current_server_verified:false,implemented_ids:[...IMPLEMENTED_SEASON_RUNTIME_IDS],
    requested:structuredClone(entries),events,
    input_cards_unmodified:true,temporary_upgrades_persist_only_within_battle:true,
    snapshot_sha256:{cards:CARD_HASH,season:SEASON_HASH},
    player_state:states.map((state,seat)=>({player_index:state.input_index,turns:state.turn,
      no_chase_remaining:state.no_chase,first_qi_bonus_remaining:state.first_qi_bonus,
      first_attack_dive_pending:state.first_attack_dive,original_cards:state.original_cards,
      battle_cards:[...originalPlayers[seat].cards]})).sort((a,b)=>a.player_index-b.player_index),
    limitations:['Cross-effect ordering and all current-server interactions remain unverified.',
      'Card ID classification links are local metadata mappings, not proof of current card-effect parity.',
      '1010 is excluded: its additive 40-percentage-point reduction is independent of weaken.'],
  })};
}
