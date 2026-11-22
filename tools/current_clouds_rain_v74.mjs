import {vesselPhysiqueFacts} from './current_vessel_physique_v74.mjs';
import {cloudDefenseFacts} from './current_cloud_defense_v71.mjs';
import {physiqueShadowFacts} from './current_physique_shadow_v70.mjs';
import {frenzyMantisFacts} from './current_frenzy_mantis_v69.mjs';
//7069 reads the original start hand and board at the owner's seasonal boundary.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='62d1addc920b5e7fe19df1192f5bd48bf8f3bad4ca8f41b71b426b090cf66fe4';
const installed=new WeakSet();
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const check=(v,m)=>{if(!v)throw new Error('clouds_rain_unresolved:'+m);};
function installExtended(root,game,value,order=[0,1]) {
  if(value===undefined)return null;
  check(object(value)&&Object.keys(value).length===1&&Array.isArray(value.players)&&value.players.length===2,'explicit_players_required');
  check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
  check(!installed.has(game),'already_installed');
  const raw=fs.readFileSync(path.join(root,'data/inspection/current-clouds-rain-v63r2.json'));
  check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');
  const facts=JSON.parse(raw);
  for(const [p,h] of Object.entries(facts.source_sha256))
    check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
  for(const c of frenzyMantisFacts(root).cards){const m=facts.metadata[c.raw_id];check(m?.runtime_id===null&&m.static_cloud===(c.base_id===401),'frenzy_mantis_cloud_binding');m.runtime_id=c.runtime_id;}
  for(const c of physiqueShadowFacts(root).cards){const m=facts.metadata[c.raw_id];check(m?.runtime_id===null&&m.static_cloud===false,'physique_shadow_cloud_binding');m.runtime_id=c.runtime_id;}
  for(const c of cloudDefenseFacts(root).cards){const m=facts.metadata[c.raw_id];check(m?.runtime_id===null&&m.static_cloud===true,'cloud_defense_cloud_binding');m.runtime_id=c.runtime_id;}
  for(const c of vesselPhysiqueFacts(root).cards){const m=facts.metadata[c.raw_id];check(m?.runtime_id===null&&m.static_cloud===false,'vessel_physique_cloud_binding');m.runtime_id=c.runtime_id;}
  const states=new Map();
  game.players.forEach((p,i)=>{
    const entry=value.players[order[i]];
    check(entry===null||object(entry)&&Object.keys(entry).length===2,'invalid_entry');
    if(entry!==null) {
      check(p.character==='sw3','non_longyao_classification_pending');
      check(Array.isArray(entry.hand)&&entry.hand.length===p.hand_count&&entry.hand.length<=256,'invalid_hand');
      check(Array.isArray(entry.board)&&entry.board.length===p.cards.length,'invalid_board');
      check([...entry.hand,...entry.board].every(c=>Number.isInteger(c)&&Object.hasOwn(facts.metadata,c)),'unknown_card');
      check(entry.board.every((c,j)=>facts.metadata[c].runtime_id===p.cards[j]),'raw_board_mismatch');
    }
    states.set(p,{entry:structuredClone(entry),index:order[i]});
  });
  if(value.players.every(e=>e===null))return null;
  const opened=new WeakSet(),events=[];
  const plants=game.do_plant_start_permanent_buffs.bind(game);
  // Installed before v27: later wrappers run1001,3001,then this7069,then plants.
  game.do_plant_start_permanent_buffs=function(...args) {
    const p=this.players[0],state=states.get(p);
    if(state.entry&&!opened.has(p)) {
      for(const field of facts.unsupported_classification_fields)
        check(p[field]===0,'conditional_classification:'+field);
      const count=cards=>cards.reduce((n,c)=>n+Number(facts.metadata[c].static_cloud),0);
      const hand=count(state.entry.hand),board=count(state.entry.board);
      const amount=Math.min(facts.cap,Math.floor((hand+board)/facts.divisor)),before=p.qi;
      opened.add(p);
      if(amount>0)this.increase_idx_qi(0,amount);
      events.push({player_index:state.index,strategy_id:7069,phase:'owner_season_after1001_and3001_before_plants',
        hand_cloud_count:hand,board_cloud_count:board,requested_qi:amount,qi_before:before,qi_after:p.qi,
        counted_original_start_arrays:true});
    }
    return plants(...args);
  };
  installed.add(game);
  return {metadata:()=>({evidence_sha256:digest,events:structuredClone(events),training_label_allowed:false})};
}

// Route only boards with new aliases through this extension.
import {installCloudsRain as previousInstall} from './current_clouds_rain_v71.mjs';
export function installCloudsRain(root,game,value,order=[0,1]){
 const ids=new Set(vesselPhysiqueFacts(root).cards.map(c=>c.raw_id));
 const extended=value?.players?.some(e=>e?.board?.some(c=>ids.has(c)));
 return extended?installExtended(root,game,value,order):previousInstall(root,game,value,order);
}
