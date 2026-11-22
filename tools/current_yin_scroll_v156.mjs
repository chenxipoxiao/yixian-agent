// Current pinned Card_214 body. Historical yisim and bridge v149 stay frozen.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='a67e3d0bac968588fee2aa716d3f3b16cc98ffc55c495986c569666ec82fca61',cache=new Map(),registered=new WeakSet(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('yin_scroll_v156:'+why);};
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
export function yinScrollFacts(root){
 if(cache.has(root))return cache.get(root);
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-yin-scroll-v156.json'));
 check(hash(raw)===digest,'evidence_changed');const facts=JSON.parse(raw);
 for(const [name,h] of Object.entries(facts.source_sha256))check(hash(fs.readFileSync(path.join(root,name)))===h,'source_changed:'+name);
 check(facts.cards.length===3&&facts.cards.every(c=>c.config.anima===0&&c.config.otherParams[2]===50),'unsupported_values');
 cache.set(root,facts);return facts;
}
export function registerYinScroll(root,swogi){
 check(!registered.has(swogi),'already_registered');
 for(const c of yinScrollFacts(root).cards){
  const old=swogi[c.runtime_id];check(old&&old.is_continuous&&typeof old.card_actions==='function','native_identity');
  swogi[c.runtime_id]={...old,is_add_qi:false,card_actions:g=>g.executeYinScroll156(c.runtime_id)};
 }
 registered.add(swogi);
}
const snap=p=>Object.fromEntries(['hp','max_hp','qi','weaken','flaw','jade_scroll_of_yin_symbol_stacks'].map(k=>[k,p[k]]));
export function installYinScroll(root,game,swogi,order=[0,1]){
 check(!installed.has(game),'already_installed');
 check(order.length===2&&new Set(order).size===2&&order.every(x=>x===0||x===1),'player_order');
 const facts=yinScrollFacts(root),cards=new Map(facts.cards.map(c=>[c.runtime_id,c]));
 const seats=new Map(game.players.map((p,i)=>[p,order[i]])),events=[];
 game.executeYinScroll156=function(id){
  const c=cards.get(id),p=this.players[0],target=this.players[1];
  check(c&&p.currently_triggering_card_id===id&&swogi[id],'card_identity');
  const e={raw_card_id:c.raw_id,player_index:seats.get(p),slot:p.currently_triggering_card_idx,
   trigger_depth:p.trigger_depth,before:snap(p),opponent_before:snap(target)};events.push(e);
  // IL 0x130..0x171: separate ModifyMaxHp then ModifyHp calls. Existing
  // gain/antiheal/overflow consumers remain active; no direct HP assignment.
  this.increase_idx_max_hp(0,c.config.otherParams[3]);
  this.increase_idx_hp(0,c.config.otherParams[3]);
  // IL 0x1e5..0x21c applies the two debuffs, then 0x291..0x2ad SETS440.
  this.add_enemy_c_of_x(c.config.otherParams[0],'weaken');
  this.add_enemy_c_of_x(c.config.otherParams[1],'flaw');
  target.jade_scroll_of_yin_symbol_stacks=c.config.otherParams[2];
  // The retained damage consumer implements presence =>40+10=50 percent.
  // Its constant is admitted only by the exact50 check in the facts loader.
  this.continuous();e.after=snap(p);e.opponent_after=snap(target);
 };
 installed.add(game);
 return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),
  historical_qi_gain_removed:true,client440_value:50,independent_acceptance:false,training_label_allowed:false}:null};
}
