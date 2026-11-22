//1001 runs in its owner's seasonal opening, preserving normal qi callbacks.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='fe5f6d67feef8465c39109bc001a6bb3f1afc4646d729194df8eb061ccd8d884';
const installed=new WeakSet();
export function installHeavenSpirit(root,game,value,order=[0,1]) {
  if(value===undefined)return null;
  const valid=value!==null && typeof value==='object' && !Array.isArray(value)
    && Object.keys(value).length===1 && Array.isArray(value.players) && value.players.length===2
    && value.players.every(e=>e===null || e!==null && typeof e==='object' && !Array.isArray(e)
      && Object.keys(e).length===2 && e.strategy_id===1001 && typeof e.enabled==='boolean');
  if(!valid)throw new Error('Explicit Heaven Spirit ownership and switch required');
  if(!Array.isArray(order)||order.length!==2||new Set(order).size!==2||!order.every(i=>i===0||i===1))
    throw new Error('Explicit Heaven Spirit player order required');
  if(installed.has(game))throw new Error('Heaven Spirit already installed');
  const raw=fs.readFileSync(path.join(root,'data/inspection/current-heaven-spirit-v34.json'));
  if(crypto.createHash('sha256').update(raw).digest('hex')!==digest)throw new Error('Heaven Spirit evidence changed');
  const facts=JSON.parse(raw);
  for(const [p,h] of Object.entries(facts.source_sha256))
    if(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')!==h)
      throw new Error('Heaven Spirit source changed:'+p);
  if(value.players.every(e=>e===null))return null;
  const states=new Map(game.players.map((p,i)=>[p,{input_index:order[i],entry:value.players[order[i]]}]));
  const opened=new WeakSet(),events=[];
  // v27's3001 wrapper is inside this call:1001 precedes3001 and the plants.
  const plants=game.do_plant_start_permanent_buffs.bind(game);
  game.do_plant_start_permanent_buffs=function(...args) {
    const me=this.players[0],state=states.get(me);
    if(state.entry && !opened.has(me)) {
      opened.add(me);
      const before=this.players.map(p=>p.qi);
      if(state.entry.enabled) {
        this.increase_idx_qi(0,facts.qi);
        this.increase_idx_qi(1,facts.qi);
      }
      events.push({strategy_id:1001,player_index:state.input_index,enabled:state.entry.enabled,
        phase:'owner_season_start_before3001_and_plants',
        target_order:[states.get(this.players[0]).input_index,states.get(this.players[1]).input_index],
        qi_before:before,qi_after:this.players.map(p=>p.qi),requested_each:state.entry.enabled?facts.qi:0});
    }
    return plants(...args);
  };
  installed.add(game);
  return {metadata:()=>({evidence_sha256:digest,events:structuredClone(events),
    acquisition_rewards_reapplied:false,training_label_allowed:false})};
}
