// Current Yan Chen card bodies, installed on one game only.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
export function installCurrentYanChen(root,swogi,game) {
  const raw=fs.readFileSync(path.join(root,'data/inspection/current-yan-chen-cards-v26.json'));
  if(crypto.createHash('sha256').update(raw).digest('hex')!=='dfcafc34d258db4c99d087f1d206f57e57a0211a09eb47e1fa2f52edde066202')throw new Error('Yan Chen evidence changed');
  const facts=JSON.parse(raw);
  for(const [name,expected] of Object.entries(facts.source_sha256)) {
    if(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,name))).digest('hex')!==expected)throw new Error('Yan Chen source changed:'+name);
  }
  const overrides=new Map();
  facts.ultimate_hexagram.reference_ids.forEach((id,index)=>{
    const c=facts.ultimate_hexagram.cards[index];
    if(!swogi[id])throw new Error('Missing Ultimate Hexagram reference:'+id);
    overrides.set(swogi[id],()=>{
      game.add_c_of_x(c.otherParams[0],'hexagram');
      game.continuous();
      game.add_c_of_x(1,'ultimate_hexagram_base_stacks');
    });
  });
  facts.fury_thunder.reference_ids.forEach((id,index)=>{
    const c=facts.fury_thunder.cards[index];
    if(!swogi[id])throw new Error('Missing Fury Thunder reference:'+id);
    overrides.set(swogi[id],()=>{
      game.increase_idx_qi(0,c.anima);
      game.do_fury_thunder(c.otherParams[0]);
    });
  });
  const original=game.just_do_the_card_and_nothing_else.bind(game);
  game.just_do_the_card_and_nothing_else=card=>{
    const override=overrides.get(card);
    return override?override():original(card);
  };
}
