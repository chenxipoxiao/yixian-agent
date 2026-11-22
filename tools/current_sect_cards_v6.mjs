// Version-specific card bodies on the pinned yisim combat primitives/scheduler.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export function registerCurrentSectCards(root, swogi) {
  const bytes=fs.readFileSync(path.join(root,'data/inspection/current-sect-cards-v6.json'));
  const digest=crypto.createHash('sha256').update(bytes).digest('hex');
  if(digest!=='c27fc6564b3517b1bbaa3eb24f8fbffdb519b5c34d4ccf468b8a14b0aa95b740') throw new Error('Current sect card evidence changed');
  const facts=JSON.parse(bytes);
  for(const [filename,expected] of [
    ['data/local/2026-11-06/tables/CardConfig.json',facts.card_table_sha256],
    ['external/yisim/gamestate_full.js',facts.native_engine_sha256]]) {
    if(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,filename))).digest('hex')!==expected) throw new Error('Current sect card source changed');
  }
  const metadata=[];
  for(const family of facts.families) for(let grade=0;grade<family.cards.length;grade++) {
    const c=family.cards[grade],id=family.runtime_ids[grade],kind=family.kind;
    if(Object.hasOwn(swogi,id)) throw new Error('Runtime card alias collision');
    swogi[id]=Object.freeze({...swogi['601011'],name:family.engine_name,names:[family.engine_name,c.name],
      qi_cost:Math.max(0,-c.anima),hp_cost:c.hpCost,marking:c.sect===1?'sw':'dx',
      is_sword:['red_sky','elephant','moonlight'].includes(kind),
      is_cloud_sword:kind==='moonlight',is_unrestrained_sword:kind==='red_sky',
      is_spirit_sword:kind==='elephant',is_add_qi:c.anima>0,is_add_physique:kind==='mountain_palm',opening:undefined,
      card_actions:game=>{
        const me=game.players[0],p=c.otherParams;
        const attack=(n=c.attack,reps=c.attackCount)=>game.atk_replay_count_or_default(n,Math.max(1,reps));
        switch(kind) {
          case 'red_sky':
            game.add_c_of_x(Math.min(me.unrestrained_sword_count,p[0]),'increase_atk');attack();break;
          case 'elephant':attack();game.add_c_of_x(p[0],'increase_atk');break;
          case 'moonlight': {
            const amount=p[0]+Math.min((me.increase_atk+me.sword_intent)*p[1],p[2]);
            game.increase_idx_max_hp(0,amount);game.increase_idx_hp(0,amount);
            if(game.if_cloud_hit()) attack();break;
          }
          case 'sword_flash':
            game.add_c_of_x(c.jianYi,'sword_intent');
            game.increase_idx_def(0,Math.min((me.qi+me.sword_intent)*p[0],p[1]));game.chase();break;
          case 'high_spirits':
            game.add_c_of_x(p[0],'max_force');game.increase_idx_force(0,p[0]);
            attack(c.attack+Math.min(me.qi+me.force,p[1]));break;
          case 'mountain_palm': {
            const slot=me.currently_triggering_card_idx;
            if(!Number.isInteger(slot)||slot<0||slot>=me.cards.length) throw new Error('Mountain palm needs triggered card slot');
            if((slot+1)%2===1) game.increase_idx_physique(0,c.physique);
            else game.increase_idx_force(0,p[0]);
            attack(c.attack+(p[1]>0?Math.trunc(me.physique/p[1]):0));break;
          }
          case 'flank': {
            attack();game.add_c_of_x(p[0],'increase_atk');
            const qi=Math.min(me.qi,p[1]);game.reduce_idx_x_by_c(0,'qi',qi);
            const force=Math.min(me.force,p[1]-qi);game.reduce_idx_force(0,force);
            game.add_c_of_x((qi+force)*p[2],'agility');break;
          }
          case 'hundred_heals': {
            const amount=Math.trunc((p[0]+me.increase_atk)*(10+me.force)/10);
            game.increase_idx_hp(0,amount);
            attack(c.attack+Math.trunc(me.hp_gained/p[1]));break;
          }
          case 'blood_shadow':
            game.increase_idx_qi(0,c.anima);game.increase_idx_hp(0,p[2]);
            game.increase_idx_debuff(0,'internal_injury',p[0]);
            game.add_c_of_x(Math.min(me.qi+game.get_debuff_count(0),p[1]),'agility');break;
          case 'asura': {
            // Both base amounts are captured before either hit changes state.
            const first=c.attack+me.qi,second=c.attack+game.get_debuff_count(0);
            game.atk(first);game.atk(second);
            game.increase_idx_hp(0,Math.trunc(me.damage_dealt_to_hp_by_this_card_atk/p[0]));break;
          }
          default:throw new Error('Unknown current sect family');
        }
      }});
    metadata.push({raw_id:c.id,runtime_id:id,kind});
  }
  return {evidence_sha256:digest,cards:metadata,native_scheduler_reused:true,
    globally_changes_original_reference_entries:false,training_label_allowed:false};
}
