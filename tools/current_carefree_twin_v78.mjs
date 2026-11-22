import {parrotFacts} from './current_parrot_v78.mjs';
import {elementArraysFacts} from './current_element_arrays_v75.mjs';
// Current selected-grid effects. No resource payment or pre-Execute upgrades repeat.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const check=(ok,msg)=>{if(!ok)throw new Error('carefree_twin_unresolved:'+msg);};
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const installed=new WeakSet();
export function installCarefreeTwin(root,game,swogi,value,order) {
 if(value===undefined)return null;
 check(object(value)&&Object.keys(value).length===2&&Array.isArray(value.players)&&value.players.length===2,'explicit_players_required');
 check(value.players.every(a=>Array.isArray(a)&&a.length<=2&&new Set(a.map(e=>e.strategy_id)).size===a.length&&a.every(e=>object(e)&&Object.keys(e).length===2&&[5001,5009].includes(e.strategy_id)&&Number.isInteger(e.slot)&&e.slot>=0&&e.slot<8)),'invalid_grid_entries');
 check(value.players.some(a=>a.length),'owner_required');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 check(!installed.has(game),'already_installed');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-carefree-twin-v53.json'));
 const digest=crypto.createHash('sha256').update(raw).digest('hex');check(digest==='fd56118358b7fc8aa53048da9c1edd8eaf22985359a0474c16c93f9e41b74196','evidence_changed');
 const facts=JSON.parse(raw);
 for(const [p,h] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 check(Array.isArray(value.raw_boards)&&value.raw_boards.length===2,'explicit_raw_boards_required');
 const extraRaw=fs.readFileSync(path.join(root,'data/inspection/current-twin-dependencies-v54.json'));
 if(crypto.createHash('sha256').update(extraRaw).digest('hex')!=='239aa5c70297af9209d66c881c03bc1815e09203d0e23dbe8985f27f2f9f9038')throw new Error('twin_dependencies_unresolved:identity_evidence_changed');
 for(const [id,c] of Object.entries(JSON.parse(extraRaw).extra_metadata)){if(Object.hasOwn(facts.metadata,id))throw new Error('twin_dependencies_unresolved:duplicate_identity');facts.metadata[id]=c;}
 for(const [id,c] of Object.entries(elementArraysFacts(root).extra_transform_cards)){check(!Object.hasOwn(facts.metadata,id),'duplicate_array');facts.metadata[id]=c;}
 for(const [id,c] of Object.entries(parrotFacts(root).extra_transform_cards)){check(!Object.hasOwn(facts.metadata,id),'duplicate_parrot');facts.metadata[id]=c;}
 const states=new Map(),byRuntime=new Map(),events=[];
 for(const [id,c] of Object.entries(facts.metadata)){const ids=byRuntime.get(c.runtime_id)??[];ids.push(Number(id));byRuntime.set(c.runtime_id,ids);}
 game.players.forEach((p,i)=>{
  const board=value.raw_boards[order[i]];
  check(Array.isArray(board)&&board.length===p.cards.length&&board.every((id,j)=>Number.isSafeInteger(id)&&facts.metadata[id]?.runtime_id===p.cards[j]),'raw_board_mismatch');
  states.set(p,{index:order[i],entries:new Map(value.players[order[i]].map(e=>[e.strategy_id,e.slot])),identities:board.map((raw,j)=>({raw,runtime:p.cards[j]}))});
 });
 const resolve=(p,idx,id)=>{
  check(Number.isInteger(idx)&&idx>=0&&idx<p.cards.length&&p.cards[idx]===id,'actual_card_identity_required');
  const entry=states.get(p).identities[idx];
  if(entry.runtime!==id){const ids=byRuntime.get(id);check(ids?.length===1,'ambiguous_or_unknown_runtime:'+id);entry.raw=ids[0];entry.runtime=id;}
  return {raw:entry.raw,...facts.metadata[entry.raw]};
 };
 // Install after130xx engraving hooks and before normal-attack hooks. All run
 // after adjacent effects and before the card body. Temporary cards are excluded.
 const cloud=game.do_cloud_sword_softheart_and_friends.bind(game);
 game.do_cloud_sword_softheart_and_friends=function(id){
  const p=this.players[0],s=states.get(p),slot=s.entries.get(5001),idx=p.currently_triggering_card_idx;
  if(slot!==undefined&&p.trigger_depth===1&&idx===slot){
   const c=resolve(p,idx,id);
   if(!c.hidden&&c.level===1){
    this.add_c_of_x(1,'this_card_chases');
    events.push({strategy_id:5001,phase:'before_card_body',player_index:s.index,slot,raw_id:c.raw,requested_chase:1});
   }
  }
  return cloud(id);
 };
 const play=game.play_card.bind(game);
 game.play_card=function(id,idx){
  const p=this.players[0],s=states.get(p),slot=s.entries.get(5009);
  if(slot===undefined||idx!==slot)return play(id,idx);
  const c=resolve(p,idx,id);
  if(c.hidden||c.level>2)return play(id,idx);
  check(p.trigger_depth===0,'temporary_execute_identity_required');
  // Client280 follows this repeat; the old native inner call runs280 sooner.
  // Do not silently reverse the two effects when the combination is present.
  check(!(p.ultimate_overcome_formation_stacks>0),'twin_ultimate_overcome_order_required');
  const result=play(id,idx);
  check(p.cards[idx]===id,'post_effect_card_identity_changed');
  const previous=p.currently_playing_card_idx,previousFake=p.dream_crash_footwork_fake_crash_fist;
  p.currently_playing_card_idx=idx;
  events.push({strategy_id:5009,phase:'repeat_execute_effect',player_index:s.index,slot,raw_id:c.raw,repeat_count:1});
  try{this.play_card_inner(id,idx);}finally{p.currently_playing_card_idx=previous;p.dream_crash_footwork_fake_crash_fist=previousFake;}
  return result;
 };
 installed.add(game);
 return {metadata:()=>({evidence_sha256:digest,events:structuredClone(events),training_label_allowed:false})};
}
