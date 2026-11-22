import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='65c11a8898d87449f3f58a7bf613d536a8cbf3e689bd41b464df96495884d804',cache=new Map(),registered=new WeakSet(),installed=new WeakSet(),native=new Map();
const check=(ok,why)=>{if(!ok)throw new Error('dream_rejuvenation_unresolved:'+why);};
export function dreamRejuvenationFacts(root){
 if(cache.has(root))return cache.get(root);
 const b=fs.readFileSync(path.join(root,'data/inspection/current-dream-rejuvenation-v121.json'));
 check(crypto.createHash('sha256').update(b).digest('hex')===digest,'evidence_changed');const f=JSON.parse(b);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,f);return f;
}
export function registerDreamRejuvenation(root,swogi){
 check(!registered.has(swogi),'already_registered');
 for(const c of dreamRejuvenationFacts(root).cards){
  const p=swogi[c.runtime_id];check(p&&typeof p.card_actions==='function'&&p.qi_cost===0&&(p.hp_cost??0)===0,'native_metadata');
  native.set(c.runtime_id,p.card_actions);
  swogi[c.runtime_id]=Object.freeze({...p,card_actions:g=>g.currentDreamRejuvenationActive?g.executeCurrentDreamRejuvenation(c.runtime_id):p.card_actions(g)});
 }
 registered.add(swogi);
}
export function installDreamRejuvenation(root,game,swogi,order=[0,1]){
 check(!installed.has(game),'already_installed');check(order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'order');
 const cards=new Map(dreamRejuvenationFacts(root).cards.map(c=>[c.runtime_id,c])),indexes=new Map(game.players.map((p,i)=>[p,order[i]])),events=[];
 game.currentDreamRejuvenationActive=game.players.some(p=>p.cards.some(id=>cards.has(id)));
 game.executeCurrentDreamRejuvenation=function(id){
  const p=this.players[0],q=this.players[1],c=cards.get(id),n=p.dream_revitalized_played_count;
  check(c&&p.currently_triggering_card_id===id&&native.has(id),'card_identity');
  check(Number.isSafeInteger(n)&&n>=0&&n<=20,'664_numeric_domain');
  check(p.dream_revitalized_doublings===0,'pending_multiplier');
  const e={raw_card_id:c.raw_id,player_index:indexes.get(p),trigger_depth:p.trigger_depth,count_before:n,base_attack:c.config.attack,
   doublings:c.config.level===5?n:Math.min(1,n),opponent_hp_before:q.hp};events.push(e);
  native.get(id)(this);
  check(p.dream_revitalized_played_count===n+1,'unexpected_664_change');check(p.dream_revitalized_doublings===0,'multiplier_not_consumed');
  e.count_after=p.dream_revitalized_played_count;e.opponent_hp_after=q.hp;
 };
 installed.add(game);return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),recorded_action_log:false,training_label_allowed:false}:null};
}
