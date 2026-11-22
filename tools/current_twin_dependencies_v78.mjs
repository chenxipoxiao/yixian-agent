import {parrotFacts} from './current_parrot_v78.mjs';
import {elementArraysFacts} from './current_element_arrays_v75.mjs';
// Source-bound5005 transformation and current extreme unrestrained sword bodies.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='239aa5c70297af9209d66c881c03bc1815e09203d0e23dbe8985f27f2f9f9038',checked=new Map(),installed=new WeakSet();
const fail=why=>{throw new Error('twin_dependencies_unresolved:'+why);};
const check=(ok,why)=>{if(!ok)fail(why);};
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
function factsAt(root){
 if(checked.has(root))return checked.get(root);
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-twin-dependencies-v54.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');
 const f=JSON.parse(raw);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 for(const [id,c] of Object.entries(elementArraysFacts(root).extra_transform_cards)){check(!Object.hasOwn(f.metadata,id),'duplicate_array');f.metadata[id]=c;}
 for(const [id,c] of Object.entries(parrotFacts(root).extra_transform_cards)){check(!Object.hasOwn(f.metadata,id),'duplicate_parrot');f.metadata[id]=c;}
 checked.set(root,f);return f;
}
export function registerTwinDependencies(root,swogi){
 for(const c of factsAt(root).cards){
  check(!Object.hasOwn(swogi,c.runtime_id),'alias_collision');
  swogi[c.runtime_id]=Object.freeze({...swogi['601011'],name:c.config.name,names:[c.config.name],
   marking:'sw',qi_cost:0,hp_cost:0,opening:undefined,is_sword:true,is_unrestrained_sword:true,
   is_cloud_sword:false,is_spirit_seal_or_formation:false,is_continuous:false,is_consumption:false,
   card_actions:g=>{
    const count=g.players[0].unrestrained_sword_count;
    check(Number.isSafeInteger(count)&&count>=0,'invalid_unrestrained_count');
    g.atk(c.config.attack+count*c.config.otherParams[0]);g.chase();
   }});
 }
}
const snapshot=p=>Object.fromEntries(['hp','max_hp','qi','def','unrestrained_sword_count','this_card_chases'].map(k=>[k,p[k]]));
export function installTwinDependencies(root,game,swogi,value,order=[0,1]){
 check(!installed.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 const f=factsAt(root),events=[],states=new Map(),byId=new Map(f.cards.map(c=>[c.runtime_id,c])),byRuntime=new Map();
 for(const [id,c] of Object.entries(f.metadata)){const ids=byRuntime.get(c.runtime_id)??[];ids.push(Number(id));byRuntime.set(c.runtime_id,ids);}
 if(value!==undefined){
  check(object(value)&&Object.keys(value).length===2&&Array.isArray(value.players)&&value.players.length===2&&value.players.every(x=>typeof x==='boolean')&&value.players.some(Boolean),'explicit_echo_ownership_required');
  check(Array.isArray(value.raw_boards)&&value.raw_boards.length===2,'explicit_raw_boards_required');
 }
 game.players.forEach((p,i)=>{
  const board=value?.raw_boards[order[i]];
  if(value!==undefined)check(Array.isArray(board)&&board.length===p.cards.length&&board.every((id,j)=>Number.isSafeInteger(id)&&f.metadata[id]?.runtime_id===p.cards[j]),'raw_board_mismatch');
  states.set(p,{index:order[i],owned:value?.players[order[i]]??false,started:false,pending:0,identities:board?.map((raw,j)=>({raw,runtime:p.cards[j]}))});
 });
 if(value!==undefined){
  const resolve=(p,idx)=>{
   check(Number.isInteger(idx)&&idx>=0&&idx<p.cards.length,'invalid_card_index');
   const id=p.cards[idx],entry=states.get(p).identities[idx];
   if(entry.runtime!==id){const ids=byRuntime.get(id);check(ids?.length===1,'ambiguous_or_unknown_runtime:'+id);entry.raw=ids[0];entry.runtime=id;}
   return {raw:entry.raw,...f.metadata[entry.raw]};
  };
  const plants=game.do_plant_start_permanent_buffs.bind(game);
  game.do_plant_start_permanent_buffs=function(...args){
   const s=states.get(this.players[0]);
   if(!s.started){s.started=true;s.pending=s.owned?1:0;}
   return plants(...args);
  };
  const previous=game.do_continuous_tune.bind(game);
  game.do_continuous_tune=function(idx){
   const p=this.players[0],s=states.get(p);
   if(!s.owned)return previous(idx);
   check(p.continuous_tune_stacks===0,'legacy_echo_stack_present');
   if(!s.pending)return;
   const current=resolve(p,idx);
   if(!f.normal_runtime_ids.includes(current.runtime_id)||idx===0)return;
   check(p.trigger_depth===0&&[1,-1].includes(p.card_play_direction),'echo_actual_execute_required');
   const sourceIdx=this.get_prev_idx(idx),source=resolve(p,sourceIdx),raw=source.echo_copy_raw_id;
   const target=raw===null?null:f.metadata[raw];
   // The19 exception consumes781 without copying; all other unknowns fail closed.
   check(source.raw===19||target&&typeof swogi[target.runtime_id]?.card_actions==='function','copy_target_unimplemented:'+source.raw);
   s.pending=0;
   if(source.raw!==19){p.cards[idx]=target.runtime_id;s.identities[idx]={raw,runtime:target.runtime_id};}
   events.push({kind:'echo',strategy_id:5005,phase:'before_execute_upgrades_after_payment',player_index:s.index,
    slot:idx,source_slot:sourceIdx,source_raw_id:source.raw,original_raw_id:current.raw,copied_raw_id:raw,
    skipped_raw19:source.raw===19,consumed:true});
  };
 }
 const body=game.just_do_the_card_and_nothing_else.bind(game);
 game.just_do_the_card_and_nothing_else=function(card){
  const p=this.players[0],id=p.currently_triggering_card_id,c=byId.get(id);
  if(!c)return body(card);
  check(card===swogi[id],'card_body_identity');
  const e={kind:'extreme_unrestrained_one',player_index:states.get(p).index,raw_id:c.raw_id,runtime_id:id,
   slot:p.currently_triggering_card_idx,trigger_depth:p.trigger_depth,before:snapshot(p)};
  events.push(e);const result=body(card);e.after=snapshot(p);return result;
 };
 installed.add(game);
 return {metadata:()=>value===undefined&&!events.length?null:{evidence_sha256:digest,events:structuredClone(events),
  remaining_echo:[...states.values()].filter(s=>s.owned).map(s=>({player_index:s.index,started:s.started,pending:s.pending})).sort((a,b)=>a.player_index-b.player_index),
  recorded_action_log:false,training_label_allowed:false}};
}
