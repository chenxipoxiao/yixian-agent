// Three explicitly owned seasonal openings, installed at their client boundaries.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='771b2817894766f06062ea5589d50a2ae510d2e5afbce3b77372733734335b70',installed=new WeakSet();
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const check=(v,m)=>{if(!v)throw new Error('season_opening_unresolved:'+m);};
export function createSeasonOpeningBatch(root,game,value,order=[0,1]) {
 if(value===undefined)return null;
 check(object(value)&&Object.keys(value).length===1&&Array.isArray(value.players)&&value.players.length===2
  &&value.players.every(entries=>Array.isArray(entries)&&new Set(entries.map(e=>e?.strategy_id)).size===entries.length
   &&entries.every(e=>object(e)&&[1002,3002,7105].includes(e.strategy_id)
    &&(e.strategy_id===1002?Object.keys(e).length===2&&typeof e.enabled==='boolean':Object.keys(e).length===1))),
  'explicit_ownership_and_switch_required');
 check(value.players.some(e=>e.length),'owner_required');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 check(!installed.has(game),'already_installed');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-season-opening-v51.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');
 const facts=JSON.parse(raw);
 for(const [p,h] of Object.entries(facts.source_sha256))
  check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 const states=new Map(game.players.map((p,i)=>[p,{index:order[i],entries:new Map(value.players[order[i]].map(e=>[e.strategy_id,e])),opened:new Set()}]));
 const events=[],boundaries=new Set();
 const state=p=>({hp:p.hp,max_hp:p.max_hp,increase_atk:p.increase_atk,guard_up:p.guard_up,styx:p.styx});
 installed.add(game);
 return {
  installBoundary(id) {
   check([1002,3002,7105].includes(id)&&!boundaries.has(id),'duplicate_or_unknown_boundary');
   boundaries.add(id);
   const plants=game.do_plant_start_permanent_buffs.bind(game);
   game.do_plant_start_permanent_buffs=function(...args) {
    check(boundaries.size===3,'incomplete_boundary_installation');
    const me=this.players[0],s=states.get(me),e=s.entries.get(id);
    if(e&&!s.opened.has(id)) {
     s.opened.add(id);
     const event={strategy_id:id,player_index:s.index,phase:facts.effects[id].phase,
      target_order:this.players.map(p=>states.get(p).index),before:this.players.map(state),enabled:e.enabled!==false};
     events.push(event);
     const amount=facts.effects[id].amount;
     if(id===1002&&e.enabled) {
      this.increase_idx_x_by_c(0,'increase_atk',amount);
      this.increase_idx_x_by_c(1,'increase_atk',amount);
     } else if(id===3002)this.increase_idx_x_by_c(0,'guard_up',amount);
     else if(id===7105) {
      // Full debuff acquisition, including prevention and character healing;
      // this is not a direct assignment to the current Styx count.
      this.increase_idx_debuff(0,'styx',amount);
     }
     event.after=this.players.map(state);
     check(this.players.every(p=>p.hp>0),'opening_terminal_pending');
    }
    return plants(...args);
   };
  },
  metadata:()=>({evidence_sha256:digest,events:structuredClone(events),
   acquisition_rewards_reapplied:false,training_label_allowed:false})
 };
}
