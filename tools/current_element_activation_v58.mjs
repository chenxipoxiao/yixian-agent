// Current7028/7084, attached only to explicitly owned battle contexts.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='a01030ff71f974a33dc99fc6e37f51e04b65144abf66c148d0465fe15ffb95c8',installed=new WeakSet();
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const check=(ok,message)=>{if(!ok)throw new Error('element_activation_unresolved:'+message);};
export function createElementActivation(root,game,value,order=[0,1]) {
 if(value===undefined)return null;
 check(object(value)&&Object.keys(value).length===2&&Array.isArray(value.players)&&value.players.length===2,'explicit_players_required');
 check(value.players.every(a=>Array.isArray(a)&&new Set(a).size===a.length&&a.every(id=>[7028,7084].includes(id))),'invalid_ownership');
 check(value.players.some(a=>a.length),'owner_required');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 check(Array.isArray(value.innate_talents)&&value.innate_talents.length===2&&value.innate_talents.every(a=>Array.isArray(a)&&new Set(a).size===a.length&&a.every(id=>[10109,20109,30109,40109,50109].includes(id))),'explicit_innate_talents_required');
 check(!installed.has(game),'already_installed');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-element-activation-v58.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');
 const facts=JSON.parse(raw);
 for(const [file,hash] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,file))).digest('hex')===hash,'source_changed:'+file);
 const states=new Map(game.players.map((p,i)=>[p,{index:order[i],ids:new Set(value.players[order[i]]),talents:new Set(value.innate_talents[order[i]]),opened:false}]));
 const events=[],fields=new Map(Object.entries(facts.activation_fields).map(([id,field])=>[field,Number(id)]));
 const snapshot=p=>Object.fromEntries(['def',...fields.keys()].map(k=>[k,p[k]]));
 const emit=(p,id,phase,extra={})=>{const e={player_index:states.get(p).index,strategy_id:id,phase,...extra};events.push(e);return e;};
 const nativeActivate=game.increase_idx_activate.bind(game);
 game.increase_idx_activate=function(idx,field,amount){
  const p=this.players[idx],s=states.get(p);
  if(!s?.ids.has(7084))return nativeActivate(idx,field,amount);
  check(fields.has(field)&&Number.isSafeInteger(amount)&&amount>=0&&amount<=2147483647,'invalid_activation_gain');
  if(amount===0)return nativeActivate(idx,field,amount);
  const result=nativeActivate(idx,field,amount),buff=fields.get(field);
  // Native activation resolves its existing callbacks and increments the
  // counter.7084 is the last gameplay branch in current ModifyBuffValue,
  // after411 (still rejected by the compiler). Nested earth uses this same
  // entry point, so ordinary activation rewards and7084's DEF both execute.
  if(buff===239||buff===241){
   const e=emit(p,7084,'positive_activation_tail_after411',{buff_id:buff,requested_gain:amount,before:snapshot(p)});
   if(buff===239)this.increase_idx_activate(idx,facts.activation_fields['241'],1);
   else this.increase_idx_def(idx,facts.effects['7084'].def);
   e.after=snapshot(p);
  }
  return result;
 };
 installed.add(game);let boundaryInstalled=false;
 return {
  installOpening(){
   check(!boundaryInstalled,'duplicate_opening_boundary');boundaryInstalled=true;
   const previous=game.do_plant_start_permanent_buffs.bind(game);
   game.do_plant_start_permanent_buffs=function(...args){
    const p=this.players[0],s=states.get(p);
    if(s.ids.has(7028)&&!s.opened){
     s.opened=true;
     for(const [talent,buffs] of facts.effects['7028'].ordered_branches){
      if(!s.talents.has(talent))continue;
      for(const buff of buffs){
       const e=emit(p,7028,'owner_season_start',{talent_id:talent,buff_id:buff,requested_gain:1,before:snapshot(p)});
       this.increase_idx_activate(0,facts.activation_fields[buff],1);
       e.after=snapshot(p);
      }
     }
    }
    return previous(...args);
   };
  },
  metadata:()=>({evidence_sha256:digest,events:structuredClone(events),acquisition_rewards_reapplied:false,training_label_allowed:false})
 };
}
