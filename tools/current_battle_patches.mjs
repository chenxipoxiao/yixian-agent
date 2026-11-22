// Narrow current-client corrections; never edit the frozen upstream simulator.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export function installCurrentCards(root, swogi, game) {
  const raw=fs.readFileSync(path.join(root,'data/inspection/full-battle-patches-v1.json'));
  if(crypto.createHash('sha256').update(raw).digest('hex')!=='806a9802660b57739d0d8b8f227e8b16e43480223c791a80576e0f425c7fcfd9') throw new Error('Current patch evidence changed');
  const facts=JSON.parse(raw);
  const cardRaw=fs.readFileSync(path.join(root,'data/local/2026-11-06/tables/CardConfig.json'));
  if(crypto.createHash('sha256').update(cardRaw).digest('hex')!==facts.card_table_sha256) throw new Error('Current card configuration changed');
  const patch=facts.spirit_cat_chaos_sword;
  const overrides=new Map();
  patch.reference_ids.forEach((id,index)=>{
    const card=patch.cards[index];
    overrides.set(swogi[id],()=>{
      game.for_each_x_up_to_c_add_y('hand_count',card.otherParams[0],'bonus_rep_amt');
      game.atk_replay_count_or_default(card.attack,card.attackCount+game.players[0].bonus_rep_amt);
    });
  });
  const original=game.just_do_the_card_and_nothing_else.bind(game);
  game.just_do_the_card_and_nothing_else=card=>{
    const override=overrides.get(card);
    return override ? override() : original(card);
  };
  return {evidence_sha256:crypto.createHash('sha256').update(raw).digest('hex'),
          patched_cards:patch.raw_ids,current_server_verified:false};
}
