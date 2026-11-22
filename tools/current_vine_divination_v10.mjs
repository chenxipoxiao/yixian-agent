// Versioned current numeric values, without altering the pinned engine.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
export function installCurrentVineDivination(root,swogi,game) {
  const raw=fs.readFileSync(path.join(root,'data/inspection/current-vine-divination-v10.json'));
  const digest=crypto.createHash('sha256').update(raw).digest('hex');
  if(digest!=='8de48b1c753039857aaa4f95374baa0183a53a15979cc0a948ec30cbafdcbce6')throw new Error('Vine/divination evidence changed');
  const facts=JSON.parse(raw),overrides=new Map();
  for(const [p,h] of Object.entries(facts.source_sha256)) {
    if(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')!==h)throw new Error('Vine/divination source changed');
  }
  for(const family of facts.families)family.cards.forEach((c,g)=>{
    overrides.set(swogi[family.native_ids[g]],()=>{
      if(family.kind==='vine') {
        if(c.otherParams[0]>0)game.increase_idx_debuff(1,'entangle',c.otherParams[0]);
        if(c.cardType===3)game.continuous();
        if(c.otherParams[1]>0)game.players[1].entangling_ancient_vine_stacks+=c.otherParams[1];
      } else if(family.kind==='cycle') {
        game.increase_idx_max_hp(0,c.otherParams[0]);game.increase_idx_hp(0,c.otherParams[0]);
        game.continuous();game.add_c_of_x(c.otherParams[1],'fate_reincarnates_stacks');
      } else {
        game.increase_idx_qi(0,c.anima);
        game.add_c_of_x(c.otherParams[1],family.kind==='conform'?'god_opportunity_conform_stacks':'god_opportunity_reversal_stacks');
      }
    });
  });
  const original=game.just_do_the_card_and_nothing_else.bind(game);
  game.just_do_the_card_and_nothing_else=card=>overrides.has(card)?overrides.get(card)():original(card);
  return {evidence_sha256:digest,native_scheduler_reused:true,training_label_allowed:false};
}
