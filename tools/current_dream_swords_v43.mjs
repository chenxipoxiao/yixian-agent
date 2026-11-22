// Reuse pinned native card bodies; preserve the client's two grade-5 intent
// requests. The observer records simulator events, never replay outcome input.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='434f9bcd2ccb5c667aae7ca9ae241c0978f47d8275759271d0b8fc2ca9f7acb6';
const installed=new WeakSet();
const checked=new Map();
function factsAt(root) {
 if(checked.has(root))return checked.get(root);
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-dream-swords-v43.json'));
 if(crypto.createHash('sha256').update(raw).digest('hex')!==digest)throw new Error('Dream swords evidence changed');
 const f=JSON.parse(raw);
 for(const [p,h] of Object.entries(f.source_sha256))
  if(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')!==h)throw new Error('Dream swords source changed:'+p);
 checked.set(root,f);return f;
}
export function registerDreamSwords(root,swogi) {
 const f=factsAt(root);
 for(const c of f.cards) {
  const card=swogi[c.runtime_id],cloud=c.raw_id%10000===70;
  if(typeof card?.card_actions!=='function'||card.name!==(cloud?'Dream - Cloud Sword - Riddle':'Dream - Dharma Spirit Sword')
    ||card.qi_cost!==0||(card.hp_cost??0)!==0||!c.config.noUpgrade||!c.config.hidden)
   throw new Error('Dream sword pinned binding changed:'+c.runtime_id);
  if(c.runtime_id==='D11035')swogi[c.runtime_id]=Object.freeze({...card,card_actions:game=>{
   game.atk(c.config.attack);
   game.add_c_of_x(c.config.otherParams[0],'cloud_sea');
   game.increase_idx_x_by_c(0,'sword_intent',c.config.otherParams[1]);
   const extra=c.config.otherParams[1]*game.players[0].cloud_sword_used_count;
   if(extra>0)game.increase_idx_x_by_c(0,'sword_intent',extra);
  }});
 }
}
const state=(g,p)=>({hp:p.hp,max_hp:p.max_hp,qi:p.qi,sword_qi:p.sword_qi,sword_intent:p.sword_intent,
 cloud_sea:p.cloud_sea,consecutive_clouds:p.cloud_sword_chain_count,cumulative_clouds:p.cloud_sword_used_count,
 opponent_hp:g.players[1].hp,opponent_def:g.players[1].def});
export function installDreamSwordObserver(root,game,swogi,order=[0,1]) {
 if(installed.has(game))throw new Error('Dream sword observer already installed');
 if(!Array.isArray(order)||order.length!==2||new Set(order).size!==2||!order.every(i=>i===0||i===1))throw new Error('Dream sword observer invalid order');
 const f=factsAt(root),byId=new Map(f.cards.map(c=>[c.runtime_id,c]));
 const seats=new Map(game.players.map((p,i)=>[p,order[i]])),events=[];
 const body=game.just_do_the_card_and_nothing_else.bind(game);
 game.just_do_the_card_and_nothing_else=function(card) {
  const p=this.players[0],id=p.currently_triggering_card_id,c=byId.get(id);
  if(!c)return body(card);
  if(card!==swogi[id])throw new Error('Dream sword action identity changed');
  const e={kind:'card_body',player_index:seats.get(p),raw_id:c.raw_id,runtime_id:id,
   slot:p.currently_triggering_card_idx,trigger_depth:p.trigger_depth,before:state(this,p)};
  events.push(e);const result=body(card);e.after=state(this,p);return result;
 };
 const swordQi=game.do_sword_qi.bind(game);
 game.do_sword_qi=function(id) {
  const p=this.players[0];
  const relevant=p.sword_qi>0&&p.cards.some(cid=>byId.has(cid)&&byId.get(cid).raw_id%10000===75)
   &&(this.is_sword(id)||this.is_spirit_sword(id));
  if(!relevant)return swordQi(id);
  const e={kind:'sword_qi_passive',player_index:seats.get(p),runtime_id:id,requested_damage:p.sword_qi,
   slot:p.currently_triggering_card_idx,trigger_depth:p.trigger_depth,before:state(this,p)};
  events.push(e);const result=swordQi(id);e.after=state(this,p);return result;
 };
 installed.add(game);
 return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),
  recorded_action_log:false,training_label_allowed:false}:null};
}
