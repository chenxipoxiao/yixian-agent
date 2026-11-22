import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='a8dd940cd3acc07aa02a842d6822846d35d378651479014e709e41c5ec01c79a',cache=new Map(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('vessel_physique_unresolved:'+why);};
export function vesselPhysiqueFacts(root){
 if(cache.has(root))return cache.get(root);
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-vessel-physique-v74.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');const f=JSON.parse(raw);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,f);return f;
}
export function registerVesselPhysique(root,swogi){
 const f=vesselPhysiqueFacts(root);
 for(const c of f.cards){
  check(!Object.hasOwn(swogi,c.runtime_id),'alias_collision');
  const flags=Object.fromEntries(Object.keys(swogi['601011']).filter(k=>k.startsWith('is_')).map(k=>[k,false]));
  swogi[c.runtime_id]=Object.freeze({...swogi['601011'],...flags,name:c.config.name,names:[c.config.name],marking:'dx',
   qi_cost:0,hp_cost:0,opening:undefined,is_add_qi:c.config.anima>0,is_add_physique:c.config.physique>0,is_consumption:c.config.cardType===1,is_continuous:c.config.cardType===2,
   card_actions:g=>g.executeCurrentVesselPhysique(c.runtime_id)});
 }
 // Register only the versioned bridge's in-memory entry. The pinned engine stays unchanged.
 check(JSON.stringify(swogi['906071'].opening)===JSON.stringify([['add_enemy_c_of_x',1,'spirit_fusion_pot_stacks']]),'unexpected_old_vessel_opening');
 swogi['906071']={...swogi['906071'],opening:[['add_enemy_c_of_x',f.vessel.opening,'spirit_fusion_pot_stacks']]};
}
const snap=p=>Object.fromEntries(['hp','max_hp','qi','physique','max_physique','physique_gained','agility','exercise_bones_stacks','spirit_fusion_pot_stacks'].map(k=>[k,p[k]]));
export function installVesselPhysique(root,game,swogi,order=[0,1]){
 const f=vesselPhysiqueFacts(root),byId=new Map(f.cards.map(c=>[c.runtime_id,c]));
 check(!installed.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(x=>x===0||x===1),'invalid_order');
 const seats=new Map(game.players.map((p,i)=>[p,order[i]])),events=[],boneActive=new WeakSet();
 game.executeCurrentVesselPhysique=function(id){
  const c=byId.get(id),p=this.players[0];check(c!==undefined&&p.currently_triggering_card_id===id,'card_identity');
  const e={kind:'card_body',raw_card_id:c.raw_id,player_index:seats.get(p),slot:p.currently_triggering_card_idx,trigger_depth:p.trigger_depth,before:snap(p)};events.push(e);
  if(c.base_id===339){
   // GetBattleDeckIdList includes every physical slot, even a consumed one.
   check(p.cards.every(id=>typeof swogi[id]?.card_actions==='function'),'unknown_deck_identity');
   e.normal_attack_count=p.cards.filter(id=>f.normal_runtime_ids.includes(id)).length;
   e.attacks=c.config.attackCount+e.normal_attack_count;
   for(let n=0;n<e.attacks;n++){
    this.atk(c.config.attack);this.increase_idx_physique(0,c.config.otherParams[0]);this.increase_idx_x_by_c(0,'agility',c.config.otherParams[1]);
   }
  }else if(c.base_id===10000100){
   this.increase_idx_physique(0,c.config.physique);this.increase_idx_x_by_c(0,'exercise_bones_stacks',c.config.otherParams[0]);
   boneActive.add(p);this.increase_idx_x_by_c(0,'agility',c.config.otherParams[2]);
  }else{
   this.increase_idx_qi(0,c.config.anima);this.increase_idx_hp(0,c.config.otherParams[0]);
   check(Number.isSafeInteger(p.qi)&&p.qi>=0,'invalid_qi');
   e.agility=c.config.otherParams[1]+(c.config.level>=4?p.qi:0);
   this.increase_idx_x_by_c(0,'agility',e.agility);this.consumption();
  }
  e.after=snap(p);
 };
 const bones=game.do_exercise_bones.bind(game);
 game.do_exercise_bones=function(){
  const p=this.players[0];if(!boneActive.has(p))return bones();
  check(Number.isSafeInteger(p.exercise_bones_stacks)&&p.exercise_bones_stacks>=0,'invalid384');
  if(p.exercise_bones_stacks===0)return 0;
  const e={kind:'384_attack',player_index:seats.get(p),before:snap(p),bonus:f.bones_attack_bonus};
  // CalculateAttack consumes384 before ModifyTiPo, so callbacks cannot reuse it.
  this.reduce_c_of_x(1,'exercise_bones_stacks');this.increase_idx_physique(0,1);e.after=snap(p);events.push(e);return f.bones_attack_bonus;
 };
 const opening=game.do_opening.bind(game);
 game.do_opening=function(idx,...args){
  const p=this.players[0],q=this.players[1],id=p.cards[idx],before=q.spirit_fusion_pot_stacks;
  const value=opening(idx,...args);
  if(id==='906071')events.push({kind:'vessel_opening',raw_card_id:181,player_index:seats.get(p),target_index:seats.get(q),slot:idx,before,after:q.spirit_fusion_pot_stacks});
  return value;
 };
 game.do_spirit_fusion_pot=function(idx){
  const p=this.players[0],q=this.players[1];if(!(p.spirit_fusion_pot_stacks>0))return;
  check(Number.isInteger(idx)&&idx>=0&&idx<p.cards.length,'vessel_actual_slot_required');
  const id=p.cards[idx],c=f.vessel_cards[id];check(c&&!c.ambiguous,'vessel_unknown_card:'+id);
  check(!c.raw19,'vessel_raw19_refresh_unresolved');
  if(c.rarity>=1)check(typeof c.downgrade_runtime_id==='string'&&typeof swogi[c.downgrade_runtime_id]?.card_actions==='function','vessel_downgrade_target:'+id);
  const e={kind:'vessel_before_use',raw_card_id:181,player_index:seats.get(q),target_index:seats.get(p),slot:idx,card_before:id,before:[snap(p),snap(q)]};events.push(e);
  this.reduce_idx_x_by_c(0,'spirit_fusion_pot_stacks',1);
  if(c.rarity>=1){p.cards[idx]=c.downgrade_runtime_id;e.downgraded=true;}
  else{
   // Execute0x22da: target HP, target maxHP, caster maxHP, caster HP.
   this.reduce_idx_hp(0,f.vessel.absorb);this.reduce_idx_max_hp(0,f.vessel.absorb);
   this.increase_idx_max_hp(1,f.vessel.absorb);this.increase_idx_hp(1,f.vessel.absorb);e.downgraded=false;
  }
  e.card_after=p.cards[idx];e.after=[snap(p),snap(q)];
 };
 installed.add(game);return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),recorded_action_log:false,training_label_allowed:false}:null};
}
