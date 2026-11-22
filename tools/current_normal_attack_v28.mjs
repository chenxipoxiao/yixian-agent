// Current-season ordinary-attack hooks. The frozen native scheduler is reused.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const check=(ok,message)=>{if(!ok)throw new Error(message);};
export function installCurrentNormalAttack(root,game,value,order) {
  if(value===undefined)return null;
  check(value!==null&&typeof value==='object'&&!Array.isArray(value)
    &&Object.keys(value).length===1&&Array.isArray(value.players)&&value.players.length===2
    &&value.players.every(ids=>Array.isArray(ids)&&new Set(ids).size===ids.length
      &&ids.every(id=>id===5004||id===5011)),'Explicit normal attack ownership required');
  check(Array.isArray(order)&&[[0,1],[1,0]].some(a=>a.length===order.length&&a.every((v,i)=>v===order[i])),
    'Explicit player order required');
  const raw=fs.readFileSync(path.join(root,'data/inspection/current-normal-attack-v28.json'));
  const digest=crypto.createHash('sha256').update(raw).digest('hex');
  check(digest==='a730457d45a9bf19627dcce13ba5063fe1ffc602106a8f1c3354bb9565211b2c','Normal attack evidence changed');
  const facts=JSON.parse(raw);
  for(const [p,h] of Object.entries(facts.source_sha256))
    check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,
      'Normal attack source changed:'+p);
  const states=new Map(game.players.map((p,i)=>[p,{input_index:order[i],ids:new Set(value.players[order[i]]),
    started:false,footwork:false,acupoint:false}]));
  const events=[];
  const plants=game.do_plant_start_permanent_buffs.bind(game);
  game.do_plant_start_permanent_buffs=function(...args) {
    const state=states.get(this.players[0]);
    if(!state.started) {
      state.started=true;state.footwork=state.ids.has(5004);state.acupoint=state.ids.has(5011);
    }
    return plants(...args);
  };
  const previous=game.do_cloud_sword_softheart_and_friends.bind(game);
  game.do_cloud_sword_softheart_and_friends=function(cardId) {
    const me=this.players[0],state=states.get(me);
    if(facts.normal_runtime_ids.includes(cardId)&&(state.footwork||state.acupoint)) {
      const idx=me.currently_triggering_card_idx;
      // Client5011 marks the actual CardItem, including temporary CardItems.
      // Native nested calls only expose a reference slot: never consume that
      // parent slot or silently skip the effect when identity is unresolved.
      if(state.acupoint&&(me.trigger_depth!==1||!Number.isInteger(idx)||idx<0||idx>=me.cards.length
        ||me.currently_playing_card_idx!==idx||me.cards[idx]!==cardId))
        throw new Error('normal_attack_card_identity_unresolved:5011');
      if(state.footwork) {
        this.increase_idx_x_by_c(0,'agility',facts.footwork.agility);
        events.push({player_index:state.input_index,effect_id:5004,phase:'before_card_body',
          card:cardId,slot:idx,amount:facts.footwork.agility,trigger_depth:me.trigger_depth});
      }
      if(state.acupoint) {
        this.increase_idx_debuff(1,'weaken',facts.acupoint.weaken);
        this.increase_idx_debuff(1,'decrease_atk',facts.acupoint.decrease_atk);
        state.acupoint=false;
        // Preserve the current execution, post-card hooks and chase. Only
        // later traversal skips the consumed CardItem.
        me.can_play[idx]=false;
        events.push({player_index:state.input_index,effect_id:5011,phase:'before_card_body',
          card:cardId,slot:idx,weaken:facts.acupoint.weaken,decrease_atk:facts.acupoint.decrease_atk,
          consumed:true});
      }
    }
    return previous(cardId);
  };
  return {metadata:()=>({evidence_sha256:digest,events,training_label_allowed:false,
    remaining:[...states.values()].map(s=>({player_index:s.input_index,footwork_active:s.footwork,
      acupoint_pending:s.acupoint})).sort((a,b)=>a.player_index-b.player_index)})};
}
