//7056: seven before-card activations; exact current-name classification.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const proofDigest='dddfad89e13af3e21ea0dc2bc8eb26fc21ee76757b9934ad8514e4d6331d6bd1',installed=new WeakSet();
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const check=(ok,why)=>{if(!ok)throw new Error('seven_stars_unresolved:'+why);};
function installExtended(root,game,value,order=[0,1]) {
 if(value===undefined)return null;
 check(object(value)&&Object.keys(value).length===1&&Array.isArray(value.players)&&value.players.length===2
  &&value.players.every(e=>e===null||object(e)&&Object.keys(e).length===2&&e.strategy_id===7056
   &&Number.isInteger(e.unlocked_slots)&&e.unlocked_slots>=3&&e.unlocked_slots<=8),'explicit_ownership_and_grids_required');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_player_order');
 check(!installed.has(game),'already_installed');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-seven-stars-v39.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===proofDigest,'evidence_changed');
 const facts=JSON.parse(raw);
 for(const [p,h] of Object.entries(facts.source_sha256))
  check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 if(value.players.every(e=>e===null))return null;
 const states=new Map(game.players.map((p,i)=>[p,{player_index:order[i],
  entry:structuredClone(value.players[order[i]]),started:false,remaining:0}]));
 for(const [p,s] of states)if(s.entry)check(s.entry.unlocked_slots===p.cards.length,'unlocked_grid_deck_mismatch');
 const openings=[],events=[],plants=game.do_plant_start_permanent_buffs.bind(game);
 game.do_plant_start_permanent_buffs=function(...args) {
  const s=states.get(this.players[0]);
  if(s.entry&&!s.started){s.started=true;s.remaining=facts.charges;
   openings.push({player_index:s.player_index,charges:s.remaining,phase:'owner_season_before_plants'});}
  return plants(...args);
 };
 //Installed after engraving/normal-attack wrappers:7056 precedes engravings.
 const cloud=game.do_cloud_sword_softheart_and_friends.bind(game);
 game.do_cloud_sword_softheart_and_friends=function(cardId) {
  const me=this.players[0],s=states.get(me);
  if(s.entry)check(s.started,'opening_not_applied');
  if(s.entry&&s.remaining>0) {
   check(Object.hasOwn(facts.runtime_classification,cardId),'unknown_card_classification:'+cardId);
   if(facts.runtime_classification[cardId]) {
    const idx=me.currently_triggering_card_idx;
    //Native nested calls expose a reference slot, not an authoritative
    //temporary CardItem grid. Refuse rather than assign its parent's grid.
    check(me.trigger_depth===1&&Number.isInteger(idx)&&idx>=0&&idx<s.entry.unlocked_slots
     &&me.currently_playing_card_idx===idx&&me.cards[idx]===cardId,'temporary_or_unknown_card_identity');
    check(me.cards.length===s.entry.unlocked_slots&&[1,-1].includes(me.card_play_direction),'grid_or_direction_changed');
    const next=this.get_next_idx(idx),expected=(idx+me.card_play_direction+s.entry.unlocked_slots)%s.entry.unlocked_slots;
    check(next===expected&&typeof me.is_star_point[next]==='boolean','next_star_grid_unresolved');
    const before={remaining:s.remaining,qi:me.qi,hp:me.hp},already=me.is_star_point[next];
    s.remaining--;
    this.become_idx_star_point(0,next);
    events.push({strategy_id:7056,player_index:s.player_index,phase:'before_card_body',card:cardId,
     slot:idx,next_slot:next,direction:me.card_play_direction,already_star:already,
     before,after:{remaining:s.remaining,qi:me.qi,hp:me.hp},trigger_depth:me.trigger_depth});
   }
  }
  return cloud(cardId);
 };
 installed.add(game);
 return {metadata:()=>({evidence_sha256:proofDigest,openings:structuredClone(openings),events:structuredClone(events),
  remaining:[...states.values()].filter(s=>s.entry).map(s=>({player_index:s.player_index,charges:s.remaining})).sort((a,b)=>a.player_index-b.player_index),
  temporary_card_identity_supported:false,training_label_allowed:false})};
}

// Route legacy-only battles through the exact frozen implementation.
import {installSevenStars as legacyInstall} from './current_seven_stars_v37.mjs';
const routed=new WeakSet();
export function installSevenStars(root,game,value,order=[0,1],civetPresent=false) {
 check(!routed.has(game),'already_installed');
 const extended=civetPresent||game.players.some(p=>p.cards.some(c=>['806141','806142','806143'].includes(c)));
 const result=extended?installExtended(root,game,value,order):legacyInstall(root,game,value,order);
 if(result)routed.add(game);
 return result;
}
