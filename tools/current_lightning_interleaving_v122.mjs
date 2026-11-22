import {dreamExerciseFacts} from './current_dream_exercise_v122.mjs';
import {dreamRejuvenationFacts} from './current_dream_rejuvenation_v121.mjs';
import {dreamQiFlowerFacts} from './current_dream_qi_flower_v119.mjs';
import {nethermindFacts} from './current_nethermind_v118.mjs';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {lightningRepeatFacts} from './current_lightning_repeat_v116.mjs';
const digest='1defeae5b1ad72ba29f11a1efd865712c8f87ce60b75f18fa4fc4f81afc279c9';
const bodyDigest='74ea1d178f6c35aa6fd5c4f68d69c1062f9adacb634644224512568f0843c51b';
const checkedRoots=new Set(),installed=new WeakSet();
const check=(v,m)=>{if(!v)throw new Error('lightning_interleaving_unresolved:'+m);};
function verify(root){
 if(checkedRoots.has(root))return;
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-lightning-interleaving-v117.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');
 for(const [p,h] of Object.entries(JSON.parse(raw).source_sha256))
  check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 checkedRoots.add(root);
}
const snap=p=>({hp:p.hp,max_hp:p.max_hp,qi:p.qi,hexagram:p.hexagram,trigger_depth:p.trigger_depth});
export function installLightningInterleaving(root,game,swogi,order=[0,1]){
 verify(root);check(!installed.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 const original=lightningRepeatFacts(root),f={...original,name_contains_thunder:{...original.name_contains_thunder}};
 for(const c of nethermindFacts(root).cards){check(!Object.hasOwn(f.name_contains_thunder,c.runtime_id),'duplicate_name');f.name_contains_thunder[c.runtime_id]=c.config.name.includes('雷');}
 for(const c of dreamQiFlowerFacts(root).cards){const value=c.config.name.includes('雷');check(!Object.hasOwn(f.name_contains_thunder,c.runtime_id)||f.name_contains_thunder[c.runtime_id]===value,'dream_name_mismatch');f.name_contains_thunder[c.runtime_id]=value;}
 for(const c of dreamRejuvenationFacts(root).cards){const value=c.config.name.includes('雷');check(!Object.hasOwn(f.name_contains_thunder,c.runtime_id)||f.name_contains_thunder[c.runtime_id]===value,'dream_rejuvenation_name');f.name_contains_thunder[c.runtime_id]=value;}
 for(const c of dreamExerciseFacts(root).cards){const value=c.config.name.includes('雷');check(!Object.hasOwn(f.name_contains_thunder,c.runtime_id)||f.name_contains_thunder[c.runtime_id]===value,'dream_exercise_name');f.name_contains_thunder[c.runtime_id]=value;}
 const cards=new Map(f.cards.map(c=>[c.runtime_id,c]));
 const states=new Map(game.players.map((p,i)=>[p,{index:order[i],pending:0}])),events=[],interleavings=[];
 game.executeCurrentLightningRepeat=function(id){
  const p=this.players[0],s=states.get(p),c=cards.get(id);
  check(c&&p.currently_triggering_card_id===id,'card_identity');
  const e={kind:'card_body',raw_card_id:c.raw_id,player_index:s.index,slot:p.currently_triggering_card_idx,
   before:snap(p),pending_before:s.pending};events.push(e);
  this.increase_idx_hexagram(0,c.config.guaXiang);
  check(Number.isSafeInteger(s.pending)&&s.pending>=0&&s.pending<2147483647,'763_overflow');
  s.pending+=1;e.after=snap(p);e.pending_after=s.pending;
 };
 const play=game.play_card.bind(game);
 const supported=p=>{
  for(const field of ['unrestrained_sword_twin_dragons_stacks','crash_fist_double_stacks','m_fire_spirit_flame_eater_stacks'])
   check(!(p[field]>0),'other_repeat_interaction:'+field);
 };
 game.play_card=function(id,idx){
  const p=this.players[0],s=states.get(p);
  if(!s.pending&&!cards.has(id)&&!p.cards.some(c=>cards.has(c)))return play(id,idx);
  check(p.trigger_depth===0&&Number.isInteger(idx)&&p.cards[idx]===id,'outer_card_identity');
  supported(p);check(Object.hasOwn(f.name_contains_thunder,id),'unknown_card_name:'+id);
  const twice=p.strike_twice_stacks>0;
  if(!twice&&!(s.pending>0&&f.name_contains_thunder[id]))return play(id,idx);
  // Client280 runs after the complete repeat section, not per inner execution.
  check(!(p.ultimate_overcome_formation_stacks>0),'280_repeat_interaction');
  p.this_card_chases=0;p.currently_playing_card_idx=idx;p.dream_crash_footwork_fake_crash_fist=0;
  let t=null;
  if(twice){
   t={kind:'205_before_763',player_index:s.index,runtime_id:id,slot:idx,
    strike_twice_before:p.strike_twice_stacks,pending_before:s.pending,before:snap(p)};interleavings.push(t);
   this.reduce_idx_x_by_c(0,'strike_twice_stacks',1);
   this.play_card_inner(id,idx);
   t.after_205=snap(p);t.pending_after_205=s.pending;t.strike_twice_after_205=p.strike_twice_stacks;
   // This body may have created a later repeat condition. Never silently skip it.
   supported(p);check(!(p.ultimate_overcome_formation_stacks>0),'280_repeat_interaction');
  }
  let e=null;
  // Read the current763 after205; do not precompute a total execution count.
  if(s.pending>0&&f.name_contains_thunder[id]){
   e={kind:'763_repeat_before_main',player_index:s.index,runtime_id:id,slot:idx,
    pending_before:s.pending,before:snap(p)};events.push(e);
   s.pending-=1;this.play_card_inner(id,idx);
   e.after_repeat=snap(p);e.pending_after_repeat=s.pending;
   supported(p);check(!(p.ultimate_overcome_formation_stacks>0),'280_repeat_interaction');
  }
  this.play_card_inner(id,idx);
  if(e){e.after_main=snap(p);e.pending_after_main=s.pending;}
  if(t){t.after_main=snap(p);t.pending_after_main=s.pending;t.strike_twice_after_main=p.strike_twice_stacks;}
  p.dream_crash_footwork_fake_crash_fist=0;p.currently_playing_card_idx=undefined;
 };
 installed.add(game);
 return {
  metadata:()=>events.length?{evidence_sha256:bodyDigest,events:structuredClone(events),recorded_action_log:false,training_label_allowed:false}:null,
  interleavingMetadata:()=>interleavings.length?{evidence_sha256:digest,events:structuredClone(interleavings),recorded_action_log:false,training_label_allowed:false}:null
 };
}
