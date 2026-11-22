// Versioned5008 insertion between the frozen5004 and5011 OnPlayCard branches.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const check=(ok,msg)=>{if(!ok)throw new Error('carefree_twin_unresolved:'+msg);};
export function installCurrentNormalAttackV53(root,game,value,order){
 check(value!==null&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).length===1
  &&Array.isArray(value.players)&&value.players.length===2
  &&value.players.every(a=>Array.isArray(a)&&new Set(a).size===a.length&&a.every(id=>[5004,5008,5011].includes(id))), 'explicit_normal_attack_ownership_required');
 check(value.players.some(a=>a.includes(5008)),'power_owner_required');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-carefree-twin-v53.json'));
 const digest=crypto.createHash('sha256').update(raw).digest('hex');check(digest==='fd56118358b7fc8aa53048da9c1edd8eaf22985359a0474c16c93f9e41b74196','evidence_changed');
 const facts=JSON.parse(raw);
 for(const [p,h] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 const priorRaw=fs.readFileSync(path.join(root,'data/inspection/current-normal-attack-v28.json'));
 check(crypto.createHash('sha256').update(priorRaw).digest('hex')==='a730457d45a9bf19627dcce13ba5063fe1ffc602106a8f1c3354bb9565211b2c','prior_normal_evidence_changed');
 const old=JSON.parse(priorRaw),states=new Map(),events=[];
 game.players.forEach((p,i)=>states.set(p,{index:order[i],ids:new Set(value.players[order[i]]),started:false,footwork:false,acupoint:false,power:0}));
 const plants=game.do_plant_start_permanent_buffs.bind(game);
 game.do_plant_start_permanent_buffs=function(...args){
  const s=states.get(this.players[0]);
  if(!s.started){s.started=true;s.footwork=s.ids.has(5004);s.power=s.ids.has(5008)?3:0;s.acupoint=s.ids.has(5011);}
  return plants(...args);
 };
 const previous=game.do_cloud_sword_softheart_and_friends.bind(game);
 game.do_cloud_sword_softheart_and_friends=function(id){
  const p=this.players[0],s=states.get(p),idx=p.currently_triggering_card_idx;
  if(facts.normal_runtime_ids.includes(id)&&(s.footwork||s.power>0||s.acupoint)){
   if(s.power>0||s.acupoint)check(p.trigger_depth===1&&Number.isInteger(idx)&&idx>=0&&idx<p.cards.length
    &&p.currently_playing_card_idx===idx&&p.cards[idx]===id,'normal_attack_actual_card_identity_required');
   if(s.footwork){
    this.increase_idx_x_by_c(0,'agility',old.footwork.agility);
    events.push({player_index:s.index,effect_id:5004,phase:'before_card_body',card:id,slot:idx,amount:old.footwork.agility});
   }
   if(s.power>0){
    const amount=s.power;
    this.increase_idx_x_by_c(0,'increase_atk',amount);
    s.power=0;p.can_play[idx]=false;
    events.push({player_index:s.index,effect_id:5008,phase:'before_card_body',card:id,slot:idx,amount,consumed:true});
   }
   if(s.acupoint){
    this.increase_idx_debuff(1,'weaken',old.acupoint.weaken);
    this.increase_idx_debuff(1,'decrease_atk',old.acupoint.decrease_atk);
    s.acupoint=false;p.can_play[idx]=false;
    events.push({player_index:s.index,effect_id:5011,phase:'before_card_body',card:id,slot:idx,
     weaken:old.acupoint.weaken,decrease_atk:old.acupoint.decrease_atk,consumed:true});
   }
  }
  return previous(id);
 };
 return {metadata:()=>({evidence_sha256:digest,events:structuredClone(events),training_label_allowed:false,
  remaining:[...states.values()].map(s=>({player_index:s.index,footwork_active:s.footwork,power_pending:s.power,acupoint_pending:s.acupoint})).sort((a,b)=>a.player_index-b.player_index)})};
}
