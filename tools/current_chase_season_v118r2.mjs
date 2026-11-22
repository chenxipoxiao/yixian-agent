import {nethermindFacts} from './current_nethermind_v118.mjs';
// Current7051/7054/7112. No shared card costs or persistent decks are mutated.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='e99fc1eafc59d9048d2afa032125bf8de12eb6f9c9173831a7e0f2442ff94c8f', installed=new WeakSet();
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const check=(v,m)=>{if(!v)throw new Error('chase_season_unresolved:'+m);};
export function createChaseSeason(root,game,swogi,value,order=[0,1]) {
 if(value===undefined)return null;
 check(object(value)&&Object.keys(value).length===2&&Array.isArray(value.players)&&value.players.length===2,'explicit_players_required');
 check(value.players.every(a=>Array.isArray(a)&&new Set(a).size===a.length&&a.every(id=>[7051,7054,7112].includes(id))),'invalid_ownership');
 check(value.players.some(a=>a.length),'owner_required');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 check(Array.isArray(value.raw_boards)&&value.raw_boards.length===2,'explicit_raw_boards_required');
 check(!installed.has(game),'already_installed');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-chase-season-v57.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');
 const facts=JSON.parse(raw);
 for(const [p,h] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 const aliases=nethermindFacts(root).cards;
 for(const c of aliases){
  const m=facts.metadata[c.raw_id];
  check(m&&m.runtime_id===null&&m.rarity===c.config.rarity&&m.no_upgrade===c.config.noUpgrade
   &&m.hidden===c.config.hidden&&!m.name_has_thunder&&!m.desc_has_chase,'new_alias_metadata_mismatch');
  facts.metadata[c.raw_id]={...m,runtime_id:c.runtime_id};
 }
 const states=new Map(),byRuntime=new Map(),events=[],boundaries=new Set();
 for(const [raw,c] of Object.entries(facts.metadata)) {
  if(c.runtime_id===null)continue;
  const ids=byRuntime.get(c.runtime_id)??[];ids.push(Number(raw));byRuntime.set(c.runtime_id,ids);
 }
 game.players.forEach((p,i)=>{
  const board=value.raw_boards[order[i]];
  check(Array.isArray(board)&&board.length===p.cards.length&&board.every((raw,j)=>Number.isSafeInteger(raw)&&facts.metadata[raw]?.runtime_id===p.cards[j]),'raw_board_mismatch');
  states.set(p,{index:order[i],ids:new Set(value.players[order[i]]),opened:new Set(),
   identities:board.map((raw,j)=>({raw,runtime:p.cards[j]}))});
 });
 const resolve=(p,slot,id)=>{
  const s=states.get(p);
  check(s&&Number.isInteger(slot)&&slot>=0&&slot<p.cards.length&&p.cards[slot]===id,'actual_card_identity_required');
  const entry=s.identities[slot];
  check(entry!==undefined,'deck_shape_changed');
  if(entry.runtime!==id) {
   const ids=byRuntime.get(id);check(ids?.length===1,'ambiguous_or_unknown_runtime:'+id);
   entry.raw=ids[0];entry.runtime=id;
  }
  return {raw:entry.raw,...facts.metadata[entry.raw]};
 };
 const emit=(p,id,phase,extra={})=>{const e={strategy_id:id,player_index:states.get(p).index,phase,...extra};events.push(e);return e;};
 const nativeChase=game.process_this_card_chases.bind(game);
 game.process_this_card_chases=function(...args){
  const p=this.players[0],s=states.get(p),before=p.chases;
  const result=nativeChase(...args);
  if(s.ids.has(7112)&&p.chases!==before) {
   check(p.chases===before+1,'unexpected_chase_count_delta');
   const e=emit(p,7112,'accepted_chase_before235',{requested_heal:facts.effects['7112'].heal,before:{hp:p.hp,max_hp:p.max_hp,chases:before}});
   this.increase_idx_hp(0,facts.effects['7112'].heal);
   e.after={hp:p.hp,max_hp:p.max_hp,chases:p.chases};
  }
  return result;
 };
 installed.add(game);
 return {
  reduceQiCost(id,slot,cost) {
   const p=game.players[0],s=states.get(p);
   if(!s.ids.has(7051))return cost;
   check(Number.isSafeInteger(cost)&&cost>=0&&cost<=2147483647,'invalid_qi_cost');
   const c=resolve(p,slot,id);
   if(!c.desc_has_chase)return cost;
   const after=Math.max(0,cost-1);
   emit(p,7051,'before_qi_payment',{slot,raw_id:c.raw,runtime_id:id,before_cost:cost,after_cost:after});
   return after;
  },
  installBoundary(id) {
   check([7054,7112].includes(id)&&!boundaries.has(id),'duplicate_or_unknown_boundary');boundaries.add(id);
   const previous=game.do_plant_start_permanent_buffs.bind(game);
   game.do_plant_start_permanent_buffs=function(...args){
    check(boundaries.size===2,'incomplete_boundary_installation');
    const p=this.players[0],s=states.get(p);
    if(s.ids.has(id)&&!s.opened.has(id)) {
     s.opened.add(id);
     if(id===7054) {
      const before=[...p.cards];let upgraded=null;
      for(let slot=0;slot<p.cards.length;slot++) {
       const c=resolve(p,slot,p.cards[slot]);
       // Unlike1009, this source branch has no hidden-card exclusion.
       if(c.no_upgrade||!c.name_has_thunder&&!c.desc_has_chase)continue;
       const next=facts.metadata[c.raw+10000];
       check(next&&typeof next.runtime_id==='string'&&typeof swogi[next.runtime_id]?.card_actions==='function','upgrade_target_unimplemented:'+c.raw);
       p.cards[slot]=next.runtime_id;s.identities[slot]={raw:c.raw+10000,runtime:next.runtime_id};
       upgraded={slot,from_raw:c.raw,to_raw:c.raw+10000,from_runtime:c.runtime_id,to_runtime:next.runtime_id};break;
      }
      emit(p,7054,'owner_season_start',{before,after:[...p.cards],upgrade:upgraded,persistent_deck_changed:false});
     }else {
      const e=emit(p,7112,'owner_season_start',{before:{hp:p.hp,max_hp:p.max_hp},requested_max_hp:facts.effects['7112'].max_hp});
      this.increase_idx_max_hp(0,facts.effects['7112'].max_hp);e.after={hp:p.hp,max_hp:p.max_hp};
     }
    }
    return previous(...args);
   };
  },
  metadata:()=>({evidence_sha256:digest,...(value.raw_boards.some(a=>a.some(raw=>aliases.some(c=>c.raw_id===raw)))?{nethermind_alias_evidence_sha256:'f326da01c1e395d0343c8e50a9434771263d3d5a353db9e945d3f57ce71b4e5f'}:{}),events:structuredClone(events),persistent_decks_changed:false,
   acquisition_rewards_reapplied:false,training_label_allowed:false})
 };
}
