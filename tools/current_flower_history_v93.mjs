import {dreamBasicsFacts} from './current_dream_basics_v93.mjs';
import fs from 'node:fs';
import {dreamIntentWaterFacts} from './current_dream_intent_water_v92.mjs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='3e07302be00c8eb7a4c9a6984808c52e8a16818dfb027c72ee95e4c31ff06594',cache=new Map(),installed=new WeakSet();
const check=(v,m)=>{if(!v)throw new Error('flower_history_unresolved:'+m);};
export function flowerHistoryFacts(root){
 if(cache.has(root))return cache.get(root);
 const b=fs.readFileSync(path.join(root,'data/inspection/current-flower-history-v91.json'));
 check(crypto.createHash('sha256').update(b).digest('hex')===digest,'evidence_changed');const f=JSON.parse(b);
 for(const [n,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,n))).digest('hex')===h,'source_changed:'+n);
 cache.set(root,f);return f;
}
export function installFlowerHistory(root,game,swogi,order=[0,1]){
 check(!installed.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 const f=flowerHistoryFacts(root),events=[],state=new Map(game.players.map((p,i)=>[p,{index:order[i],waterCount:0}]));
 const classify=id=>{const c=f.runtime_classification[id]??dreamIntentWaterFacts(root).new_classification[id]??dreamBasicsFacts(root).new_classification[id];check(c&&typeof swogi[id]?.card_actions==='function','unknown_card:'+id);return c;};
 const nativeBookkeeping=game.do_elemental_spirit_stuff.bind(game);
 game.do_elemental_spirit_stuff=function(id){
  const p=this.players[0],result=nativeBookkeeping(id);
  if(p.blossom_dance_stacks>0&&classify(id).is_water_name){
   const s=state.get(p);check(s.waterCount<2147483647,'counter_overflow');s.waterCount++;
   events.push({kind:'completed_water_card_766',player_index:s.index,runtime_id:id,trigger_depth:p.trigger_depth,water_count:s.waterCount});
  }
  return result;
 };
 const nativeCycle=game.do_cycle_of_five_elements_and_friends.bind(game);
 game.do_cycle_of_five_elements_and_friends=function(id){
  const p=this.players[0];if(p.blossom_dance_stacks<=0)return nativeCycle(id);
  const c=classify(id),s=state.get(p),generating=this.cards_have_generating_interaction(p.last_card_id,id);
  // Same native ordering for cycle-of-five-elements and the101 resource grant.
  // The315 request below is an independent IL branch, not inside generating.
  if(generating){
   if(p.p2_cycle_of_five_elements_stacks>0)this.increase_idx_def(0,3*p.p2_cycle_of_five_elements_stacks);
   if(p.p3_cycle_of_five_elements_stacks>0)this.increase_idx_qi(0,p.p3_cycle_of_five_elements_stacks);
   if(p.p4_cycle_of_five_elements_stacks>0){const n=4*p.p4_cycle_of_five_elements_stacks;this.add_c_of_x(n,'max_hp');this.heal(n);}
   if(p.p5_cycle_of_five_elements_stacks>0)this.add_c_of_x(4*p.p5_cycle_of_five_elements_stacks,'penetrate');
   this.increase_idx_qi(0,f.talent101.otherParams[0]);this.add_c_of_x(f.talent101.otherParams[1],'max_hp');this.heal(f.talent101.otherParams[1]);
  }
  if(c.is_peach_base20&&s.waterCount>0){
   this.chase();events.push({kind:'flower_peach_315',player_index:s.index,runtime_id:id,trigger_depth:p.trigger_depth,
    water_count:s.waterCount,previous_card:p.last_card_id,generating_interaction:generating});
  }
 };
 installed.add(game);
 return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),training_label_allowed:false}:null};
}
