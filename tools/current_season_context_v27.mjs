// Per-battle current-season 3001 and 23080, with explicit source ownership.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
export function installCurrentSeasonContext(root,game,swogi,value,order) {
  if(value===undefined)return null;
  const valid=value!==null && typeof value==='object' && !Array.isArray(value)
    && Object.keys(value).length===1 && Array.isArray(value.players) && value.players.length===2
    && value.players.every(ids=>Array.isArray(ids) && new Set(ids).size===ids.length
      && ids.every(id=>id===3001||id===23080));
  if(!valid)throw new Error('Explicit season context ownership required');
  if(!Array.isArray(order)||![[0,1],[1,0]].some(v=>v.length===order.length&&v.every((x,i)=>x===order[i])))
    throw new Error('Explicit player order required');
  const raw=fs.readFileSync(path.join(root,'data/inspection/current-season-context-v27.json'));
  const digest=crypto.createHash('sha256').update(raw).digest('hex');
  if(digest!=='44d5f4877bd6ebe38923f1268c78aa72d24e5d43f0679fa653791e5714b5fe22')throw new Error('Season context evidence changed');
  const facts=JSON.parse(raw);
  for(const [p,h] of Object.entries(facts.source_sha256))
    if(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')!==h)
      throw new Error('Season context source changed:'+p);
  const states=new Map(game.players.map((p,i)=>[p,{ids:new Set(value.players[order[i]]),input_index:order[i]}]));
  const events=[];
  const plants=game.do_plant_start_permanent_buffs.bind(game);
  const opened=new WeakSet();
  game.do_plant_start_permanent_buffs=function(...args) {
    const me=this.players[0],state=states.get(me);
    if(state.ids.has(3001)&&!opened.has(me)) {
      opened.add(me);
      this.increase_idx_debuff(1,'decrease_atk',facts.dragon_awe.amount);
      events.push({player_index:state.input_index,effect_id:3001,phase:'before_permanent_plants',amount:1});
    }
    return plants(...args);
  };
  const names=['wood','fire','earth','metal','water'];
  const originals=Object.fromEntries(names.map(n=>[n,game['do_'+n+'_spirit_formation'].bind(game)]));
  const forceage=game.do_wood_spirit_forceage_formation.bind(game);
  const has=()=>states.get(game.players[0]).ids.has(23080);
  // The current client order is earth, water, fire, wood, forceage, metal.
  // Run this group at the first native formation hook, and suppress only the
  // later calls for the owner. All nonowners retain the frozen native methods.
  game.do_wood_spirit_formation=function(cardId) {
    if(!has())return originals.wood(cardId);
    const card=swogi[cardId],p=this.players[0],state=states.get(p);
    if(!card)throw new Error('Unknown formation card');
    const eligible=n=>Boolean(card['is_'+n+'_spirit']||card['is_'+facts.generating_formation.successors[n]+'_spirit']);
    for(const n of facts.generating_formation.order) {
      if(n==='wood_forceage'){forceage(cardId);continue;}
      const amount=p[n+'_spirit_formation_stacks'];
      if(!eligible(n)||amount===0)continue;
      if(n==='earth')this.increase_idx_def(0,amount);
      else if(n==='water')this.increase_idx_qi(0,amount);
      else if(n==='fire'){
        this.reduce_idx_hp(1,amount);this.reduce_idx_max_hp(1,amount);
      } else if(n==='wood')this.increase_idx_hp(0,amount);
      else this.increase_idx_x_by_c(0,'penetrate',amount);
      events.push({player_index:state.input_index,effect_id:23080,phase:'before_card_body',
        formation:n,card:cardId,amount,generating_only:!card['is_'+n+'_spirit']});
    }
  };
  for(const n of ['fire','earth','metal','water'])
    game['do_'+n+'_spirit_formation']=function(cardId){if(!has())return originals[n](cardId);};
  game.do_wood_spirit_forceage_formation=function(cardId){if(!has())return forceage(cardId);};
  return {metadata:()=>({evidence_sha256:digest,events,training_label_allowed:false})};
}
