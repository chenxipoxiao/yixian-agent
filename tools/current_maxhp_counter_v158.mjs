// Client ModifyMaxHp0x313-0x31f: counter325 counts the modified request,
// including the part below the zero maxHP floor. Keep the original reducer,
// clipping, callbacks and counters672 unchanged.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='6da6a764a603e98188196e525f00b0dedf13ca4471a8ecc08cf0d2742583b132';
const cache=new Set(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('maxhp_counter_v158:'+why);};
function verify(root){
  if(cache.has(root))return;
  const bytes=fs.readFileSync(path.join(root,'data/inspection/current-maxhp-request-counter-v158.json'));
  check(crypto.createHash('sha256').update(bytes).digest('hex')===digest,'proof_changed');
  const facts=JSON.parse(bytes);
  for(const [p,h] of Object.entries(facts.source_sha256)){
    check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
  }
  cache.add(root);
}
export function installMaxHpCounter(root,game,order,nativeReducer){
  verify(root);check(!installed.has(game),'already_installed');
  check(game.reduce_idx_max_hp===nativeReducer,'unexpected_reducer_override');
  check(order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
  const seats=new Map(game.players.map((p,i)=>[p,order[i]])),events=[];
  game.reduce_idx_max_hp=function(idx,amount){
    // The original handles zero and invalid negative requests without a patch.
    if(amount<=0)return Reflect.apply(nativeReducer,this,[idx,amount]);
    const p=this.players[idx],opponent=this.players[1-idx];
    const before={hp:p.hp,max_hp:p.max_hp,max_hp_lost:p.max_hp_lost,
      times_max_hp_reduced:p.times_max_hp_reduced};
    let requested=amount+opponent.kun_wu_molten_ring_stacks;
    if(p.dream_motionless_tutelary_formation_stacks>0)requested=Math.min(requested,1);
    check(Number.isSafeInteger(requested)&&requested>=0&&requested<=2147483647,'invalid_modified_request');
    const value=Reflect.apply(nativeReducer,this,[idx,amount]);
    const actual=Math.min(requested,before.max_hp),excess=requested-actual;
    check(p.max_hp_lost===before.max_hp_lost+actual,'unexpected_counter_update');
    if(excess>0){
      check(before.max_hp_lost+requested<=2147483647,'counter_int32_overflow');
      p.max_hp_lost+=excess;
      events.push({player_index:seats.get(p),actor:seats.get(this.players[0]),
        runtime_card_id:this.players[0].currently_triggering_card_id,
        amount,modified_request:requested,actual_reduction:actual,restored_excess:excess,before,
        after:{hp:p.hp,max_hp:p.max_hp,max_hp_lost:p.max_hp_lost,
          times_max_hp_reduced:p.times_max_hp_reduced}});
    }
    return value;
  };
  installed.add(game);
  return {metadata:()=>events.length?{schema:'maxhp-counter-v158',proof_sha256:digest,events:structuredClone(events),
    recorded_intermediate_counter:false,training_label_allowed:false}:null};
}
