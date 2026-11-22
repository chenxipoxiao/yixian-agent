// Selected-grid configuration is distinct from mutable per-battle usage state.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const check=(ok,message)=>{if(!ok)throw new Error(message);};
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);

export function installCurrentEngravings(root,game,input,order) {
  if(input===undefined)return null;
  check(object(input)&&Object.keys(input).length===1&&Array.isArray(input.players)&&input.players.length===2,'Explicit engraving players required');
  check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(v=>v===0||v===1),'Invalid engraving seat order');
  const raw=fs.readFileSync(path.join(root,'data/inspection/current-engraving-effects-v18.json'));
  check(crypto.createHash('sha256').update(raw).digest('hex')==='7d3da58b97c2bfc57b2205d65d6fc0ba984df4cc8dc12e17132f2605182f45e0','Engraving evidence changed');
  const facts=JSON.parse(raw);
  for(const [p,h] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'Engraving source changed: '+p);
  const byId=new Map(facts.effects.map(e=>[e.id,e]));
  const ledger=new WeakMap();
  game.players.forEach((player,seat)=>{
    const entries=input.players[order[seat]];
    check(Array.isArray(entries)&&entries.length<=2,'Invalid engraving array');
    const seen=new Set();
    for(const e of entries) {
      check(object(e)&&Object.keys(e).length===2&&byId.has(e.strategy_id)&&Number.isInteger(e.slot)&&e.slot>=0&&e.slot<8,'Invalid engraving strategy or slot');
      check(!seen.has(e.strategy_id),'Duplicate engraving strategy');seen.add(e.strategy_id);
    }
    ledger.set(player,entries.map(e=>({...e,used:false})).sort((a,b)=>a.strategy_id-b.strategy_id));
  });
  // Client OnBeforeExecuted: adjacent effects -> fate-strategy OnPlayCard ->
  // seasonal OnPlayCard -> cloud-sword passives and subsequent card effects.
  // Legacy fate-strategy lists are still rejected by the compiler. Ordinary
  // talent/card passives retain their pinned scheduler positions.
  const cloud=game.do_cloud_sword_softheart_and_friends.bind(game);
  game.do_cloud_sword_softheart_and_friends=function(cardId) {
    const me=this.players[0],idx=me.currently_triggering_card_idx;
    // Nested trigger_card calls are temporary card executions in this bridge.
    if(me.trigger_depth===1) {
      check(Number.isInteger(idx)&&idx>=0&&idx<me.cards.length,'Engraving requires actual card slot');
      for(const e of ledger.get(me)) {
        if(e.used||e.slot!==idx||me.can_post_action[idx])continue;
        e.used=true;const params=byId.get(e.strategy_id).otherParams;
        if(e.strategy_id===13009) {
          this.increase_idx_def(0,params[0]);
          this.add_c_of_x(params[1],'moon_water_sword_formation_stacks');
        } else if(e.strategy_id===13016) {
          this.add_c_of_x(params[0],'sword_intent');
          const damage=Math.trunc(me.sword_intent/params[1]);
          if(damage>0)this.deal_damage(damage);
        }
        this.log('current engraving '+e.strategy_id+' first use at slot '+idx);
      }
    }
    return cloud(cardId);
  };
  return {forPlayer:p=>ledger.get(p).map(e=>({...e}))};
}
