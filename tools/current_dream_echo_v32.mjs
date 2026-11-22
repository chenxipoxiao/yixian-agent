// Current Dream Echo: actual pre-battle hand; unresolved choices never use board fallback.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='b8d21d306e7d2f2962d39ebe1fa75d996ddefa7796c1e3063f931db59da16690';
const installed=new WeakSet();
const unresolved=reason=>{throw new Error('dream_echo_unresolved:'+reason);};
function factsAt(root) {
  const raw=fs.readFileSync(path.join(root,'data/inspection/current-dream-echo-v32.json'));
  if(crypto.createHash('sha256').update(raw).digest('hex')!==digest)throw new Error('Dream Echo evidence changed');
  const f=JSON.parse(raw);
  for(const [p,h] of Object.entries(f.source_sha256))
    if(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')!==h)throw new Error('Dream Echo source changed:'+p);
  return f;
}
export function registerDreamEcho(root,swogi) {
  const f=factsAt(root);
  for(const c of f.cards) {
    if(typeof swogi[c.runtime_id]?.card_actions!=='function')throw new Error('Pinned Dream Echo alias absent');
    swogi[c.runtime_id]=Object.freeze({...swogi[c.runtime_id],qi_cost:0,hp_cost:0,
      is_continuous:false,is_consumption:false,opening:undefined,
      card_actions:game=>{
        if(typeof game.current_dream_echo!=='function')unresolved('hand_context_required');
        game.current_dream_echo(c.raw_id,c.hp_and_max_hp);
      }});
  }
}
export function installDreamEcho(root,game,swogi,input,order=[0,1]) {
  if(input===undefined) {
    if(game.players.some(p=>p.cards.some(c=>c==='D25024'||c==='D25025')))unresolved('hand_context_required');
    return null;
  }
  const f=factsAt(root);
  if(installed.has(game))unresolved('already_installed');
  if(!input||Object.keys(input).length!==1||!Array.isArray(input.hands)||input.hands.length!==2)unresolved('invalid_hands');
  if(!Array.isArray(order)||order.length!==2||new Set(order).size!==2||!order.every(v=>v===0||v===1))unresolved('invalid_order');
  const originals=[...game.players],states=new WeakMap(),events=[];
  originals.forEach((p,seat)=>{
    const hand=input.hands[order[seat]];
    if(hand===null) {
      if(p.cards.some(c=>c==='D25024'||c==='D25025'))unresolved('hand_context_required');
      states.set(p,null);return;
    }
    if(!Array.isArray(hand)||hand.length>256||!hand.every(v=>Number.isSafeInteger(v)&&Object.hasOwn(f.hand_metadata,v)))unresolved('invalid_hand_card');
    const candidates=[...new Set(hand.filter(v=>[1,3].includes(f.hand_metadata[v].card_type)))];
    if(candidates.length>1)unresolved('multiple_targets');
    const raw=candidates.length?candidates[0]:null;
    const runtime=raw===null?null:f.hand_metadata[raw].runtime_id;
    if(raw!==null&&(!runtime||typeof swogi[runtime]?.card_actions!=='function'))unresolved('unmapped_target:'+raw);
    states.set(p,{hand:[...hand],raw,runtime,owner:order[seat]});
  });
  installed.add(game);
  game.current_dream_echo=function(raw,amount) {
    const c=f.cards.find(c=>c.raw_id===raw);
    if(!c||amount!==c.hp_and_max_hp)unresolved('invalid_grade');
    const me=this.players[0],s=states.get(me);
    if(!s)unresolved('hand_context_required');
    const before={hp:me.hp,max_hp:me.max_hp};
    this.increase_idx_max_hp(0,amount);
    this.increase_idx_hp(0,amount);
    events.push({player_index:s.owner,raw_id:raw,hp_and_max_hp:amount,
      selected_raw:s.raw,selection:'unique_prebattle_hand_target',before,
      after_prefix:{hp:me.hp,max_hp:me.max_hp},hand_mutated:false});
    if(s.runtime!==null) {
      this.log('current Dream Echo triggers hand card '+s.raw);
      this.trigger_card(s.runtime,me.currently_playing_card_idx);
    }
  };
  return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),
    recorded_parameters_as_input:false,random_selection_distribution_verified:false,
    policy_observation:false,training_label_allowed:false}:null};
}
