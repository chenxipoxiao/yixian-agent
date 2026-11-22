// Temporary capacity is owned by the player; permanent chase capacity survives cleanup.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const checked=new Map(),installed=new WeakSet();
const fail=why=>{throw new Error('temporary_chase_unresolved:'+why);};
// Filled from the frozen source audit before candidate registration.
const digest='f865f78998e3dce4c903ede0bf9b63e8d2bb62e33573eea8bfdfeba2e90d1050';
function factsAt(root) {
 if(checked.has(root))return checked.get(root);
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-temporary-chase-v61.json'));
 if(crypto.createHash('sha256').update(bytes).digest('hex')!==digest)fail('evidence_changed');
 const facts=JSON.parse(bytes);
 for(const [p,h] of Object.entries(facts.source_sha256))
  if(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')!==h)fail('source_changed:'+p);
 checked.set(root,facts);return facts;
}
export function registerTemporaryChase(root,swogi) {
 for(const c of factsAt(root).cards) {
  if(Object.hasOwn(swogi,c.runtime_id))fail('alias_collision');
  swogi[c.runtime_id]=Object.freeze({...swogi['601011'],name:c.config.name,names:[c.config.name],
   marking:'no_marking',qi_cost:0,hp_cost:0,opening:undefined,is_continuous:false,is_consumption:false,
   card_actions:g=>{
    if(typeof g.current_temporary_chase_card!=='function')fail('runtime_missing');
    g.current_temporary_chase_card(c.raw_id,c.runtime_id);
   }});
 }
}
export function installTemporaryChase(root,game,order=[0,1]) {
 const facts=factsAt(root);
 if(installed.has(game))fail('already_installed');
 if(!Array.isArray(order)||order.length!==2||new Set(order).size!==2||!order.every(x=>x===0||x===1))fail('invalid_order');
 const seats=new Map(game.players.map((p,i)=>[p,order[i]])),pending=new WeakMap(),events=[];
 const integer=x=>Number.isInteger(x)&&x>=0&&x<=2147483647;
 const state=p=>({hp:p.hp,def:p.def,max_chases:p.max_chases,chases:p.chases,pending572:pending.get(p)??0});
 game.current_temporary_chase_card=function(raw,id) {
  const c=facts.cards.find(c=>c.raw_id===raw),p=this.players[0];
  if(!c||c.runtime_id!==id||p.currently_triggering_card_id!==id)fail('card_identity');
  const event={kind:'card_body',player_index:seats.get(p),raw_id:raw,slot:p.currently_triggering_card_idx,
   trigger_depth:p.trigger_depth,before:state(p),attack:c.config.attack,attack_count:c.config.attackCount};
  for(let n=0;n<c.config.attackCount;n++)this.atk(c.config.attack);
  const count=pending.get(p)??0;
  if(!integer(p.max_chases)||!integer(count)||!integer(p.max_chases+1)||!integer(count+1))fail('capacity_range');
  p.max_chases+=1;pending.set(p,count+1);
  this.chase();
  event.after=state(p);events.push(event);
 };
 game.current_temporary_chase_cleanup=function() {
  const p=this.players[0],count=pending.get(p);
  if(count===undefined)return;
  if(!integer(count)||!integer(p.max_chases-count))fail('cleanup_range');
  const before=state(p);p.max_chases-=count;pending.delete(p);
  events.push({kind:'owner_turn_end',player_index:seats.get(p),removed572:count,before,after:state(p)});
 };
 installed.add(game);
 return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),training_label_allowed:false}:null,
  pendingFor:p=>pending.get(p)??0};
}
