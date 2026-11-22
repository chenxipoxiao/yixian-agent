//1006 caches both current-HP amounts before owner-first HP and max-HP callbacks.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='c29faf481dddaeee4bebad23d0f73f9e227510c3c1ca04b6a961047e6ad97c1e',installed=new WeakSet();
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const check=(v,m)=>{if(!v)throw new Error('killing_sound_unresolved:'+m);};
export function installKillingSound(root,game,value,order=[0,1]) {
 if(value===undefined)return null;
 check(object(value)&&Object.keys(value).length===1&&Array.isArray(value.players)&&value.players.length===2
  &&value.players.every(e=>e===null||object(e)&&Object.keys(e).length===2&&e.strategy_id===1006&&typeof e.enabled==='boolean'),'ownership_and_switch_required');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 check(!installed.has(game),'already_installed');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-killing-sound-v36.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');
 const facts=JSON.parse(raw);
 for(const [p,h] of Object.entries(facts.source_sha256))
  check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 if(value.players.every(e=>e===null))return null;
 const states=new Map(game.players.map((p,i)=>[p,{index:order[i],entry:structuredClone(value.players[order[i]])}]));
 const opened=new WeakSet(),events=[],plants=game.do_plant_start_permanent_buffs.bind(game);
 // Install after v27 and before1001:1001 ->1006 ->3001 ->7069 ->plants.
 game.do_plant_start_permanent_buffs=function(...args) {
  const me=this.players[0],state=states.get(me);
  if(state.entry&&!opened.has(me)) {
   const before=this.players.map(p=>({hp:p.hp,max_hp:p.max_hp}));
   let requested=[0,0];
   if(state.entry.enabled) {
    check(before.every(p=>Number.isInteger(p.hp)&&p.hp>0&&p.hp*facts.percent<=2147483647),'positive_int32_start_hp_required');
    requested=before.map(p=>Math.floor(p.hp*facts.percent/100));
    for(let i=0;i<2;i++) {
     this.reduce_idx_hp(i,requested[i],false);
     this.reduce_idx_max_hp(i,requested[i]);
    }
    check(this.players.every(p=>p.hp>0),'opening_terminal_pending');
   }
   opened.add(me);
   events.push({strategy_id:1006,player_index:state.index,enabled:state.entry.enabled,
    phase:'owner_season_after1001_before3001_clouds_and_plants',
    target_order:this.players.map(p=>states.get(p).index),requested_reductions:requested,
    before,after:this.players.map(p=>({hp:p.hp,max_hp:p.max_hp})),both_amounts_cached_before_callbacks:true});
  }
  return plants(...args);
 };
 installed.add(game);
 return {metadata:()=>({evidence_sha256:digest,events:structuredClone(events),training_label_allowed:false})};
}
