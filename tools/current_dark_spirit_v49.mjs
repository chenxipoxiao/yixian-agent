// Source-bound Card336. Gains use normal callbacks; count their resulting state.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='23994d72abf661cd9686e953e3effb3819c65da7c8e91a1c62ae46f55604b1e9';
const checked=new Map(),installed=new WeakSet();
function factsAt(root) {
 if(checked.has(root))return checked.get(root);
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-dark-spirit-v49.json'));
 if(crypto.createHash('sha256').update(raw).digest('hex')!==digest)throw new Error('Dark Spirit evidence changed');
 const f=JSON.parse(raw);
 for(const [p,h] of Object.entries(f.source_sha256))
  if(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')!==h)throw new Error('Dark Spirit source changed:'+p);
 checked.set(root,f);return f;
}
const fields=['internal_injury','weaken','flaw','decrease_atk','entangle','wound','styx','indigestion'];
function countDebuffs(p) {
 return fields.reduce((sum,k)=>{
  if(!Number.isSafeInteger(p[k]))throw new Error('dark_spirit_unresolved:non_integer_debuff:'+k);
  return sum+Math.max(0,p[k]);
 },0);
}
export function registerDarkSpirit(root,swogi) {
 const f=factsAt(root);
 if(JSON.stringify(Object.values(f.debuff_count.fields))!==JSON.stringify(fields))throw new Error('Dark Spirit category mapping changed');
 for(const c of f.cards) {
  if(Object.hasOwn(swogi,c.runtime_id))throw new Error('Dark Spirit alias collision');
  swogi[c.runtime_id]=Object.freeze({...swogi['601011'],name:'Dark Spirit Possession',names:['Dark Spirit Possession',c.config.name],
   marking:'dx',qi_cost:0,hp_cost:0,is_add_qi:true,opening:undefined,
   card_actions:game=>{
    game.increase_idx_qi(0,c.config.anima);
    game.increase_idx_x_by_c(0,'increase_atk',c.config.otherParams[0]);
    game.increase_idx_debuff(0,'decrease_atk',c.config.otherParams[0]);
    game.increase_idx_x_by_c(0,'agility',countDebuffs(game.players[0]));
   }});
 }
}
const state=p=>Object.fromEntries(['hp','max_hp','qi','increase_atk','agility','hexproof',...fields].map(k=>[k,p[k]]));
export function installDarkSpiritObserver(root,game,swogi,order=[0,1]) {
 if(installed.has(game))throw new Error('Dark Spirit observer already installed');
 if(!Array.isArray(order)||order.length!==2||new Set(order).size!==2||!order.every(i=>i===0||i===1))throw new Error('Dark Spirit observer invalid order');
 const f=factsAt(root),byId=new Map(f.cards.map(c=>[c.runtime_id,c]));
 const seats=new Map(game.players.map((p,i)=>[p,order[i]])),events=[];
 const body=game.just_do_the_card_and_nothing_else.bind(game);
 game.just_do_the_card_and_nothing_else=function(card) {
  const p=this.players[0],id=p.currently_triggering_card_id,c=byId.get(id);
  if(!c)return body(card);
  if(card!==swogi[id])throw new Error('Dark Spirit action identity changed');
  const e={kind:'card_body',player_index:seats.get(p),raw_id:c.raw_id,runtime_id:id,
   slot:p.currently_triggering_card_idx,trigger_depth:p.trigger_depth,before:state(p)};
  events.push(e);const result=body(card);e.after=state(p);e.positive_debuff_layers_after=countDebuffs(p);return result;
 };
 installed.add(game);
 return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),
  recorded_action_log:false,training_label_allowed:false}:null};
}
