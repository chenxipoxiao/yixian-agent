import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='2c67f9860d4c3eab9874ac76798579dfb31acba4378abc2542093a568ca2f925',cache=new Map(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('dream_brush_load_unresolved:'+why);};
export function dreamBrushLoadFacts(root){
 if(cache.has(root))return cache.get(root);
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-dream-brush-load-v127.json'));
 check(crypto.createHash('sha256').update(bytes).digest('hex')===digest,'evidence_changed');const f=JSON.parse(bytes);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,f);return f;
}
export function registerDreamBrushLoad(root,swogi){
 for(const c of dreamBrushLoadFacts(root).cards){
  const prior=swogi[c.runtime_id];check(prior&&typeof prior.card_actions==='function','missing_native_metadata');
  check((prior.hp_cost??0)===0&&prior.qi_cost===0&&c.config.hpCost===0&&c.config.anima===0,'cost_changed');
  swogi[c.runtime_id]=Object.freeze({...prior,card_actions:g=>g.executeCurrentDreamBrushLoad(c.runtime_id)});
 }
}
const snap=p=>Object.fromEntries(['hp','max_hp','def','def_lost','qi','black_earth_turtle_stacks','moon_water_sword_formation_stacks'].map(k=>[k,p[k]]));
// Install immediately after GameState creation: other turn-start wrappers retain
// their existing positions around this core decay boundary.
export function installDreamBrushLoad(root,game,swogi,order=[0,1]){
 check(!installed.has(game),'already_installed');
 check(order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 const f=dreamBrushLoadFacts(root),cards=new Map(f.cards.map(c=>[c.runtime_id,c]));
 const seats=new Map(game.players.map((p,i)=>[p,order[i]])),events=[];
 game.executeCurrentDreamBrushLoad=function(id){
  const c=cards.get(id),p=this.players[0];check(c&&p.currently_triggering_card_id===id,'active_identity');
  const e={kind:c.kind,raw_card_id:c.raw_id,runtime_id:id,player_index:seats.get(p),trigger_depth:p.trigger_depth,before:snap(p)};events.push(e);
  if(c.kind==='dream_brush'){
   check(typeof this.consumeDreamBrushResultV127==='function','bound_card_result_required');
   this.increase_idx_def(0,c.config.def);this.consumeDreamBrushResultV127(c);
  }else{
   let n=0;for(const k of f.debuff_fields){check(Number.isSafeInteger(p[k]),'unknown_debuff:'+k);n+=Math.max(0,p[k]);}
   const amount=c.config.def+n*c.config.otherParams[0];check(Number.isSafeInteger(amount)&&amount<=2147483647,'def_overflow');
   e.debuff_layers=n;e.requested_def=amount;this.increase_idx_def(0,amount);
  }
  e.after=snap(p);
 };
 const decay=game.do_def_decay.bind(game);
 game.do_def_decay=function(...args){
  const p=this.players[0];if(!p.cards.some(id=>id==='D14154'||id==='D14155'))return decay(...args);
  check(Number.isSafeInteger(p.def)&&p.def>=0&&p.def<=2147483647,'invalid_def');
  const e={kind:'owner_turn_decay',player_index:seats.get(p),before:snap(p),copies:p.cards.filter(id=>id==='D14154'||id==='D14155').length};
  let rate=p.black_earth_turtle_stacks>0?Math.fround(0.2):Math.fround(0.5);
  if(p.moon_water_sword_formation_stacks>0){this.reduce_idx_x_by_c(0,'moon_water_sword_formation_stacks',1);rate=0;}
  const amount=p.def>0&&rate>0?Math.ceil(Math.fround(Math.fround(p.def)*rate)):0;
  check(amount>=0&&amount<=2147483647,'decay_overflow');e.rate=rate;e.requested_decay=amount;
  if(amount>0){this.reduce_idx_def(0,amount);e.after_def_callbacks=snap(p);this.increase_idx_hp(0,amount);}
  if(p.black_earth_turtle_stacks>0)this.for_each_x_add_y('black_earth_turtle_stacks','def');
  e.after=snap(p);events.push(e);
 };
 installed.add(game);
 return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),recorded_action_log:false,training_label_allowed:false}:null};
}
