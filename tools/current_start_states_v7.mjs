import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export function installCurrentStartStates(root,game) {
  const raw=fs.readFileSync(path.join(root,'data/inspection/current-start-states-v7.json'));
  const digest=crypto.createHash('sha256').update(raw).digest('hex');
  if(digest!=='bdc8242efd356f18b419a6f829a61489bfe64570bddc8ef012e1bb3617bf6947')throw new Error('Current state evidence changed');
  const facts=JSON.parse(raw),shift=facts.wind_forging.native_cap-facts.wind_forging.current_cap;
  const original=game.increase_idx_qi.bind(game),entered=new WeakSet();
  game.increase_idx_qi=(idx,amount)=>{
    const me=game.players[idx];
    if(me.wind_spirit_forging_stacks<=0 || entered.has(me))return original(idx,amount);
    // Only the native threshold sees the offset. Do not move the physique
    // reaction after other qi callbacks or change the persistent count.
    entered.add(me);me.wind_spirit_forging_gained+=shift;
    try{return original(idx,amount);}
    finally{me.wind_spirit_forging_gained-=shift;entered.delete(me);}
  };
  return {evidence_sha256:digest,wind_forging_cap:facts.wind_forging.current_cap,
    acquisition_rewards_reapplied:false,native_scheduler_reused:true,training_label_allowed:false};
}
