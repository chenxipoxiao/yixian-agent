import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='d1c238e4122dc3ca97f43438bc08a5a48642c259482db2cc836ef5d363bb5bcc',installed=new WeakSet();
const check=(v,m)=>{if(!v)throw new Error('season_water_unresolved:'+m);};
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const nonnegative=(n,m)=>check(Number.isSafeInteger(n)&&n>=0&&n<=2147483647,m);
const scaled=n=>{nonnegative(n,'damage_outside_int32');const r=Math.floor(Math.fround(Math.fround(n)*Math.fround(1.5)));nonnegative(r,'scaled_damage_outside_int32');return r;};
export function installSeasonWater(root,game,swogi,value,order=[0,1],initial=undefined){
 if(value===undefined)return null;
 check(object(value)&&Object.keys(value).length===1&&Array.isArray(value.players)&&value.players.length===2,'explicit_players_required');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 check(value.players.every(a=>Array.isArray(a)&&new Set(a).size===a.length&&a.every(id=>[3012,7032].includes(id)))&&value.players.some(a=>a.length),'explicit_supported_ownership_required');
 check(!installed.has(game),'already_installed');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-season-water-v76.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');const f=JSON.parse(raw);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 const states=new Map(game.players.map((p,i)=>[p,{index:order[i],ids:new Set(value.players[order[i]]),active:false,card:null}])),events=[];
 const has=(p,id)=>states.get(p).ids.has(id);
 for(const [p,s] of states){
  check(Number.isInteger(p.round_number)&&p.round_number>=1,'explicit_round_required');
  if(s.ids.has(7032))for(const field of ['force_of_water','m_water_spirit_billows_stacks']){
   nonnegative(p[field],'invalid_'+field);
   check(!initial?.[s.index]||!Object.hasOwn(initial[s.index],field)||initial[s.index][field]>0,'initial_presence_unresolved:'+field);
  }
 }
 const emit=(p,kind,extra)=>events.push({player_index:states.get(p).index,kind,...extra});
 const start=game.do_dream_cloud_sword_softheart_gain_def.bind(game);
 game.do_dream_cloud_sword_softheart_gain_def=function(...args){
  const result=start(...args),p=this.players[0];
  if(has(p,3012)){
   const c=f.configs['3012'],amount=c.otherParams[p.round_number>=c.effectRound?1:0],before=p.def;
   this.increase_idx_def(0,amount);emit(p,'3012_after650_before651',{round:p.round_number,requested:amount,before,after:p.def});
  }
  return result;
 };
 game.current_water_selected_card=function(card,slot){
  const p=this.players[0];if(!has(p,7032))return;
  check(Number.isInteger(slot)&&slot>=0&&slot<p.cards.length&&swogi[card],'selected_card_identity');
  states.get(p).card={card,slot};
 };
 game.current_water_blade_active=p=>states.get(p)?.active===true;
 game.current_water_blade_damage=function(p,damage,fengrui){
  check(states.get(p).active,'temporary576_missing');const result=scaled(damage),display=scaled(fengrui);
  emit(p,'576_post_shield_wound_scale',{damage_before:damage,damage_after:result,fengrui_before:fengrui,fengrui_after:display});return result;
 };
 const normal=game.do_force_of_water.bind(game);
 game.do_force_of_water=function(...args){
  const p=this.players[0],s=states.get(p);if(!has(p,7032))return normal(...args);
  nonnegative(p.force_of_water,'water_presence_not_reconstructable');nonnegative(p.m_water_spirit_billows_stacks,'billows_presence_not_reconstructable');
  // The adapter admits only normal generated counters, whose nonpositive
  // transitions remove their dictionary entry. Explicit ambiguous starts reject.
  if(p.force_of_water===0)return;
  check(s.card!==null,'turn_end_selected_card_required');
  const count=1+(p.m_water_spirit_billows_stacks>0?1:0);
  for(let i=0;i<count;i++){
   const previous={id:p.currently_triggering_card_id,slot:p.currently_triggering_card_idx,playing:p.currently_playing_card_idx};
   check(!s.active,'nested_water_attack_unresolved');s.active=true;
   p.currently_triggering_card_id=s.card.card;p.currently_triggering_card_idx=s.card.slot;p.currently_playing_card_idx=s.card.slot;
   const e={iteration:i+1,iterations:count,base_attack:p.force_of_water,card:s.card.card,slot:s.card.slot,before:{hp:p.hp,target_hp:this.players[1].hp,target_def:this.players[1].def}};
   emit(p,'7032_add382_then576',e);
   try{this.atk(p.force_of_water,true);}
   finally{
    s.active=false;p.currently_triggering_card_id=previous.id;p.currently_triggering_card_idx=previous.slot;p.currently_playing_card_idx=previous.playing;
    emit(p,'7032_remove576_then382',{iteration:i+1,after:{hp:p.hp,target_hp:this.players[1].hp,target_def:this.players[1].def}});
   }
  }
 };
 game.current_water_blade_cleanup=function(){
  const p=this.players[0];if(!has(p,7032))return;
  nonnegative(p.m_water_spirit_billows_stacks,'billows_cleanup_value');
  if(p.m_water_spirit_billows_stacks>0){const before=p.m_water_spirit_billows_stacks;this.reduce_idx_x_by_c(0,'m_water_spirit_billows_stacks',1);emit(p,'484_late_turn_cleanup',{before,after:p.m_water_spirit_billows_stacks});}
 };
 installed.add(game);
 return {metadata:()=>({evidence_sha256:digest,events:structuredClone(events),training_label_allowed:false})};
}
