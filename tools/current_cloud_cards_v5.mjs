// Current card-specific actions. All battle primitives and scheduling remain native.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export function registerCurrentCloudCards(root, swogi) {
  const bytes=fs.readFileSync(path.join(root,'data/inspection/current-cloud-cards-v5.json'));
  const digest=crypto.createHash('sha256').update(bytes).digest('hex');
  if(digest!=='f9fa41a2eeae81c58a01865f3b9b08e8c26d9349a51f4d978e4f733159f4f906') throw new Error('Current cloud card evidence changed');
  const facts=JSON.parse(bytes);
  for(const [filename,expected] of [
    ['data/local/2026-11-06/tables/CardConfig.json',facts.card_table_sha256],
    ['external/yisim/gamestate_full.js',facts.native_engine_sha256]]) {
    if(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,filename))).digest('hex')!==expected) throw new Error('Current cloud card source changed');
  }
  const metadata=[];
  for(const family of facts.families) {
    family.cards.forEach((card,grade)=>{
      const id=family.runtime_ids[grade];
      if(Object.hasOwn(swogi,id)) throw new Error('Runtime card alias collision');
      const cloud=family.kind==='cloud_spirit_sea';
      const body=family.kind==='overlord_cauldron';
      if(!cloud && !body && family.kind!=='floating_cloud') throw new Error('Unknown current card family');
      swogi[id]=Object.freeze({...swogi['601011'],name:family.engine_name,names:[family.engine_name,card.name],
        qi_cost:Math.max(0,-card.anima),hp_cost:card.hpCost,marking:body?'dx':'sw',
        is_sword:cloud,is_cloud_sword:cloud,is_add_physique:body,is_add_qi:true,
        opening:undefined,
        card_actions:game=>{
          const me=game.players[0];
          if(cloud) {
            game.atk_replay_count_or_default(card.attack,card.attackCount);
            game.increase_idx_qi(0,card.anima);
            game.add_c_of_x(card.otherParams[0],'cloud_sea');
            if(game.if_cloud_hit()) {
              const extra=card.otherParams[1]-1;
              game.add_c_of_x(extra,'cloud_sword_chain_count');
              // Client ModifyBuffValue(304,c) also increases cumulative 720.
              game.add_c_of_x(extra,'cloud_sword_used_count');
            }
          } else if(body) {
            game.increase_idx_qi(0,card.anima);
            game.increase_idx_physique(0,card.physique);
            game.add_c_of_x(card.otherParams[0],'increase_atk');
          } else {
            const slot=me.currently_triggering_card_idx;
            if(!Number.isInteger(slot) || slot<0 || slot>=me.cards.length) throw new Error('Floating cloud requires actual triggered card slot');
            game.increase_idx_qi(0,card.anima);
            game.add_c_of_x(card.otherParams[0],'cloud_sea');
            if((slot+1)%2===1) {
              const nominal=card.otherParams[1]+me.qi*card.otherParams[3];
              const healRequest=Math.min(nominal,me.max_hp-me.hp);
              if(healRequest<0) throw new Error('Floating cloud negative heal request unresolved');
              // Split BEFORE native heal modifiers; prevented healing is not defense.
              game.increase_idx_hp(0,healRequest);
              if(nominal>healRequest) game.increase_idx_def(0,nominal-healRequest);
            } else game.add_c_of_x(card.otherParams[2],'agility');
          }
        }});
      metadata.push({raw_id:card.id,runtime_id:id,kind:family.kind});
    });
  }
  return {evidence_sha256:digest,cards:metadata,native_scheduler_reused:true,
          globally_changes_original_reference_entries:false,training_label_allowed:false};
}
