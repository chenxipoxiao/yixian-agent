// Current Card_272: grade-specific positive recovery, then wood/cumulative-heal attack gain.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='10881320dca7fb754dd5613399aa3bba3a9657d1acfc86cb6228585eb5ff12c2',registered=new WeakSet(),games=new WeakMap();
const check=(ok,why)=>{if(!ok)throw new Error('phantom_wood_recovery_v181:'+why);};
const int32=n=>Number.isInteger(n)&&n>=-2147483648&&n<=2147483647;
export function registerPhantomWoodRecovery(root,swogi){
 check(!registered.has(swogi),'already_registered');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-phantom-wood-recovery-v181.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');
 const facts=JSON.parse(raw);
 for(const [p,h] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 for(const c of facts.cards){
  const cfg=c.config,old=swogi[c.runtime_id],cap=cfg.otherParams[1];
  check(old&&typeof old.card_actions==='function','missing_card_identity');
  check(old.qi_cost===0&&old.hp_cost===cfg.hpCost&&cfg.anima===2&&[20,30,40].includes(cap),'config_or_cost_mismatch');
  swogi[c.runtime_id]={...old,card_actions:g=>{
   const state=games.get(g),p=g.players[0];check(state&&state.seats.has(p),'observer_required');
   check(p.currently_triggering_card_id===c.runtime_id,'actual_card_identity_required');
   g.increase_idx_qi(0,cfg.anima);
   const previous=p.xuanming_recurring_hp===undefined?0:p.xuanming_recurring_hp;
   check(int32(previous)&&int32(p.hp)&&int32(previous-p.hp),'invalid_hp_history_or_difference');
   const before=p.hp,requested=Math.min(previous-p.hp,cap);
   if(requested>0)g.increase_idx_hp(0,requested);
   const wood=g.if_wood_spirit(),total=p.hp_gained;
   check(int32(total)&&total>=0,'invalid_cumulative_healing');
   const gain=wood&&total>0?cfg.otherParams[0]:0;
   if(gain)g.increase_idx_x_by_c(0,'increase_atk',gain);
   state.events.push({player_index:state.seats.get(p),raw_id:c.raw_id,runtime_id:c.runtime_id,
    previous_owner_start_hp:previous,hp_before_recovery:before,cap,requested_healing:Math.max(0,requested),
    hp_after_recovery:p.hp,wood_active:wood,cumulative_healing:total,attack_gain:gain});
  }};
 }
 registered.add(swogi);
}
export function installPhantomWoodRecovery(game,order){
 check(!games.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 const state={seats:new Map(game.players.map((p,i)=>[p,order[i]])),events:[]};games.set(game,state);
 return {metadata:()=>state.events.length?{evidence_sha256:digest,events:structuredClone(state.events),training_label_allowed:false}:null};
}
