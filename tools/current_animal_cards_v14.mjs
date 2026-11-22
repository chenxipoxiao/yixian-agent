// Current animal-card combat effects; future-round resource effects stay pending.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export function registerCurrentAnimalCards(root,swogi) {
  const bytes=fs.readFileSync(path.join(root,'data/inspection/current-animal-cards-v14.json'));
  const digest=crypto.createHash('sha256').update(bytes).digest('hex');
  if(digest!=='7ca841c61895fb0bfaedf52b6272ac5232df00bfa58a75a8b698b9c5de6d0bb2')throw new Error('Animal card evidence changed');
  const facts=JSON.parse(bytes);
  for(const [p,h] of Object.entries(facts.source_sha256)) {
    if(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')!==h)throw new Error('Animal source changed:'+p);
  }
  // Current IsYunJian/IsKuangJian/IsLingJian all classify base213 unconditionally.
  // This is a property of the card, not an acquisition reward or chosen fate.
  for(const id of ['615031','615032','615033'])swogi[id]=Object.freeze({...swogi[id],
    is_cloud_sword:true,is_unrestrained_sword:true,is_spirit_sword:true,is_sword_formation:true});
  for(const f of facts.families)f.cards.forEach((c,g)=>{
    const id=f.runtime_ids[g];
    if(Object.hasOwn(swogi,id))throw new Error('Animal alias collision');
    swogi[id]=Object.freeze({...swogi['601011'],name:f.engine_name,names:[f.engine_name,c.name],
      qi_cost:Math.max(0,-c.anima),hp_cost:c.hpCost,is_consumption:true,is_add_qi:c.anima>0,
      opening:undefined,card_actions:game=>{
        const p=c.otherParams;
        if(f.kind==='badger')game.deal_damage(p[0]);
        else if(f.kind==='turtle') {
          game.increase_idx_def(0,c.def);game.increase_idx_max_hp(0,p[0]);
        } else if(f.kind==='rat') {
          game.increase_idx_qi(0,c.anima);game.increase_idx_def(0,c.def);
        } else if(f.kind==='parrot')game.increase_idx_hp(0,p[0]);
        else throw new Error('Unknown animal card');
        game.current_record_animal_effect(f.kind,c.id,p);
        game.consumption();
      }});
  });
  return {evidence_sha256:digest};
}

export function installCurrentAnimalLedger(game) {
  const pending=new WeakMap(game.players.map(p=>[p,[]]));
  game.current_record_animal_effect=(kind,raw_card,params)=>{
    const event={raw_card,kind,params:[...params],executed_in_current_battle:true,
      future_match_state_mutated:false};
    pending.get(game.players[0]).push(event);
  };
  return {forPlayer:player=>structuredClone(pending.get(player))};
}
