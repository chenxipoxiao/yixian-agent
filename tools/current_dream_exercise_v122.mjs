import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='ad8e9466636c292732705e2e9a691fcb69cd4035ae18f50cdbfcc44e5d20c245',cache=new Map(),registered=new WeakSet(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('dream_exercise_unresolved:'+why);};
export function dreamExerciseFacts(root){
 if(cache.has(root))return cache.get(root);
 const b=fs.readFileSync(path.join(root,'data/inspection/current-dream-exercise-v122.json'));
 check(crypto.createHash('sha256').update(b).digest('hex')===digest,'evidence_changed');const f=JSON.parse(b);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,f);return f;
}
export function registerDreamExercise(root,swogi){
 check(!registered.has(swogi),'already_registered');
 for(const c of dreamExerciseFacts(root).cards){
  const p=swogi[c.runtime_id];check(p&&typeof p.card_actions==='function'&&p.qi_cost===0&&p.hp_cost===c.config.hpCost&&p.is_crash_fist,'native_metadata');
  swogi[c.runtime_id]=Object.freeze({...p,card_actions:g=>g.currentDreamExerciseActive?g.executeCurrentDreamExercise(c.runtime_id):p.card_actions(g)});
 }
 registered.add(swogi);
}
export function installDreamExercise(root,game,swogi,order=[0,1]){
 check(!installed.has(game),'already_installed');check(order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'order');
 const cards=new Map(dreamExerciseFacts(root).cards.map(c=>[c.runtime_id,c])),state=new Map(game.players.map((p,i)=>[p,{index:order[i],remaining705:0,used706:0}])),events=[];
 game.currentDreamExerciseActive=game.players.some(p=>p.cards.some(id=>cards.has(id)));
 const pristine=p=>check(p.dream_exercise_fist_atk_physique_pct===0&&p.later_dream_exercise_fist_atk_physique_pct===0,'unknown_legacy_percentage');
 if(game.currentDreamExerciseActive)game.players.forEach(pristine);
 game.executeCurrentDreamExercise=function(id){
  const p=this.players[0],s=state.get(p),c=cards.get(id);check(c&&p.currently_triggering_card_id===id,'card_identity');pristine(p);
  const e={kind:'card_body',raw_card_id:c.raw_id,player_index:s.index,trigger_depth:p.trigger_depth,remaining705_before:s.remaining705,physique_before:p.physique};events.push(e);
  for(let i=0;i<c.config.attackCount;i++)this.atk(c.config.attack);
  s.remaining705++;check(Number.isSafeInteger(s.remaining705)&&s.remaining705<=2147483647,'705_overflow');
  e.remaining705_after_body=s.remaining705;e.physique_after=p.physique;
 };
 game.currentDreamExerciseAfterHit=function(playerIdx,isExtra,injury){
  const p=this.players[playerIdx],s=state.get(p),id=p.currently_triggering_card_id;pristine(p);
  if(isExtra||!id||(!cards.has(id)&&s.remaining705===0))return;
  check(Number.isSafeInteger(injury)&&injury>=0&&injury<=2147483647,'injury_domain');
  const amount=injury>0?Math.floor(Math.fround(Math.fround(injury)*Math.fround(0.4))):0;
  const e={kind:'hit_705',player_index:s.index,runtime_id:id,trigger_depth:p.trigger_depth,injury,requested_physique:amount,remaining705:s.remaining705,physique_before:p.physique};
  if(injury>0)this.increase_idx_physique(playerIdx,amount);
  if(s.remaining705>0)s.used706=1;
  e.used706=s.used706;e.physique_after=p.physique;events.push(e);
 };
 const post=game.do_post_crash_fist.bind(game);
 game.do_post_crash_fist=function(id){
  const value=post(id);if(!this.currentDreamExerciseActive)return value;
  const s=state.get(this.players[0]);
  if(s.used706){check(s.used706===1&&s.remaining705>=1,'706_without705');const before=s.remaining705;s.remaining705-=s.used706;s.used706=0;
   events.push({kind:'post_card_706',player_index:s.index,runtime_id:id,remaining705_before:before,remaining705_after:s.remaining705});}
  return value;
 };
 installed.add(game);return {forPlayer:p=>({...state.get(p)}),metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),recorded_action_log:false,training_label_allowed:false}:null};
}
