//3011 activates at its owner's seasonal opening;543 is consumed before qi callbacks.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='6f08e2fb8060f2beae321cf786c951aa912e69804d4e8f2e7062ce369b5948a0';
const installed=new WeakSet();
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const check=(v,m)=>{if(!v)throw new Error('dragon_qi_unresolved:'+m);};
export function installDragonQi(root,game,value,order=[0,1]) {
 if(value===undefined)return null;
 check(object(value)&&Object.keys(value).length===1&&Array.isArray(value.players)&&value.players.length===2
  &&value.players.every(e=>e===null||object(e)&&Object.keys(e).length===1&&e.strategy_id===3011),'explicit_ownership_required');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 check(!installed.has(game),'already_installed');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-dragon-qi-v40.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');
 const facts=JSON.parse(raw);
 for(const [p,h] of Object.entries(facts.source_sha256))
  check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 if(value.players.every(e=>e===null))return null;
 const states=new Map(game.players.map((p,i)=>[p,{index:order[i],owned:value.players[order[i]]!==null,opened:false,remaining:0}]));
 const events=[],plants=game.do_plant_start_permanent_buffs.bind(game);
 // Install after7069, before3001/1006/1001: the wrappers execute in reverse order.
 game.do_plant_start_permanent_buffs=function(...args) {
  const state=states.get(this.players[0]);
  if(state.owned&&!state.opened) {
   state.opened=true;state.remaining=facts.bonus;
   events.push({kind:'owner_season_start',player_index:state.index,client_buff:543,remaining:state.remaining});
  }
  return plants(...args);
 };
 const qi=game.increase_idx_qi.bind(game);
 game.increase_idx_qi=function(idx,amount) {
  const p=this.players[idx],state=states.get(p);
  check(state!==undefined,'invalid_target');
  if(!state.owned)return qi(idx,amount);
  // This is the gain API; spending/reduction stays on reduce_idx_qi.
  check(Number.isSafeInteger(amount)&&amount>=0&&amount<=2147483647,'nonnegative_int32_gain_required');
  if(amount===0||state.remaining===0)return qi(idx,amount);
  check(amount+state.remaining<=2147483647,'int32_bonus_overflow');
  const bonus=state.remaining;state.remaining=0;
  const event={kind:'first_positive_qi',player_index:state.index,requested:amount,bonus,
   delegated_amount:amount+bonus,before:{qi:p.qi,hp:p.hp,physique:p.physique},consumed_before_callbacks:true};
  events.push(event);
  const result=qi(idx,amount+bonus);
  event.after={qi:p.qi,hp:p.hp,physique:p.physique};
  return result;
 };
 installed.add(game);
 return {metadata:()=>({evidence_sha256:digest,events:structuredClone(events),
  remaining:[...states.values()].map(s=>({player_index:s.index,owned:s.owned,opened:s.opened,bonus:s.remaining})),
  acquisition_rewards_reapplied:false,training_label_allowed:false})};
}
