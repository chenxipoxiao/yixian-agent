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
  const raw=fs.readFileSync(path.join(root,'data/inspection/current-engraving-effects-v20.json'));
  check(crypto.createHash('sha256').update(raw).digest('hex')==='fd5446a34e7d0c93c030d6e32a30efc2b065ea58061a8b6b617d4acd6d713edf','Engraving evidence changed');
  const facts=JSON.parse(raw);
  for(const [p,h] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'Engraving source changed: '+p);
  const byId=new Map(facts.effects.map(e=>[e.id,e]));
  const ledger=new WeakMap(),pending=new WeakMap();
  game.players.forEach((player,seat)=>{
    const entries=input.players[order[seat]];
    check(Array.isArray(entries)&&entries.length<=8,'Invalid engraving array');
    const seen=new Set();
    for(const e of entries) {
      check(object(e)&&Object.keys(e).length===2&&byId.has(e.strategy_id)&&Number.isInteger(e.slot)&&e.slot>=0&&e.slot<8,'Invalid engraving strategy or slot');
      check(!seen.has(e.strategy_id),'Duplicate engraving strategy');seen.add(e.strategy_id);
    }
    pending.set(player,{544:0,745:0,794:0});
    ledger.set(player,entries.map(e=>({...e,used:false})).sort((a,b)=>a.strategy_id-b.strategy_id));
  });
  // Temporary card identity cannot be reconstructed from a reference slot.
  // The client permits its 13006 branch, so fail before executing an unknown
  // nested card instead of treating all temporary cards as ineligible.
  const trigger=game.trigger_card.bind(game);
  game.trigger_card=function(cardId,idx) {
    const me=this.players[0];
    if(me.trigger_depth>=1&&ledger.get(me).some(e=>e.strategy_id===13006&&!e.used))
      throw new Error('engraving_temporary_card_identity_unresolved:13006');
    return trigger(cardId,idx);
  };
  const shocked=game.do_crash_fist_shocked.bind(game);
  game.do_crash_fist_shocked=function(cardId) {
    const me=this.players[0],state=pending.get(me);
    const effect=ledger.get(me).find(e=>e.strategy_id===13006);
    if(effect&&!effect.used&&state[794]===0) {
      check(me.trigger_depth===1,'engraving_temporary_card_identity_unresolved:13006');
      const idx=me.currently_triggering_card_idx;
      check(Number.isInteger(idx)&&idx>=0&&idx<me.cards.length,'Engraving requires actual card slot');
      if(idx===effect.slot&&!me.can_post_action[idx]) {
        effect.used=true;state[794]=1;
        this.log('current engraving 13006 first use at slot '+idx);
        this.atk(byId.get(13006).otherParams[0],true);
      }
    }
    return shocked(cardId);
  };
  // Damage/body effects keep their original order. 544 is an after-attack
  // effect even when guard or defense prevented all HP loss. Non-attacks do
  // not consume it; the state belongs to the player rather than active seat.
  const damage=game.deal_damage_inner.bind(game);
  game.deal_damage_inner=function(dmg,isAttack,seat,...args) {
    const owner=this.players[seat],opponent=this.players[1-seat];
    const result=damage(dmg,isAttack,seat,...args);
    const state=pending.get(owner);
    if(isAttack&&state[544]>0) {
      const amount=state[544];state[544]=0;
      this.increase_idx_debuff(this.players.indexOf(opponent),'internal_injury',amount);
    }
    return result;
  };
  const loseHp=game.reduce_idx_hp.bind(game);
  game.reduce_idx_hp=function(seat,...args) {
    const owner=this.players[seat],before=owner.guard_up;
    const result=loseHp(seat,...args);
    if(before-owner.guard_up===1)pending.get(owner)[745]=Math.max(0,pending.get(owner)[745]-1);
    return result;
  };
  const decay=game.do_def_decay.bind(game);
  game.do_def_decay=function() {
    const state=pending.get(this.players[0]);
    if(state[745]>0) {
      const amount=state[745];state[745]=0;
      this.reduce_idx_x_by_c(0,'guard_up',amount);
    }
    return decay();
  };
  const heal=amount=>{if(game.players[0].hp>0)game.increase_idx_hp(0,amount);};
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
        if(e.strategy_id===13006||e.used||e.slot!==idx||me.can_post_action[idx])continue;
        e.used=true;const params=byId.get(e.strategy_id).otherParams;
        if(e.strategy_id===13001) {
          pending.get(me)[544]+=params[0];
        } else if(e.strategy_id===13004) {
          check(Number.isSafeInteger(me.hp_lost)&&me.hp_lost>=0&&me.hp_lost*params[0]<=2147483647,'HP-loss amount outside client integer range');
          const amount=Math.trunc(me.hp_lost*params[0]/100);
          if(amount>0){this.increase_idx_max_hp(0,amount);heal(amount);}
        } else if(e.strategy_id===13008) {
          this.add_c_of_x(params[0],'guard_up');pending.get(me)[745]+=params[0];
        } else if(e.strategy_id===13013) {
          this.add_c_of_x(params[0],'hexagram');
          const amount=me.hexagram*params[1];
          this.increase_idx_max_hp(0,amount);heal(amount);
        } else if(e.strategy_id===13019) {
          const count=Object.values(facts.debuff_fields).reduce((n,key)=>n+Math.max(0,me[key]),0);
          heal(count+params[0]);
        } else if(e.strategy_id===13009) {
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
  return {forPlayer:p=>ledger.get(p).map(e=>({...e})),pendingFor:p=>({...pending.get(p)})};
}
