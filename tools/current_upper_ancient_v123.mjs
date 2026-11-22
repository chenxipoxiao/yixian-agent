import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='f13f829354c296ac72ee222d4d4af3a137c71113807481b7ce6b1ae313157f8f',installed=new WeakSet();
const check=(ok,m)=>{if(!ok)throw new Error('upper_ancient_unresolved:'+m);};
export function createUpperAncient(root,game,swogi,value,order=[0,1]){
 if(value===undefined)return null;
 check(value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).length===1&&Array.isArray(value.players)&&value.players.length===2&&value.players.every(x=>typeof x==='boolean')&&value.players.some(Boolean),'explicit_owners_required');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(x=>x===0||x===1),'invalid_order');
 check(!installed.has(game),'already_installed');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-upper-ancient-v123.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');const facts=JSON.parse(raw);
 for(const [p,h] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 const states=new Map(game.players.map((p,i)=>[p,{index:order[i],owned:value.players[order[i]],opened:false}])),events=[];
 game.currentUpperAncientOwns=p=>states.get(p)?.owned===true;
 game.currentUpperAncientConsumeForce=function(idx,is_extra){
  const p=this.players[idx],s=states.get(p);check(s?.owned===true,'owner_required');
  const card=p.currently_triggering_card_id;
  check(Object.hasOwn(facts.runtime_classification,card)&&typeof swogi[card]?.card_actions==='function','unknown_actual_card:'+card);
  check(Number.isSafeInteger(p.force)&&p.force>=0,'invalid_force');
  const palm=facts.runtime_classification[card].palm,before=p.force;
  // Do not remove and refund: that would incorrectly trigger lost-force effects.
  if(!palm)this.reduce_idx_x_by_c(idx,'force',1);
  events.push({player_index:s.index,phase:'calculate_attack_force_consumption',card,palm,is_extra:is_extra===true,before,after:p.force,requested:palm?0:1});
 };
 installed.add(game);let openingInstalled=false;
 return {installOpening(){
  check(!openingInstalled,'duplicate_opening_boundary');openingInstalled=true;
  const prior=game.do_plant_start_permanent_buffs.bind(game);
  game.do_plant_start_permanent_buffs=function(...args){
   const p=this.players[0],s=states.get(p);
   if(s.owned){
    check(!s.opened,'opening_repeated');check(Number.isSafeInteger(p.max_force)&&p.max_force>=0&&p.max_force<=2147483641,'invalid_force_cap');
    const before=p.max_force;s.opened=true;this.increase_idx_x_by_c(0,'max_force',facts.force_cap_increase);
    events.push({player_index:s.index,phase:'season_opening7120_before7135',before,after:p.max_force,force:p.force,requested:facts.force_cap_increase});
   }
   return prior(...args);
  };
 },metadata:()=>({evidence_sha256:digest,events:structuredClone(events),training_label_allowed:false})};
}
