// Source-derived current Only Traces values over the frozen native executor.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export function installCurrentOnlyTraces(root, swogi, game) {
  const raw=fs.readFileSync(path.join(root,'data/inspection/current-only-traces-v23.json'));
  if(crypto.createHash('sha256').update(raw).digest('hex')!=='518e5063fb28bd4b9de1b56dd77ded53b48822b01506ef450b9be370685c402f')throw new Error('Only Traces evidence changed');
  const facts=JSON.parse(raw);
  for(const [name,expected] of Object.entries(facts.source_sha256)) {
    if(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,name))).digest('hex')!==expected)throw new Error('Only Traces source changed:'+name);
  }
  const overrides=new Map();
  facts.reference_ids.forEach((id,index)=>{
    const c=facts.cards[index];
    if(!swogi[id])throw new Error('Missing Only Traces reference card:'+id);
    overrides.set(swogi[id],()=>{
      game.increase_idx_qi(0,c.anima);
      if(c.rarity===0) {
        if(game.if_post_action())game.chase();
      } else {
        game.reduce_idx_hp(0,c.otherParams[1]);
        // Native chase() only requests a later chase, not immediate execution.
        if(c.actionAgain)game.chase();
        if(game.if_post_action())game.increase_idx_hp(0,c.otherParams[0]);
      }
    });
  });
  const original=game.just_do_the_card_and_nothing_else.bind(game);
  game.just_do_the_card_and_nothing_else=card=>{
    const override=overrides.get(card);
    return override ? override() : original(card);
  };
}
