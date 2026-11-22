// Two current card families installed only inside the versioned v2 process.
// Aliases have normal phase/grade digits but are not official reference IDs.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export function registerCurrentSwordCards(root, swogi) {
  const proof=fs.readFileSync(path.join(root,'data/inspection/current-sword-cards-v2.json'));
  if(crypto.createHash('sha256').update(proof).digest('hex')!=='caf6ee89c9a4515ee36d60b3d9078b5ddc72a2132925ef301f8cc233119e35b9') throw new Error('Current sword evidence changed');
  const facts=JSON.parse(proof);
  const config=fs.readFileSync(path.join(root,'data/local/2026-11-06/tables/CardConfig.json'));
  if(crypto.createHash('sha256').update(config).digest('hex')!==facts.card_table_sha256) throw new Error('Current sword card configuration changed');
  const metadata=[];
  for(const family of facts.families) {
    family.cards.forEach((card,grade)=>{
      const id=family.runtime_ids[grade];
      if(Object.hasOwn(swogi,id)) throw new Error('Runtime card alias collision');
      const flying=family.kind==='flying_swallow';
      if(!flying && family.kind!=='thousand_blades') throw new Error('Unknown current sword family');
      const entry={...swogi['601011'],name:family.engine_name,names:[family.engine_name,card.name],
        qi_cost:Math.max(0,-card.anima),hp_cost:card.hpCost,marking:'sw',
        is_sword:true,is_spirit_sword:flying,is_sword_formation:!flying,
        opening:flying ? ['current_swallow_opening',card.otherParams[0]] : undefined,
        card_actions:game=>{
          // Snapshot defense once before all hits, as in client IL, rather
          // than recalculating after reactive effects of each individual hit.
          const attack=card.attack+(flying ? 0 : Math.trunc(game.players[0].def/card.otherParams[0]));
          game.atk_replay_count_or_default(attack,card.attackCount);
        }};
      swogi[id]=Object.freeze(entry);
      metadata.push({raw_id:card.id,runtime_id:id,kind:family.kind});
    });
  }
  return {evidence_sha256:crypto.createHash('sha256').update(proof).digest('hex'),cards:metadata,
          globally_changes_original_reference_entries:false,training_label_allowed:false};
}

export function installCurrentSwordMethods(game) {
  game.current_swallow_opening=amount=>{
    // Exactly zero, not a grant at snapshot import and not once per combat.
    // A legitimate opening retrigger re-evaluates this same qi condition.
    if(game.players[0].qi===0) game.increase_idx_qi(0,amount);
  };
}
