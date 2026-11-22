// Delayed effects belong to the player object, including when active seats swap.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {installCurrentDelayedDamage} from './current_delayed_damage_v70.mjs';

function factsAt(root) {
  const raw=fs.readFileSync(path.join(root,'data/inspection/current-delayed-effects-v17.json'));
  const sha=crypto.createHash('sha256').update(raw).digest('hex');
  if(sha!=='2cb785a17ffe524303bc5360f3e738f15b3f9ff6f3aa1ea6a83d44e3aa049829')throw new Error('Delayed effect evidence changed');
  const facts=JSON.parse(raw);
  for(const [p,h] of Object.entries(facts.source_sha256)) {
    if(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')!==h)throw new Error('Delayed effect source changed: '+p);
  }
  return facts;
}

export function registerCurrentDelayedCards(root,swogi) {
  const facts=factsAt(root);
  for(const f of facts.families)f.cards.forEach((c,grade)=>{
    const id=f.runtime_ids[grade];
    if(Object.hasOwn(swogi,id))throw new Error('Delayed effect alias collision');
    swogi[id]=Object.freeze({...swogi['601011'],name:f.engine_name,names:[f.engine_name,c.name],
      qi_cost:Math.max(0,-c.anima),hp_cost:c.hpCost,marking:c.sect===2?'he':'fe',
      is_add_qi:c.anima>0,is_astral_move:f.kind==='astral_chain',
      is_wood_spirit:f.kind==='wood_branch',is_earth_spirit:f.kind==='earth_step',opening:undefined,
      card_actions:game=>{
        if(typeof game.current_gain_delayed!=='function')throw new Error('Delayed effect scheduler not installed');
        if(f.kind==='wood_branch') {
          game.increase_idx_qi(0,c.anima);
          if(game.if_wood_spirit())game.current_gain_delayed(777,c.otherParams[0]);
        } else if(f.kind==='earth_step') {
          game.increase_idx_def(0,c.def);
          game.current_gain_delayed(779,1);
          if(game.if_earth_spirit())game.add_c_of_x(c.otherParams[0],'agility');
        } else if(f.kind==='astral_chain') {
          game.atk_replay_count_or_default(c.attack,Math.max(1,c.attackCount));
          game.increase_idx_qi(0,c.anima);game.current_gain_delayed(778,c.otherParams[0]);
        } else throw new Error('Unknown delayed card family');
      }});
  });
}

export function installCurrentDelayedEffects(root,game,swogi) {
  const facts=factsAt(root),map=new WeakMap(game.players.map(p=>[p,{777:0,778:0,779:0}]));
  const stealBase=facts.families.find(f=>f.kind==='wood_branch').cards[0].otherParams[1];
  const healBase=facts.families.find(f=>f.kind==='astral_chain').cards[0].otherParams[1];
  game.current_gain_delayed=function(buff,amount) {
    if(![777,778,779].includes(buff)||!Number.isSafeInteger(amount)||amount<=0)throw new Error('Invalid delayed effect addition');
    map.get(this.players[0])[buff]+=amount;
  };
  // All six elemental formation hooks have run at this boundary. The new
  // effects run in client order 778 -> 777, before the card's own action.
  const water=game.do_water_spirit_formation.bind(game);
  game.do_water_spirit_formation=function(cardId) {
    const value=water(cardId),me=this.players[0],state=map.get(me);
    if(state[778]>0&&swogi[cardId].is_astral_move) {
      const idx=me.currently_triggering_card_idx;
      if(!Number.isInteger(idx)||idx<0||idx>=me.cards.length)throw new Error('Delayed astral effect requires triggering slot');
      if(me.is_star_point[idx])this.increase_idx_star_power(0,1);
      else {this.become_idx_star_point(0,idx);this.increase_idx_hp(0,healBase);}
      state[778]--;this.log('current delayed 778 before astral card at slot '+idx);
    }
    if(state[777]>0) {
      const amount=stealBase+me.increase_atk;
      this.reduce_idx_hp(1,amount);this.increase_idx_hp(0,amount);
      state[777]--;this.log('current delayed 777 steal request '+amount);
    }
    return value;
  };
  game.current_delayed_after_attack=function(playerIdx,hpLoss) {
    const state=map.get(this.players[playerIdx]);
    if(state[779]>0) {
      state[779]--;
      const amount=Math.trunc(hpLoss/3);
      if(amount>0)this.increase_idx_def(playerIdx,amount);
      this.log('current delayed 779 from HP loss '+hpLoss+' grants defense '+Math.max(0,amount));
    }
  };
  installCurrentDelayedDamage(game);
  // Read-only diagnostics for boundary tests; never accepted as replay input.
  return {forPlayer:player=>({...map.get(player)})};
}
