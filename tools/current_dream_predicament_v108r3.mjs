// Exact348: owner-ordered passive after card openings; body loses5 HP.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='ca63bb529076460408965f61cfb2b679f10e94b11aa7ac1bd253bfa43a369451',cache=new Map(),installed=new WeakSet();
const check=(v,s)=>{if(!v)throw new Error('dream_predicament_v108r3_unresolved:'+s);};
function factsAt(root){
 if(cache.has(root))return cache.get(root);
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-hand-cap-dream-v108r3.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');
 const f=JSON.parse(raw);
 for(const [n,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,n))).digest('hex')===h,'source_changed:'+n);
 cache.set(root,f);return f;
}
export function registerDreamPredicament(root,swogi){
 const f=factsAt(root),card=swogi.D23035;
 check(card?.name==='Dream - Predicament for Immortals'&&typeof card.card_actions==='function','native_binding');
 check(f.card348.otherParams[0]===3&&f.card348.otherParams[1]===5&&f.card348.anima===0&&f.card348.hpCost===0,'config');
 // ModifyHp(-5), not an HP payment: preserve all normal HP-loss hooks.
 swogi.D23035=Object.freeze({...card,qi_cost:0,hp_cost:0,opening:undefined,
  card_actions:game=>game.reduce_idx_hp(0,5)});
}
export function installDreamPredicament(root,game,swogi,order=[0,1]){
 if(!game.players.some(p=>p.cards.includes('D23035')))return null;
 factsAt(root);check(!installed.has(game),'duplicate_install');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'order');
 const states=new Map(game.players.map((p,i)=>[p,{index:order[i],opened:false}])),events=[];
 // Disable the reference's both-player early setup. Client initializes each
 // owner's683 after its card-opening loop, before its Dream Unrestrained hook.
 game.do_dream_predicament_for_immortals_setup=function(){};
 const next=game.do_dream_unrestrained_sword_zero_setup.bind(game);
 game.do_dream_unrestrained_sword_zero_setup=function(...args){
  const p=this.players[0],s=states.get(p);check(!s.opened,'opening_twice');s.opened=true;
  const copies=this.players.reduce((n,q)=>n+q.cards.filter(id=>id==='D23035').length,0);
  const before=p.dream_predicament_for_immortals_stacks;
  this.increase_idx_x_by_c(0,'dream_predicament_for_immortals_stacks',3*copies);
  events.push({player_index:s.index,phase:'after_owner_card_openings',copies,before,after:p.dream_predicament_for_immortals_stacks});
  return next(...args);
 };
 installed.add(game);
 return {metadata:()=>({evidence_sha256:digest,events:structuredClone(events),training_label_allowed:false})};
}
