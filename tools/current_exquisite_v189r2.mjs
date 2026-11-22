const PROOF_HASH='cf2b7a22fad08cd6249c545fccf8010f063befe23071b58f0cb1e297b76bccec';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const cache=new Map(),registered=new WeakSet(),installed=new WeakSet();
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const check=(ok,why)=>{if(!ok)throw new Error('exquisite_v189:'+why);};
const bounded=n=>{check(Number.isSafeInteger(n)&&n>=0&&n<=2147483647,'integer_range');return n;};
export function facts189(root){
  if(cache.has(root))return cache.get(root);
  const bytes=fs.readFileSync(path.join(root,'data/inspection/current-exquisite-sword-v189r2.json'));
  check(hash(bytes)===PROOF_HASH,'evidence_changed');const f=JSON.parse(bytes);
  for(const [name,h] of Object.entries(f.source_sha256))check(hash(fs.readFileSync(path.join(root,name)))===h,'source_changed:'+name);
  cache.set(root,f);return f;
}
export function registerExquisite189(root,swogi){
  check(!registered.has(swogi),'already_registered');
  for(const c of facts189(root).cards){
    check(!Object.hasOwn(swogi,c.runtime_id),'alias_collision');
    const flags=Object.fromEntries(Object.keys(swogi['601011']).filter(k=>k.startsWith('is_')).map(k=>[k,false]));
    swogi[c.runtime_id]=Object.freeze({...swogi['601011'],...flags,name:'Current Exquisite Sword Formation',names:[c.config.name],
      marking:'sw',qi_cost:0,hp_cost:0,opening:undefined,is_add_qi:true,is_sword:true,is_sword_formation:true,
      card_actions:g=>g.executeExquisite189(c.runtime_id)});
  }
  registered.add(swogi);
}
const snap=p=>Object.fromEntries(['hp','max_hp','qi','def','next_turn_def'].map(k=>[k,p[k]]));
export function installExquisite189(root,game,swogi,order=[0,1]){
  check(!installed.has(game),'already_installed');const f=facts189(root),cards=new Map(f.cards.map(c=>[c.runtime_id,c]));
  const seats=new Map(game.players.map((p,i)=>[p,order[i]])),events=[];
  game.executeExquisite189=function(id){
    const p=this.players[0],c=cards.get(id);check(c&&p.currently_triggering_card_id===id,'card_identity');
    const event={kind:'card_body',raw_card_id:c.raw_id,player_index:seats.get(p),before:snap(p),opponent_before:snap(this.players[1])};
    events.push(event);
    this.increase_idx_qi(0,c.config.anima);
    const qi=bounded(p.qi);event.qi_snapshot=qi;
    this.deal_damage(bounded(qi*c.config.otherParams[0]));
    this.next_turn_def(bounded(qi*c.config.otherParams[1]));
    event.after=snap(p);event.opponent_after=snap(this.players[1]);
  };
  installed.add(game);
  return {metadata:()=>events.length?{evidence_sha256:PROOF_HASH,events:structuredClone(events),recorded_action_log:false,training_label_allowed:false}:null};
}
