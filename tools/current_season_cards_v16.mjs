// Opt-in current card bodies. The original reference entries stay untouched.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export function registerCurrentSeasonCards(root,swogi) {
  const bytes=fs.readFileSync(path.join(root,'data/inspection/current-season-cards-v16.json'));
  const digest=crypto.createHash('sha256').update(bytes).digest('hex');
  if(digest!=='5e8e11cf52ec707fbd2028826e14189b777b5a32245209e08b4d9c0c87055500')throw new Error('Season card evidence changed');
  const facts=JSON.parse(bytes);
  for(const [p,h] of Object.entries(facts.source_sha256)) {
    if(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')!==h)throw new Error('Season card source changed:'+p);
  }
  const slot=game=>{
    const me=game.players[0],idx=me.currently_triggering_card_idx;
    if(!Number.isInteger(idx)||idx<0||idx>=me.cards.length)throw new Error('Season card requires triggering slot');
    return idx;
  };
  const activate=(game,id)=>{
    for(const element of ['metal','wood','water','fire','earth']) {
      if(swogi[id]['is_'+element+'_spirit'])game['activate_'+element+'_spirit']();
    }
  };
  const generates=(game,a,b)=>{
    const x=swogi[a],y=swogi[b];
    if([['metal','water'],['wood','fire'],['earth','metal'],['water','wood'],['fire','earth']]
      .some(([one,two])=>x['is_'+one+'_spirit']&&y['is_'+two+'_spirit']))return true;
    const any=c=>['metal','wood','water','fire','earth'].some(e=>c['is_'+e+'_spirit']);
    return game.players[0].fire_spirit_generation_stacks>0 && any(x)&&any(y)&&Boolean(x.is_fire_spirit)!==Boolean(y.is_fire_spirit);
  };
  for(const f of facts.families)f.cards.forEach((c,grade)=>{
    const id=f.runtime_ids[grade],kind=f.kind;
    if(Object.hasOwn(swogi,id))throw new Error('Season card alias collision');
    swogi[id]=Object.freeze({...swogi['601011'],name:f.engine_name,names:[f.engine_name,c.name],
      qi_cost:Math.max(0,-c.anima),hp_cost:c.hpCost,marking:c.sect===2?'he':'fe',
      is_add_qi:c.anima>0,is_astral_move:kind==='astral_tip',is_snake:kind==='seek_snake',
      is_seal:kind==='twin_seal',is_fire_spirit:['fire_extinction','extreme_fire'].includes(kind),
      is_water_spirit:kind==='water_rain',is_metal_spirit:kind==='metal_sand',opening:undefined,
      card_actions:game=>{
        const me=game.players[0],p=c.otherParams;
        const attack=(n=c.attack)=>game.atk_replay_count_or_default(n,Math.max(1,c.attackCount));
        switch(kind) {
          case 'seek_snake':
            game.add_enemy_c_of_x(p[0],'internal_injury');
            game.add_enemy_c_of_x(p[1],'snake_shadow');game.chase();break;
          case 'astral_tip': {
            attack();
            if(slot(game)%2===0)game.increase_idx_star_power(0,p[0]);
            else {
              const amount=Math.min(me.star_power,p[1]);
              if(amount>0){game.reduce_idx_x_by_c(0,'star_power',amount);game.add_c_of_x(amount,'guard_up');}
            }
            break;
          }
          case 'soul_hexagram':
            game.add_c_of_x(c.guaXiang+(game.get_debuff_count(1)>0?p[0]:0),'hexagram');
            if(slot(game)%2===0)game.add_enemy_c_of_x(p[1],'internal_injury');
            else game.add_enemy_c_of_x(p[2],'wound');break;
          case 'twin_seal': {
            attack();const next=game.get_next_idx(slot(game)),after=game.get_next_idx(next);
            const a=me.cards[next],b=me.cards[after];activate(game,a);activate(game,b);
            if(generates(game,a,b))game.increase_idx_def(0,p[1]);break;
          }
          case 'fire_extinction': {
            let amount=p[0];
            if(game.if_fire_spirit())amount+=me.increase_atk*p[1];
            if(game.if_earth_spirit()&&p[2]>0)amount+=Math.trunc(me.def/p[2]);
            if(game.if_metal_spirit()&&p[3]>0)amount+=Math.trunc(me.penetrate/p[3]);
            if(amount>0){game.reduce_idx_hp(1,amount);game.reduce_idx_max_hp(1,amount);}break;
          }
          case 'water_rain':
            game.add_c_of_x(p[0],'force_of_water');
            game.increase_idx_max_hp(0,p[1]);game.increase_idx_hp(0,p[1]);
            if(game.if_water_spirit())attack(c.attack+me.force_of_water);
            if(game.if_wood_spirit())attack(c.attack+me.qi);break;
          case 'metal_sand':
            game.increase_idx_qi(0,c.anima);game.add_c_of_x(p[0],'penetrate');
            if(game.if_metal_spirit()||game.if_water_spirit())game.chase();break;
          case 'extreme_fire':
            game.increase_idx_qi(0,c.anima);game.add_c_of_x(p[0],'increase_atk');
            if(game.if_fire_spirit()){
              const amount=p[1]+me.increase_atk;game.reduce_idx_hp(1,amount);game.reduce_idx_max_hp(1,amount);
            }break;
          default:throw new Error('Unknown current season family');
        }
      }});
  });
  return {evidence_sha256:digest,training_label_allowed:false};
}
