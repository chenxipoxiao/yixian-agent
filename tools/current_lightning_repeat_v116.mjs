import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='74ea1d178f6c35aa6fd5c4f68d69c1062f9adacb634644224512568f0843c51b',cache=new Map(),registered=new WeakSet(),installed=new WeakSet();
const check=(v,m)=>{if(!v)throw new Error('lightning_repeat_unresolved:'+m);};
export function lightningRepeatFacts(root){
 if(cache.has(root))return cache.get(root);
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-lightning-repeat-v116.json'));
 check(crypto.createHash('sha256').update(bytes).digest('hex')===digest,'evidence_changed');
 const f=JSON.parse(bytes);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,f);return f;
}
export function registerLightningRepeat(root,swogi){
 check(!registered.has(swogi),'already_registered');
 for(const c of lightningRepeatFacts(root).cards){
  check(!Object.hasOwn(swogi,c.runtime_id),'alias_collision');
  const flags=Object.fromEntries(Object.keys(swogi['601011']).filter(k=>k.startsWith('is_')).map(k=>[k,false]));
  swogi[c.runtime_id]=Object.freeze({...swogi['601011'],...flags,name:c.config.name,names:[c.config.name],marking:'he',
   qi_cost:1,hp_cost:0,is_thunder:true,opening:undefined,card_actions:g=>g.executeCurrentLightningRepeat(c.runtime_id)});
 }
 registered.add(swogi);
}
const snap=p=>({hp:p.hp,max_hp:p.max_hp,qi:p.qi,hexagram:p.hexagram,trigger_depth:p.trigger_depth});
export function installLightningRepeat(root,game,swogi,order=[0,1]){
 check(!installed.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 const f=lightningRepeatFacts(root),cards=new Map(f.cards.map(c=>[c.runtime_id,c]));
 const states=new Map(game.players.map((p,i)=>[p,{index:order[i],pending:0}])),events=[];
 game.executeCurrentLightningRepeat=function(id){
  const p=this.players[0],s=states.get(p),c=cards.get(id);
  check(c&&p.currently_triggering_card_id===id,'card_identity');
  const e={kind:'card_body',raw_card_id:c.raw_id,player_index:s.index,slot:p.currently_triggering_card_idx,
   before:snap(p),pending_before:s.pending};events.push(e);
  this.increase_idx_hexagram(0,c.config.guaXiang);
  check(Number.isSafeInteger(s.pending)&&s.pending>=0&&s.pending<2147483647,'763_overflow');
  s.pending+=1;e.after=snap(p);e.pending_after=s.pending;
 };
 // Installed around the base scheduler before other versioned play wrappers.
 // ExecuteEffect includes before/body/after callbacks; it does not repay costs.
 const play=game.play_card.bind(game);
 game.play_card=function(id,idx){
  const p=this.players[0],s=states.get(p);
  if(!s.pending&&!cards.has(id))return play(id,idx);
  check(p.trigger_depth===0&&Number.isInteger(idx)&&p.cards[idx]===id,'outer_card_identity');
  // Earlier repeat branches can generate763 before this branch. Their dynamic
  // interleaving is not inherited from the frozen precomputed-play-count loop.
  for(const field of ['strike_twice_stacks','unrestrained_sword_twin_dragons_stacks','crash_fist_double_stacks','m_fire_spirit_flame_eater_stacks'])
   check(!(p[field]>0),'other_repeat_interaction:'+field);
  check(Object.hasOwn(f.name_contains_thunder,id),'unknown_card_name:'+id);
  const repeat=s.pending>0&&f.name_contains_thunder[id];
  if(!repeat)return play(id,idx);
  // Client280 follows the complete repeat section; the reference inner helper
  // runs it per effect, so reject that unresolved combination explicitly.
  check(!(p.ultimate_overcome_formation_stacks>0),'280_repeat_interaction');
  p.this_card_chases=0;p.currently_playing_card_idx=idx;p.dream_crash_footwork_fake_crash_fist=0;
  const e={kind:'763_repeat_before_main',player_index:s.index,runtime_id:id,slot:idx,
   pending_before:s.pending,before:snap(p)};events.push(e);
  s.pending-=1;
  this.play_card_inner(id,idx);
  e.after_repeat=snap(p);e.pending_after_repeat=s.pending;
  this.play_card_inner(id,idx);
  e.after_main=snap(p);e.pending_after_main=s.pending;
  p.dream_crash_footwork_fake_crash_fist=0;p.currently_playing_card_idx=undefined;
 };
 installed.add(game);
 return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),
  recorded_action_log:false,training_label_allowed:false}:null};
}
