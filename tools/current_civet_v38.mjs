// Current Card433: HP recovery, mirror-aware temp-life request, consumption.
// A temp-life display request is not an authoritative match-state mutation.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='75a8f175659da11363f8d1d01ecb77fe1057c9e499a7ff1b547ded8acb34bf83';
const check=(ok,why)=>{if(!ok)throw new Error('civet_unresolved:'+why);};
const installed=new WeakSet();
function proof(root) {
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-civet-v38.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');
 const facts=JSON.parse(raw);
 for(const [p,h] of Object.entries(facts.source_sha256))
  check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 return facts;
}
export function registerCivet(root,swogi) {
 const facts=proof(root);
 facts.cards.forEach((c,i)=>{
  const id=facts.runtime_ids[i];check(!Object.hasOwn(swogi,id),'alias_collision');
  swogi[id]=Object.freeze({...swogi['601011'],name:'Current Civet Power',names:['Current Civet Power',c.name],
   qi_cost:0,hp_cost:0,is_consumption:true,is_add_qi:false,opening:undefined,
   card_actions:game=>{
    check(typeof game.current_civet_execute==='function','explicit_context_required');
    game.current_civet_execute(c.id);
    game.consumption();
   }});
 });
}
export function installCivet(root,game,context,order=[0,1]) {
 const facts=proof(root),cards=new Map(facts.cards.map(c=>[c.id,c]));
 check(!installed.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(v=>v===0||v===1),'invalid_order');
 if(context!==undefined)check(context!==null&&typeof context==='object'&&!Array.isArray(context)
  &&Object.keys(context).length===1&&Array.isArray(context.is_mirror)&&context.is_mirror.length===2
  &&context.is_mirror.every(v=>typeof v==='boolean'),'explicit_mirror_context_required');
 const mirrors=context===undefined?null:[...context.is_mirror];
 const originals=[...game.players],events=[];
 game.current_civet_execute=function(rawCard) {
  check(mirrors!==null,'explicit_mirror_context_required');
  check(cards.has(rawCard),'unknown_card');
  const p=this.players[0],seat=originals.indexOf(p);check(seat>=0,'unknown_owner');
  const player=order[seat],card=cards.get(rawCard),hp=p.hp;
  this.increase_idx_hp(0,card.otherParams[0]);
  events.push({player_index:player,raw_card:rawCard,phase:'card_body_after_hp_recovery',
   hp_before:hp,hp_after:p.hp,hp_requested:card.otherParams[0],is_mirror:mirrors[player],
   requested_destiny_gain:mirrors[player]?0:card.otherParams[1],
   authoritative_match_state_mutated:false});
 };
 installed.add(game);
 return {
  verifyTerminal:()=>{
   // Do not let an unmodelled positive balance affect an in-battle direct
   // destiny death/survival path in the legacy engine.
   if(events.some(e=>e.requested_destiny_gain>0))
    check(originals.every(p=>p.direct_destiny_lost===0),'direct_destiny_interaction_required');
  },
  metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),
   requested_destiny_gains:[0,1].map(i=>events.filter(e=>e.player_index===i).reduce((s,e)=>s+e.requested_destiny_gain,0)),
   authoritative_destiny_gain_resolved:false,training_label_allowed:false}:null
 };
}
