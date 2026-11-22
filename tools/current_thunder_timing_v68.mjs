import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='b338045a15e00ce73895b05b82462991105cb9d05322fa84de261e0b0773ea6e',cache=new Map(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('thunder_timing_unresolved:'+why);};
function factsAt(root){
 if(cache.has(root))return cache.get(root);
 const b=fs.readFileSync(path.join(root,'data/inspection/current-thunder-timing-v68.json'));
 check(crypto.createHash('sha256').update(b).digest('hex')===digest,'evidence_changed');const f=JSON.parse(b);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,f);return f;
}
export function installThunderTiming(root,game,swogi,order=[0,1]){
 const f=factsAt(root),byCard=new Map(f.cards.map(c=>[swogi[c.runtime_id],c]));
 check(!byCard.has(undefined),'missing_card_identity');check(!installed.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(x=>x===0||x===1),'invalid_order');
 const seats=new Map(game.players.map((p,i)=>[p,order[i]])),events=[];
 const body=game.just_do_the_card_and_nothing_else.bind(game);
 game.just_do_the_card_and_nothing_else=function(card){
  const c=byCard.get(card);if(!c)return body(card);
  const p=this.players[0];check(p.currently_triggering_card_id===c.runtime_id,'card_identity');
  const e={kind:'five_thunders_body',player_index:seats.get(p),raw_card_id:c.raw_id,slot:p.currently_triggering_card_idx,
   trigger_depth:p.trigger_depth,hexagram_before:p.hexagram,draws:[],base_attack:c.config.otherParams[1]};
  events.push(e);
  // The client fixes all five successes before any hit callback can alter state.
  for(let i=0;i<5;i++)e.draws.push(this.if_c_pct(c.config.otherParams[0]));
  e.hits=e.draws.filter(Boolean).length;e.hexagram_before_hits=p.hexagram;
  // Do not aggregate: defense, guard, injury and on-hit hooks run per hit.
  // Zero successes means no attack; do not call the scalar zero-count fallback.
  for(let i=0;i<e.hits;i++)this.atk(e.base_attack);
  e.hexagram_after=p.hexagram;
 };
 installed.add(game);
 return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),
  recorded_action_log:false,random_outcomes_reconstructed:false,training_label_allowed:false}:null};
}
