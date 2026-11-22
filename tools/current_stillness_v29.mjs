// Three current card bodies reuse the pinned shared qi/healing primitives.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const ids=['125961','125962','125963'];
export function registerCurrentStillness(root,swogi) {
  const bytes=fs.readFileSync(path.join(root,'data/inspection/current-stillness-v29.json'));
  const digest=crypto.createHash('sha256').update(bytes).digest('hex');
  if(digest!=='70192a63bede0b24110b48f6c3b3d271b17c044ac3cf6a4f89180fdf09e7fd1f')throw new Error('Stillness evidence changed');
  const facts=JSON.parse(bytes);
  for(const [p,h] of Object.entries(facts.source_sha256))
    if(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')!==h)
      throw new Error('Stillness source changed:'+p);
  const family=facts.families[0];
  family.cards.forEach((c,index)=>{
    const id=family.runtime_ids[index];
    if(Object.hasOwn(swogi,id))throw new Error('Stillness alias collision');
    swogi[id]=Object.freeze({...swogi['122091'],name:family.engine_name,names:[family.engine_name,c.name],
      qi_cost:0,hp_cost:0,marking:'he',is_continuous:true,is_consumption:false,is_add_qi:false,
      opening:undefined,card_actions:game=>{
        game.continuous();
        game.increase_idx_max_hp(0,c.otherParams[1]);
        game.add_c_of_x(c.otherParams[0],'stillness_citta_dharma_stacks');
        game.chase();
      }});
  });
  return {evidence_sha256:digest,native_qi_healing_reused:true,training_label_allowed:false};
}

// Read-only observations. Combined HP changes are not attributed wholly to203.
export function installStillnessObserver(game,swogi,order) {
  const owners=new Map(game.players.map((p,i)=>[p,order[i]]));
  const used=new Set(),events=[];
  const cards=new Map(ids.map((id,i)=>[swogi[id],{runtime_id:id,raw_id:4000098+i*10000}]));
  const previous=game.just_do_the_card_and_nothing_else.bind(game);
  game.just_do_the_card_and_nothing_else=function(card) {
    const me=this.players[0],info=cards.get(card);
    const before=info?{hp:me.hp,max_hp:me.max_hp,stacks:me.stillness_citta_dharma_stacks}:null;
    const result=previous(card);
    if(info) {
      used.add(me);
      events.push({kind:'card_body',player_index:owners.get(me),...info,
        trigger_depth:me.trigger_depth,slot:me.currently_triggering_card_idx,before,
        after:{hp:me.hp,max_hp:me.max_hp,stacks:me.stillness_citta_dharma_stacks}});
    }
    return result;
  };
  const qi=game.increase_idx_qi.bind(game);
  game.increase_idx_qi=function(idx,amount) {
    const me=this.players[idx],active=used.has(me);
    const before=active?{hp:me.hp,qi:me.qi,total_qi_gained:me.total_qi_gained,combined_stillness:me.stillness_citta_dharma_stacks}:null;
    const result=qi(idx,amount);
    if(active&&me.total_qi_gained>before.total_qi_gained)
      events.push({kind:'qi_gain_after_card',player_index:owners.get(me),requested:amount,before,
        after:{hp:me.hp,qi:me.qi,total_qi_gained:me.total_qi_gained,combined_stillness:me.stillness_citta_dharma_stacks}});
    return result;
  };
  return {metadata:()=>events.length?{events,combined_hp_delta_not_exclusive_effect_attribution:true,
    training_label_allowed:false}:null};
}
