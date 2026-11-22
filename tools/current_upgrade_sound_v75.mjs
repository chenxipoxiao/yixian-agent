import {elementArraysFacts} from './current_element_arrays_v75.mjs';
import {vesselPhysiqueFacts} from './current_vessel_physique_v74.mjs';
import {cloudDefenseFacts} from './current_cloud_defense_v71.mjs';
import {physiqueShadowFacts} from './current_physique_shadow_v70.mjs';
import {frenzyMantisFacts} from './current_frenzy_mantis_v69.mjs';
//1009 changes the copied battle decks once, before ordinary opening effects.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='a2a3fdc933da1f0e18916714308a28167d4b4385d738542705e8e21dd9e09595';
const installed=new WeakSet();
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const check=(v,m)=>{if(!v)throw new Error('upgrade_sound_unresolved:'+m);};

// Pure planning keeps both copied decks unchanged if any reached level is unknown.
// The production caller supplies only the hashed client catalogue below.
export function planUpgradeSound(board,metadata,swogi,tailCount=3) {
  check(Array.isArray(board)&&board.length>=1&&board.length<=8,'invalid_raw_board');
  const after=[...board],events=[];
  for(let slot=Math.max(0,board.length-tailCount);slot<board.length;slot++) {
    let raw=after[slot],card=metadata[raw];
    check(object(card),'unknown_raw_card:'+raw);
    if(card.rarity===2||card.no_upgrade||card.hidden)continue;
    check(Number.isInteger(card.rarity)&&card.rarity>=0&&card.rarity<2,'unknown_rarity');
    const steps=2-card.rarity;
    for(let j=0;j<steps;j++) {
      card=metadata[raw];
      if(card.no_upgrade)continue;
      const next=card.upgrade_raw_id,nextCard=metadata[next];
      check(Number.isSafeInteger(next)&&object(nextCard),'missing_upgrade_level:'+raw);
      check(typeof nextCard.runtime_id==='string'&&typeof swogi[nextCard.runtime_id]?.card_actions==='function',
        'missing_upgrade_implementation:'+next);
      events.push({slot,from_raw:raw,to_raw:next,from_runtime:card.runtime_id,to_runtime:nextCard.runtime_id});
      raw=next;after[slot]=raw;
    }
  }
  return {after,events};
}

export function installUpgradeSound(root,game,swogi,value,order=[0,1]) {
  if(value===undefined)return null;
  check(object(value)&&Object.keys(value).length===2&&Array.isArray(value.players)&&value.players.length===2
    &&value.players.every(e=>e===null||object(e)&&Object.keys(e).length===2&&e.strategy_id===1009&&typeof e.enabled==='boolean'),
    'explicit_ownership_and_switch_required');
  check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
  check(!installed.has(game),'already_installed');
  const raw=fs.readFileSync(path.join(root,'data/inspection/current-upgrade-sound-v41.json'));
  check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');
  const facts=JSON.parse(raw);
  for(const [p,h] of Object.entries(facts.source_sha256))
    check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
  const aliasesRaw=fs.readFileSync(path.join(root,'data/inspection/current-hexagram-thunder-v67.json'));
  check(crypto.createHash('sha256').update(aliasesRaw).digest('hex')==='2d27273823be098c052cd474f84b24a1057d0a81ab7d847c3e675995c72aa5e3','thunder_alias_evidence_changed');
  const aliases=JSON.parse(aliasesRaw);
  for(const c of aliases.cards){
    const previous=facts.metadata[c.raw_id];
    check(previous?.runtime_id===null&&previous.rarity===c.config.rarity&&previous.hidden===c.config.hidden&&previous.no_upgrade===c.config.noUpgrade,'thunder_alias_binding_mismatch');
    previous.runtime_id=c.runtime_id;
  }
  for(const c of frenzyMantisFacts(root).cards){const m=facts.metadata[c.raw_id];check(m?.runtime_id===null&&m.hidden===true&&m.rarity===c.config.rarity&&m.no_upgrade===c.config.noUpgrade,'frenzy_mantis_alias_binding');m.runtime_id=c.runtime_id;}
  for(const c of physiqueShadowFacts(root).cards){const m=facts.metadata[c.raw_id];check(m?.runtime_id===null&&m.hidden===true&&m.rarity===c.config.rarity&&m.no_upgrade===c.config.noUpgrade,'physique_shadow_alias_binding');m.runtime_id=c.runtime_id;}
  for(const c of cloudDefenseFacts(root).cards){const m=facts.metadata[c.raw_id];check(m?.runtime_id===null&&m.hidden===true&&m.rarity===c.config.rarity&&m.no_upgrade===c.config.noUpgrade,'cloud_defense_alias_binding');m.runtime_id=c.runtime_id;}
  for(const c of vesselPhysiqueFacts(root).cards){const m=facts.metadata[c.raw_id];check(m?.runtime_id===null&&m.hidden===true&&m.rarity===c.config.rarity&&m.no_upgrade===c.config.noUpgrade,'vessel_physique_alias_binding');m.runtime_id=c.runtime_id;}
  for(const c of elementArraysFacts(root).cards){const m=facts.metadata[c.raw_id];check(m?.runtime_id===null&&m.hidden===true&&m.rarity===c.config.rarity&&m.no_upgrade===c.config.noUpgrade,'array_alias_binding');m.runtime_id=c.runtime_id;}
  check(Array.isArray(value.raw_boards)&&value.raw_boards.length===2,'explicit_raw_boards_required');
  const states=game.players.map((player,i)=>{
    const board=value.raw_boards[order[i]];
    check(Array.isArray(board)&&board.length===player.cards.length&&board.every((c,j)=>Number.isSafeInteger(c)
      &&Object.hasOwn(facts.metadata,c)&&facts.metadata[c].runtime_id===player.cards[j]),'raw_board_mismatch');
    return {player,index:order[i],board:[...board],runtime:[...player.cards]};
  });
  check(value.players.some(e=>e!==null),'owner_required');
  const enabled=value.players.some(e=>e?.enabled===true);
  const plans=enabled?states.map(s=>planUpgradeSound(s.board,facts.metadata,swogi,facts.tail_count)):states.map(s=>({after:[...s.board],events:[]}));
  const events=[];let applied=false;
  const setup=game.start_of_game_setup.bind(game);
  game.start_of_game_setup=function(...args) {
    if(!applied) {
      // Installer callbacks may inspect original identities; none may mutate the
      // deck before this prebattle boundary without an explicit new contract.
      for(const s of states)check(s.player.cards.length===s.runtime.length&&s.player.cards.every((c,j)=>c===s.runtime[j]),'earlier_deck_transform_pending');
      for(let i=0;i<states.length;i++) {
        const s=states[i],plan=plans[i];
        for(const e of plan.events)s.player.cards[e.slot]=e.to_runtime;
        events.push({player_index:s.index,phase:'before_ordinary_opening',enabled,
          before_raw:[...s.board],after_raw:[...plan.after],upgrades:structuredClone(plan.events)});
      }
      applied=true;
    }
    return setup(...args);
  };
  installed.add(game);
  return {metadata:()=>({evidence_sha256:digest,enabled,owners:structuredClone(value.players),events:structuredClone(events),
    shared_application_once:true,persistent_decks_changed:false,training_label_allowed:false})};
}
