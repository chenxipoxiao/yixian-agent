import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='e6a1c5b999a580ed70f4e7bdf6f0f4490d6d40117c98a3e77c78bc1bd0667863',cache=new Map(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('dream_formations_v163:'+why);};
export function dreamFormationFacts(root){
 if(cache.has(root))return cache.get(root);
 const b=fs.readFileSync(path.join(root,'data/inspection/current-dream-formations-v163.json'));
 check(crypto.createHash('sha256').update(b).digest('hex')===digest,'evidence_changed');const f=JSON.parse(b);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,f);return f;
}
export function registerDreamFormations(root,swogi){
 for(const c of dreamFormationFacts(root).cards){
  const p=swogi[c.runtime_id];check(p&&typeof p.card_actions==='function','native_metadata_missing');
  check(p.qi_cost===0&&(p.hp_cost??0)===0&&c.config.noUpgrade===true&&c.config.rarity===0,'configuration_changed');
  swogi[c.runtime_id]=Object.freeze({...p,card_actions:g=>g.executeDreamFormation163(c.runtime_id)});
 }
}
const fields=['hp','max_hp','def','qi','sword_intent','hexagram','dream_consonance_qi_gives_def_stacks','dream_consonance_sword_intent_gives_def_stacks','dream_yin_yang_formation_def_stacks','dream_yin_yang_formation_hp_stacks'];
const snap=p=>Object.fromEntries(fields.map(k=>[k,p[k]]));
export function installDreamFormations(root,game,swogi,input,order=[0,1]){
 check(!installed.has(game),'already_installed');
 const facts=dreamFormationFacts(root),byId=new Map(facts.cards.map(c=>[c.runtime_id,c]));
 const seats=new Map(game.players.map((p,i)=>[p,order[i]])),events=[],contexts=[];
 // Native contexts have no seasonal primitive wrapper. Preserve every other
 // path and explicitly verify the delegated method before executing692.
 if(input.season_batch===undefined){
  const original=game.increase_idx_x_by_c,native=Object.getPrototypeOf(game).increase_idx_x_by_c;
  game.increase_idx_x_by_c=function(idx,x,c){
   const p=this.players[idx];
   if(x!=='sword_intent'||!(c>0)||!(p.dream_consonance_sword_intent_gives_def_stacks>0))return original.call(this,idx,x,c);
   check(original===native,'unintegrated_native_sword_intent_wrapper');
   check(Number.isSafeInteger(c)&&Number.isSafeInteger(p.sword_intent+c)&&p.sword_intent+c<=2147483647,'sword_intent_overflow');
   p.sword_intent+=c;
   this.increase_idx_def(idx,c*p.dream_consonance_sword_intent_gives_def_stacks);
   this.log('gained '+c+' '+x+'. Now have '+p[x]+' '+x);
  };
 }

 const active=p=>fields.slice(6).some(k=>p[k]>0);
 for(const [method,kind] of [['increase_idx_qi','qi'],['increase_idx_hexagram','hexagram'],['increase_idx_x_by_c','buff']]){
  const original=game[method].bind(game);
  game[method]=function(idx,...args){
   const p=this.players[idx],resource=kind==='buff'?args[0]:kind,n=kind==='buff'?args[1]:args[0];
   if(!active(p)||!['qi','hexagram','sword_intent'].includes(resource)||!(n>0))return original(idx,...args);
   const e={kind:'resource_gain',player_index:seats.get(p),resource,requested:n,before:snap(p),effects:[]};events.push(e);contexts.push(e);
   try{const out=original(idx,...args);e.after=snap(p);return out;}finally{contexts.pop();}
  };
 }
 for(const method of ['increase_idx_def','increase_idx_hp']){
  const original=game[method].bind(game);
  game[method]=function(idx,n,...args){
   const e=contexts.at(-1),p=this.players[idx];
   if(e&&e.player_index===seats.get(p))e.effects.push({method,requested:n,before:snap(p)});
   return original(idx,n,...args);
  };
 }
 game.executeDreamFormation163=function(id){
  const c=byId.get(id),p=this.players[0];check(c&&p.currently_triggering_card_id===id,'card_identity');
  // The verified sword-intent callback is integrated in the season primitive.
  // Both native and seasonal positive intent readers now use the same692 ordering.
  const e={kind:'card_body',player_index:seats.get(p),raw_card_id:c.raw_id,runtime_id:id,trigger_depth:p.trigger_depth,before:snap(p)};events.push(e);
  if(c.kind==='consonance'){
   this.increase_idx_def(0,c.config.def);this.continuous();
   this.increase_idx_x_by_c(0,'dream_consonance_qi_gives_def_stacks',c.config.otherParams[0]);
   if(c.config.otherParams[1]>0)this.increase_idx_x_by_c(0,'dream_consonance_sword_intent_gives_def_stacks',c.config.otherParams[1]);
  }else if(c.kind==='yin_yang'){
   check(c.config.def===0&&c.config.otherParams[2]===0,'unadmitted_reward_variant');this.continuous();
   this.increase_idx_x_by_c(0,'dream_yin_yang_formation_def_stacks',c.config.otherParams[0]);
   if(c.config.level>=3)this.increase_idx_x_by_c(0,'dream_yin_yang_formation_hp_stacks',c.config.otherParams[1]);
  }else{
   this.increase_idx_hexagram(0,c.config.guaXiang);this.consumption();
  }
  e.after=snap(p);
 };
 installed.add(game);
 return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),recorded_action_log:false,training_label_allowed:false}:null};
}
