// Extreme Footwork shares the combat primitives; only this new family's
// repetition eligibility is evaluated sequentially at the client boundaries.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='c98883b3198540d967c62b640897345feb6b29843935aac5bfb8c12376f8b977';
const checked=new Map(),installed=new WeakSet();
const fail=why=>{throw new Error('extreme_footwork_unresolved:'+why);};
function factsAt(root){
 if(checked.has(root))return checked.get(root);
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-extreme-footwork-v44.json'));
 if(crypto.createHash('sha256').update(bytes).digest('hex')!==digest)fail('evidence_changed');
 const f=JSON.parse(bytes);
 for(const [p,h] of Object.entries(f.source_sha256))
  if(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')!==h)fail('source_changed:'+p);
 checked.set(root,f);return f;
}
export function registerExtremeFootwork(root,swogi){
 for(const c of factsAt(root).cards){
  if(Object.hasOwn(swogi,c.runtime_id))fail('alias_collision');
  swogi[c.runtime_id]=Object.freeze({...swogi['143011'],name:'Current Extreme Footwork',names:['Current Extreme Footwork',c.config.name],
   qi_cost:0,hp_cost:0,is_add_qi:c.config.anima>0,is_continuous:true,is_consumption:false,opening:undefined,
   card_actions:g=>{
    if(typeof g.current_extreme_footwork!=='function')fail('runtime_not_installed');
    g.current_extreme_footwork(c.runtime_id);
   }});
 }
}
const state=p=>({qi:p.qi,agility:p.agility,footwork:p.crash_footwork_stacks,double:p.crash_fist_double_stacks,
 strike_twice:p.strike_twice_stacks,poke:p.crash_fist_poke_stacks,block:p.crash_fist_block_stacks,def:p.def});
export function installExtremeFootwork(root,game,swogi,order=[0,1]){
 if(installed.has(game))fail('already_installed');
 if(!Array.isArray(order)||order.length!==2||new Set(order).size!==2||!order.every(i=>i===0||i===1))fail('invalid_order');
 const cards=new Map(factsAt(root).cards.map(c=>[c.runtime_id,c])),seats=new Map(game.players.map((p,i)=>[p,order[i]])),events=[];
 game.current_extreme_footwork=function(id){
  const p=this.players[0],c=cards.get(id);
  if(!c||p.currently_triggering_card_id!==id)fail('action_identity');
  if(p.trigger_depth!==1||p.cards[p.currently_playing_card_idx]!==id)fail('temporary_card_identity');
  const e={kind:'card_body',player_index:seats.get(p),raw_id:c.raw_id,runtime_id:id,
   slot:p.currently_playing_card_idx,before:state(p)};events.push(e);
  this.continuous();
  if(c.config.anima>0)this.increase_idx_qi(0,c.config.anima);
  this.add_c_of_x(c.config.otherParams[0],'agility');
  this.add_c_of_x(1,'crash_footwork_stacks');
  e.after=state(p);
 };
 const play=game.play_card.bind(game);
 game.play_card=function(id,slot){
  if(!cards.has(id))return play(id,slot);
  const p=this.players[0];
  if(!Number.isInteger(slot)||p.cards[slot]!==id||p.trigger_depth!==0)fail('play_identity');
  p.this_card_chases=0;p.currently_playing_card_idx=slot;p.dream_crash_footwork_fake_crash_fist=0;
  //205 extra execution is before355 eligibility; neither is the main execution.
  if(p.strike_twice_stacks>0){
   this.reduce_idx_x_by_c(0,'strike_twice_stacks',1);this.play_card_inner(id,slot);
  }
  const eligible=p.crash_fist_double_stacks>0&&this.is_crash_fist(id);
  events.push({kind:'double_check',player_index:seats.get(p),raw_id:cards.get(id).raw_id,slot,eligible,state:state(p)});
  if(eligible){this.reduce_idx_x_by_c(0,'crash_fist_double_stacks',1);this.play_card_inner(id,slot);}
  this.play_card_inner(id,slot);
  p.dream_crash_footwork_fake_crash_fist=0;p.currently_playing_card_idx=undefined;
 };
 installed.add(game);
 return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),recorded_action_log:false,
  temporary_identity_supported:false,training_label_allowed:false}:null};
}
