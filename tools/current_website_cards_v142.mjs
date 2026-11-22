import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='6dcacc45713bc9a24290f0972eb0490833b16094bb297275f7a48c91adf08294',cache=new Map(),registered=new WeakSet(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('website_cards_v142:'+why);};
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
export function websiteCardFacts(root){
 if(cache.has(root))return cache.get(root);
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-website-cards-v142.json'));
 check(hash(bytes)===digest,'evidence_changed');const f=JSON.parse(bytes);
 for(const [p,h] of Object.entries(f.source_sha256))check(hash(fs.readFileSync(path.join(root,p)))===h,'source_changed:'+p);
 cache.set(root,f);return f;
}
export function registerWebsiteCards(root,swogi){
 check(!registered.has(swogi),'duplicate_registration');
 for(const c of websiteCardFacts(root).cards){
  check(!Object.hasOwn(swogi,c.runtime_id),'alias_collision');
  const flags=Object.fromEntries(Object.keys(swogi['601011']).filter(k=>k.startsWith('is_')).map(k=>[k,false]));
  swogi[c.runtime_id]=Object.freeze({...swogi['601011'],...flags,name:c.config.name,names:[c.config.name],
   marking:c.kind==='night_howl'?'dx':'sw',qi_cost:Math.max(0,-c.config.anima),hp_cost:0,opening:undefined,
   is_add_qi:c.config.anima>0,is_sword:c.kind==='cloud_silence',is_unrestrained_sword:c.kind==='cloud_silence',
   is_continuous:c.kind==='cloud_silence',card_actions:g=>g.executeWebsiteCard142(c.runtime_id)});
 }
 registered.add(swogi);
}
const snap=p=>Object.fromEntries(['hp','max_hp','qi','def','cloud_sea','agility','weaken','unrestrained_sword_count'].map(k=>[k,p[k]]));
export function installWebsiteCards(root,game,swogi,input,order=[0,1]){
 check(!installed.has(game),'duplicate_install');check(order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'player_order');
 const f=websiteCardFacts(root),cards=new Map(f.cards.map(c=>[c.runtime_id,c]));
 const states=new Map(game.players.map((p,i)=>[p,{index:order[i],silence:0,pending:0}])),events=[];
 const bounded=n=>{check(Number.isSafeInteger(n)&&n>=0&&n<=2147483647,'counter_overflow');return n;};
 game.executeWebsiteCard142=function(id){
  const p=this.players[0],s=states.get(p),c=cards.get(id),idx=p.currently_triggering_card_idx;
  check(c&&p.currently_triggering_card_id===id&&swogi[id],'card_identity');
  const e={kind:'card_body',raw_card_id:c.raw_id,player_index:s.index,slot:idx,trigger_depth:p.trigger_depth,before:snap(p),opponent_before:snap(this.players[1]),silence_before:s.silence,pending_before:s.pending};events.push(e);
  if(c.kind==='cloud_silence'){
   this.increase_idx_max_hp(0,c.config.otherParams[0]);this.increase_idx_hp(0,c.config.otherParams[0]);s.silence=bounded(s.silence+1);this.continuous();
  }else if(c.kind==='cloud_steps'){
   // Temporary cards need their actual grid; the triggering slot is not proof.
   check(p.trigger_depth===1&&Number.isInteger(idx)&&p.cards[idx]===id,'temporary_402_grid_unresolved');
   this.increase_idx_qi(0,c.config.anima);this.add_c_of_x(c.config.otherParams[0],'cloud_sea');
   if(idx%2===0)s.pending=bounded(s.pending+1);else this.add_c_of_x(c.config.otherParams[1],'agility');
  }else{
   this.add_c_of_x(1,'ignore_def');this.atk(c.config.attack);
   this.increase_idx_debuff(0,'weaken',c.config.otherParams[0]);this.increase_idx_debuff(1,'weaken',c.config.otherParams[0]);
  }
  e.after=snap(p);e.opponent_after=snap(this.players[1]);e.silence_after=s.silence;e.pending_after=s.pending;
 };
 // The fake-classification hook is also queried by357 Dragon Devours Clouds.
 const fake=game.is_fake_unrestrained_sword.bind(game);
 game.is_fake_unrestrained_sword=function(id){
  if(fake(id))return true;
  const s=states.get(this.players[0]);if(!s.silence)return false;
  const values=f.runtime_rarities[id];check(values?.length===1,'755_unknown_or_ambiguous_rarity:'+id);
  return values[0]>=1;
 };
 game.currentCloudRepeat756=function(id,idx){
  const p=this.players[0],s=states.get(p);
  if(!s.pending||!this.is_cloud_sword(id))return false;
  check(!(p.ultimate_overcome_formation_stacks>0),'756_280_interaction');
  const e={kind:'756_before_main',player_index:s.index,runtime_id:id,slot:idx,pending_before:s.pending,before:snap(p)};events.push(e);
  s.pending--;this.play_card_inner(id,idx);e.after=snap(p);e.pending_after=s.pending;return true;
 };
 const play=game.play_card.bind(game);
 game.play_card=function(id,idx){
  const p=this.players[0],s=states.get(p);
  if(!s.pending&&!p.cards.some(c=>cards.get(c)?.kind==='cloud_steps'))return play(id,idx);
  check(p.trigger_depth===0&&Number.isInteger(idx)&&p.cards[idx]===id,'756_outer_identity');
  check(!(p.ultimate_overcome_formation_stacks>0),'756_280_interaction');
  check(!p.cards.some(c=>swogi[c]?.name==='Current Extreme Footwork'),'756_extreme_footwork_interaction');
  // Sequential client branches:406,205,756,355,483,main.763 is handled by the
  // outer versioned lightning wrapper, which calls the same756 boundary.
  p.this_card_chases=0;p.currently_playing_card_idx=idx;p.dream_crash_footwork_fake_crash_fist=0;
  try{
   if(p.unrestrained_sword_twin_dragons_stacks>0&&this.is_unrestrained_sword(id)){this.reduce_idx_x_by_c(0,'unrestrained_sword_twin_dragons_stacks',1);this.play_card_inner(id,idx);}
   if(p.strike_twice_stacks>0){this.reduce_idx_x_by_c(0,'strike_twice_stacks',1);this.play_card_inner(id,idx);}
   this.currentCloudRepeat756(id,idx);
   if(p.crash_fist_double_stacks>0){
    // Adjacency-only Dream Footwork classification needs its original wrapper.
    check(!p.cards.some(c=>/^D1412[1-5]$/.test(c)),'756_dream_footwork_interaction');
    if(this.is_crash_fist(id)){if(!swogi[id].is_crash_fist_continue)this.reduce_idx_x_by_c(0,'crash_fist_double_stacks',1);this.play_card_inner(id,idx);}
   }
   if(p.m_fire_spirit_flame_eater_stacks>0&&(swogi[id].is_fire_spirit||swogi[id].is_earth_spirit)){this.reduce_idx_x_by_c(0,'m_fire_spirit_flame_eater_stacks',1);this.play_card_inner(id,idx);}
   check(!(p.ultimate_overcome_formation_stacks>0),'756_created_280_interaction');
   this.play_card_inner(id,idx);
  }finally{p.dream_crash_footwork_fake_crash_fist=0;p.currently_playing_card_idx=undefined;}
 };
 installed.add(game);
 return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),pending:[...states.values()].map(s=>({player_index:s.index,buff755:s.silence,buff756:s.pending})),recorded_action_log:false,training_label_allowed:false}:null};
}
