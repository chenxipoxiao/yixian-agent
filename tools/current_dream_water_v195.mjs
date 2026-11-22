export const waterCards = [{"alias": "D195W", "config": {"id": 7040103, "name": "梦•水灵汹涌", "desc": "{attack}攻（每有1[灵气]或[水势]此牌多1攻）\\n每[击伤]{otherParams[0]}生命就加1生命及上限", "sect": 3, "level": 5, "attack": 10, "overrideSpriteIds": [7000037], "otherParams": [3], "estimateTime": 1.5, "hidden": true, "noUpgrade": true, "subcategory": 14, "career": 0, "anima": 0, "randomAttack": 0, "attackCount": 0, "def": 0, "randomDef": 0, "damage": 0, "randomDamage": 0, "jianYi": 0, "guaXiang": 0, "actionAgain": false, "cardType": 0, "rarity": 0, "hpCost": 0, "physique": 0, "linkageId": 0, "chargeQi": 0, "owner": 0, "seasonMechanics": [], "obsolete": false, "description_preview": "10攻（每有1[灵气]或[水势]此牌多1攻）\n每[击伤]3生命就加1生命及上限"}}];

export function registerWater(swogi) {
  const [{alias,config}] = waterCards;
  if (Object.hasOwn(swogi,alias)) throw Error('water alias collision');
  const template = swogi['601011'];
  const flags = Object.fromEntries(Object.keys(template).filter(k=>k.startsWith('is_')).map(k=>[k,false]));
  swogi[alias] = Object.freeze({...template,...flags,name:config.name,names:[config.name],marking:'fe',
    qi_cost:0,hp_cost:0,opening:undefined,is_water_spirit:true,card_actions(game) {
      const p=game.players[0];
      const attack=config.attack+p.qi+p.force_of_water;
      if (!Number.isSafeInteger(attack)||attack<0||attack>2147483647) throw Error('water attack range');
      game.atk(attack);
      const hit=p.damage_dealt_to_hp_by_this_card_atk;
      if (!Number.isSafeInteger(hit)||hit<0) throw Error('water hit counter');
      const heal=Math.floor(hit/config.otherParams[0]);
      if (heal>0) {
        game.increase_idx_max_hp(0,heal);
        game.increase_idx_hp(0,heal);
      }
    }});
}
