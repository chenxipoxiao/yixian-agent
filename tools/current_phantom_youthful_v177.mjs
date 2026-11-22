// Current-client Card_275 body. Preserve the reference and all prior versions.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='6edb11ed3a93f7d12ce4ef2878e38437f99f38198da5e9354d602627fd34eae8',registered=new WeakSet(),games=new WeakMap();
const check=(ok,why)=>{if(!ok)throw new Error('phantom_youthful_v177:'+why);};
const int32=n=>Number.isInteger(n)&&n>=0&&n<=2147483647;
export function registerPhantomYouthful(root,swogi){
 check(!registered.has(swogi),'already_registered');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-phantom-youthful-v177.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');
 const facts=JSON.parse(raw);
 for(const [p,h] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 for(const c of facts.cards){
  const old=swogi[c.runtime_id],cfg=c.config,divisor=cfg.otherParams[0];
  check(old&&typeof old.card_actions==='function','missing_card_identity');
  check(old.hp_cost===cfg.hpCost&&old.qi_cost===cfg.anima&&cfg.cardType===0,'cost_or_type_mismatch');
  check(cfg.attack===6&&cfg.attackCount===2&&[24,18,14].includes(divisor),'invalid_config');
  swogi[c.runtime_id]={...old,card_actions:g=>{
   const state=games.get(g),p=g.players[0];check(state&&state.seats.has(p),'missing_observer');
   check(p.currently_triggering_card_id===c.runtime_id,'actual_card_identity_required');
   const total=p.hp_gained;check(int32(total),'healing_counter_unknown_or_invalid');
   // Client performs integer division before float conversion and FloorToInt.
   const extra=Math.floor(Math.fround(Math.trunc(total/divisor))),count=cfg.attackCount+extra;
   check(int32(count),'attack_count_overflow');
   state.events.push({player_index:state.seats.get(p),raw_id:c.raw_id,runtime_id:c.runtime_id,
    healed_total:total,divisor,base_attacks:cfg.attackCount,extra_attacks:extra,attack_count:count,attack:cfg.attack});
   // The count is fixed before the first hit, including effects triggered by hits.
   for(let i=0;i<count;i++)g.atk(cfg.attack);
  }};
 }
 registered.add(swogi);
}
export function installPhantomYouthful(game,order){
 check(!games.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 const state={seats:new Map(game.players.map((p,i)=>[p,order[i]])),events:[]};games.set(game,state);
 return {metadata:()=>state.events.length?{evidence_sha256:digest,events:structuredClone(state.events),training_label_allowed:false}:null};
}
