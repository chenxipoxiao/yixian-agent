import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export function installCurrentWindCards(root,swogi,game,realms) {
  const raw=fs.readFileSync(path.join(root,'data/inspection/current-wind-cards-v8.json'));
  const digest=crypto.createHash('sha256').update(raw).digest('hex');
  if(digest!=='ad4cdfdadce2a3d4d7e540bee184f0d76b10c9096eea4c472468b058d9bf01c4')throw new Error('Current wind evidence changed');
  const facts=JSON.parse(raw);
  for(const [p,h] of [['data/local/2026-11-06/tables/CardConfig.json',facts.card_table_sha256],['external/yisim/gamestate_full.js',facts.native_engine_sha256]]) {
    if(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')!==h)throw new Error('Wind source changed');
  }
  const levels=new WeakMap(game.players.map((p,i)=>[p,realms?.[i]])),overrides=new Map();
  for(const family of facts.families) family.cards.forEach((c,grade)=>{
    overrides.set(swogi[family.native_ids[grade]],()=>{
      const me=game.players[0];
      if(family.kind==='feather') {
        game.atk_replay_count_or_default(c.attack,c.attackCount);
        game.increase_idx_qi(0,c.anima);game.increase_idx_physique(0,c.physique);game.add_c_of_x(c.otherParams[0],'agility');
      } else if(family.kind==='cyclone') {
        const qi=Math.trunc(me.physique/c.otherParams[0]);if(qi>0)game.increase_idx_qi(0,qi);
        const attack=c.attack+me.qi;game.atk_replay_count_or_default(attack,c.attackCount);
      } else {
        const realm=levels.get(me);
        if(!Number.isInteger(realm)||realm<1||realm>6)throw new Error('Wind flash requires explicit start realm');
        game.increase_idx_physique(0,c.physique);game.add_c_of_x(c.otherParams[0],'agility');
        const amount=Math.trunc(me.agility/2)*(realm>=5?2:1);
        if(amount>0)game.deal_damage(amount);
      }
    });
  });
  const original=game.just_do_the_card_and_nothing_else.bind(game);
  game.just_do_the_card_and_nothing_else=card=>overrides.has(card)?overrides.get(card)():original(card);
  return {evidence_sha256:digest,official_turn_limit:facts.turn_limit.value,
    realm_input:realms??null,native_scheduler_reused:true,training_label_allowed:false};
}
