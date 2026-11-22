// Selected-grid configuration is distinct from mutable per-battle usage state.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const check=(ok,message)=>{if(!ok)throw new Error(message);};
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);

export function installCurrentEngravings(root,game,input,order,transformCards,swogi) {
  if(input===undefined){check(transformCards===undefined,'Transform cards require engraving ownership');return null;}
  check(object(input)&&Object.keys(input).length===1&&Array.isArray(input.players)&&input.players.length===2,'Explicit engraving players required');
  check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(v=>v===0||v===1),'Invalid engraving seat order');
  const raw=fs.readFileSync(path.join(root,'data/inspection/current-engraving-effects-v21.json'));
  check(crypto.createHash('sha256').update(raw).digest('hex')==='a2d0b5176190d202566d94820030b1d87001062284a233ed32600cb2b710b4c6','Engraving evidence changed');
  const facts=JSON.parse(raw);
  for(const [p,h] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'Engraving source changed: '+p);
  // Explicit identity extension; frozen v21 effect timing and checks remain.
  const extensionRaw=fs.readFileSync(path.join(root,'data/inspection/engraving-dream-identities-v51r2.json'));
  check(crypto.createHash('sha256').update(extensionRaw).digest('hex')==='0596971ed6c1e7560a81ab89ba588e4f5f19a15648026c1291ead0b62036f95a','Dream identity evidence changed');
  const extension=JSON.parse(extensionRaw);
  for(const [p,h] of Object.entries(extension.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'Dream identity source changed: '+p);
  for(const [id,c] of Object.entries(extension.transform_cards)) {
    check(!Object.hasOwn(facts.transform_cards,id),'Duplicate transform identity');
    check(c.hidden===true&&c.no_upgrade===true&&c.rarity===0,'Unexpected dream transform eligibility');
    facts.transform_cards[id]=c;
  }
  const soundRaw=fs.readFileSync(path.join(root,'data/inspection/current-sound-control-v52.json'));
  check(crypto.createHash('sha256').update(soundRaw).digest('hex')==='3ac8d98433a3186bf86df7dcc7f9e7337ea7b418639093bfa1c6aec7d8549001','Sound identity evidence changed');
  for(const [id,c] of Object.entries(JSON.parse(soundRaw).extra_transform_cards)) {
    check(!Object.hasOwn(facts.transform_cards,id),'Duplicate sound transform identity');facts.transform_cards[id]=c;
  }
 const extraRaw=fs.readFileSync(path.join(root,'data/inspection/current-twin-dependencies-v54.json'));
 if(crypto.createHash('sha256').update(extraRaw).digest('hex')!=='239aa5c70297af9209d66c881c03bc1815e09203d0e23dbe8985f27f2f9f9038')throw new Error('twin_dependencies_unresolved:identity_evidence_changed');
 for(const [id,c] of Object.entries(JSON.parse(extraRaw).extra_metadata)){if(Object.hasOwn(facts.transform_cards,id))throw new Error('twin_dependencies_unresolved:duplicate_identity');facts.transform_cards[id]=c;}
  const temporaryRaw=fs.readFileSync(path.join(root,'data/inspection/current-temporary-chase-v61.json'));
  check(crypto.createHash('sha256').update(temporaryRaw).digest('hex')==='f865f78998e3dce4c903ede0bf9b63e8d2bb62e33573eea8bfdfeba2e90d1050','Temporary chase identity evidence changed');
  for(const [id,c] of Object.entries(JSON.parse(temporaryRaw).extra_transform_cards)) {
    check(!Object.hasOwn(facts.transform_cards,id),'Duplicate temporary chase identity');facts.transform_cards[id]=c;
  }
  const flagRaw=fs.readFileSync(path.join(root,'data/inspection/current-element-flag-v62r2.json'));
  check(crypto.createHash('sha256').update(flagRaw).digest('hex')==='885436bc30ab371450a076e7948ca88ededc035a8d1f08998a0dd1cf17033e40','Flag identity evidence changed');
  for(const [id,c] of Object.entries(JSON.parse(flagRaw).extra_transform_cards)) {
    check(!Object.hasOwn(facts.transform_cards,id),'Duplicate flag identity');facts.transform_cards[id]=c;
  }
  const fireRaw=fs.readFileSync(path.join(root,'data/inspection/current-dream-fire-v63.json'));
  check(crypto.createHash('sha256').update(fireRaw).digest('hex')==='2be2802df323d4c925226bb94d8aecc4e05928be883fa8042311a8f05deba11f','Dream fire identity evidence changed');
  for(const [id,c] of Object.entries(JSON.parse(fireRaw).extra_transform_cards)) {
    check(!Object.hasOwn(facts.transform_cards,id),'Duplicate dream fire identity');facts.transform_cards[id]=c;
  }
  const passiveRaw=fs.readFileSync(path.join(root,'data/inspection/current-character-passives-v64.json'));
  check(crypto.createHash('sha256').update(passiveRaw).digest('hex')==='ec3a1caec911fe34999fbb27742a52c6cc4261143db9e953bb54d58716e53fa1','Character identity evidence changed');
  for(const [id,c] of Object.entries(JSON.parse(passiveRaw).extra_transform_cards)) {
    check(!Object.hasOwn(facts.transform_cards,id),'Duplicate character identity');facts.transform_cards[id]=c;
  }
  const spaceRaw=fs.readFileSync(path.join(root,'data/inspection/current-space-field-v66.json'));
  check(crypto.createHash('sha256').update(spaceRaw).digest('hex')==='f7e5c5c5747506fb80f94695b46da9846ebebebea125c270ad62e2c0f8d717bb','Space field identity evidence changed');
  for(const [id,c] of Object.entries(JSON.parse(spaceRaw).extra_transform_cards)) {
    check(!Object.hasOwn(facts.transform_cards,id),'Duplicate space field identity');facts.transform_cards[id]=c;
  }
  const thunderRaw=fs.readFileSync(path.join(root,'data/inspection/current-hexagram-thunder-v67.json'));
  check(crypto.createHash('sha256').update(thunderRaw).digest('hex')==='2d27273823be098c052cd474f84b24a1057d0a81ab7d847c3e675995c72aa5e3','Hexagram thunder identity evidence changed');
  for(const [id,c] of Object.entries(JSON.parse(thunderRaw).extra_transform_cards)) {
    check(!Object.hasOwn(facts.transform_cards,id),'Duplicate hexagram thunder identity');facts.transform_cards[id]=c;
  }
  const byId=new Map(facts.effects.map(e=>[e.id,e]));
  const ledger=new WeakMap(),pending=new WeakMap();
  game.players.forEach((player,seat)=>{
    const entries=input.players[order[seat]];
    check(Array.isArray(entries)&&entries.length<=10,'Invalid engraving array');
    const seen=new Set();
    for(const e of entries) {
      check(object(e)&&Object.keys(e).length===2&&byId.has(e.strategy_id)&&Number.isInteger(e.slot)&&e.slot>=0&&e.slot<8,'Invalid engraving strategy or slot');
      check(!seen.has(e.strategy_id),'Duplicate engraving strategy');seen.add(e.strategy_id);
    }
    pending.set(player,{544:0,560:0,745:0,794:0});
    ledger.set(player,entries.map(e=>({...e,used:false})).sort((a,b)=>a.strategy_id-b.strategy_id));
  });
  const transforms=input.players.some(entries=>entries.some(e=>[13003,13007].includes(e.strategy_id)));
  const identities=new WeakMap(),byRuntime=new Map();
  if(transforms) {
    check(object(transformCards)&&Object.keys(transformCards).length===1&&Array.isArray(transformCards.players)&&transformCards.players.length===2,'Explicit raw transform cards required');
    check(object(swogi),'Runtime card catalogue required');
    for(const [raw,c] of Object.entries(facts.transform_cards)) {
      const ids=byRuntime.get(c.runtime_id)??[];ids.push(Number(raw));byRuntime.set(c.runtime_id,ids);
    }
    game.players.forEach((player,seat)=>{
      const raw=transformCards.players[order[seat]];
      check(Array.isArray(raw)&&raw.length===player.cards.length&&raw.every((id,i)=>Number.isInteger(id)&&facts.transform_cards[id]?.runtime_id===player.cards[i]),'Raw transform cards disagree with actual deck');
      identities.set(player,raw.map((id,i)=>({raw:id,runtime:player.cards[i]})));
    });
  } else check(transformCards===undefined,'Transform cards require an admitted transform effect');
  const unresolved=reason=>{throw new Error('engraving_transform_unresolved:'+reason);};
  const resolve=(player,idx)=>{
    check(transforms&&Number.isInteger(idx)&&idx>=0&&idx<player.cards.length,'Invalid transform slot');
    const entry=identities.get(player)[idx],runtime=player.cards[idx];
    if(entry.runtime!==runtime) {
      const raw=byRuntime.get(runtime);
      if(!raw||raw.length!==1)unresolved('ambiguous_or_unknown_runtime:'+runtime);
      entry.raw=raw[0];entry.runtime=runtime;
    }
    return {entry,card:facts.transform_cards[entry.raw]};
  };
  const replace=(player,idx,raw,kind)=>{
    const target=facts.transform_cards[raw];
    if(!target||typeof swogi[target.runtime_id]?.card_actions!=='function')unresolved('unmapped_target:'+raw);
    const old=player.cards[idx];player.cards[idx]=target.runtime_id;
    identities.get(player)[idx]={raw,runtime:target.runtime_id};
    game.log('current engraving '+kind+' transforms slot '+idx+' from '+old+' to '+target.runtime_id);
  };
  const finishing=game.do_finishing_touch.bind(game);
  game.do_finishing_touch=function(idx) {
    const me=this.players[0],e=ledger.get(me).find(e=>e.strategy_id===13003);
    if(e&&e.slot===idx&&!me.can_post_action[idx]) {
      const {card}=resolve(me,idx);
      if(!card.hidden&&!card.no_upgrade) {
        replace(me,idx,card.upgrade_raw_id,13003);e.used=true;
        this.log('current engraving 13003 first use at slot '+idx);
      }
    }
    return finishing(idx);
  };
  const pot=game.do_spirit_fusion_pot.bind(game);
  game.do_spirit_fusion_pot=function(idx) {
    if(transforms&&this.players[0].spirit_fusion_pot_stacks>0&&resolve(this.players[0],idx).entry.raw===19)
      unresolved('unverified_native_pot_raw19');
    const result=pot(idx),me=this.players[0],state=pending.get(me);
    if(state[560]>0) {
      const {entry,card}=resolve(me,idx);
      if(card.rarity>=1&&entry.raw!==19) {
        // Resolve target before committing the candidate, then consume560
        // before replacing; no target inference from native ID digits.
        const target=facts.transform_cards[card.downgrade_raw_id];
        if(!target||typeof swogi[target.runtime_id]?.card_actions!=='function')unresolved('unmapped_target:'+card.downgrade_raw_id);
        state[560]-=1;replace(me,idx,card.downgrade_raw_id,13007);
      }
    }
    return result;
  };
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
        if(e.strategy_id===13003||e.strategy_id===13006||e.used||e.slot!==idx||me.can_post_action[idx])continue;
        e.used=true;const params=byId.get(e.strategy_id).otherParams;
        if(e.strategy_id===13001) {
          pending.get(me)[544]+=params[0];
        } else if(e.strategy_id===13004) {
          check(Number.isSafeInteger(me.hp_lost)&&me.hp_lost>=0&&me.hp_lost*params[0]<=2147483647,'HP-loss amount outside client integer range');
          const amount=Math.trunc(me.hp_lost*params[0]/100);
          if(amount>0){this.increase_idx_max_hp(0,amount);heal(amount);}
        } else if(e.strategy_id===13007) {
          pending.get(this.players[1])[560]+=1;
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
