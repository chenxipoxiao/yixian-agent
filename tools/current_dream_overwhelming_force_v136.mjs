import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const digest='821f99435c29f231c0f30add989a00a47aca7ac171da50ab568457c7d9a557f5';
const cache=new Map(), registered=new WeakSet(), installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('dream_force_v136:'+why);};
const int32=n=>Number.isSafeInteger(n)&&n>=-2147483648&&n<=2147483647;
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
export function dreamForceFacts(root){
  if(cache.has(root))return cache.get(root);
  const bytes=fs.readFileSync(path.join(root,'data/inspection/current-dream-overwhelming-force-v136.json'));
  check(hash(bytes)===digest,'evidence_changed');
  const facts=JSON.parse(bytes);
  for(const [name,expected] of Object.entries(facts.source_sha256))
    check(hash(fs.readFileSync(path.join(root,name)))===expected,'source_changed:'+name);
  check(facts.cards.length===5,'five_realms_required');
  cache.set(root,facts);return facts;
}
export function registerDreamForce(root,swogi){
  check(!registered.has(swogi),'already_registered');
  for(const card of dreamForceFacts(root).cards){
    const prior=swogi[card.runtime_id],c=card.config;
    check(prior&&typeof prior.card_actions==='function'&&prior.qi_cost===0&&
      (prior.hp_cost??0)===0&&prior.is_add_physique,'native_metadata');
    check(c.level===card.realm&&c.rarity===0&&c.noUpgrade===true&&c.anima===0&&c.hpCost===0,'config_identity');
    swogi[card.runtime_id]=Object.freeze({...prior,
      card_actions:game=>game.executeCurrentDreamForce(card.runtime_id)});
  }
  registered.add(swogi);
}
const snap=p=>Object.fromEntries(['qi','force','agility','physique','hp','max_hp'].map(k=>[k,p[k]]));
export function installDreamForce(root,game,swogi,order=[0,1]){
  check(!installed.has(game),'already_installed');
  check(order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'player_order');
  const cards=new Map(dreamForceFacts(root).cards.map(c=>[c.runtime_id,c]));
  const indexes=new Map(game.players.map((p,i)=>[p,order[i]])),events=[];
  game.executeCurrentDreamForce=function(id){
    const p=this.players[0],card=cards.get(id);
    check(card&&p.currently_triggering_card_id===id&&swogi[id],'card_identity');
    // Client caches both values before the realm branch and agility callbacks.
    const force=p.force,qi=p.qi,params=card.config.otherParams;
    check(int32(force)&&int32(qi),'unknown_force_or_qi');
    const e={kind:'card_body',raw_card_id:card.raw_id,runtime_id:id,realm:card.realm,
      player_index:indexes.get(p),trigger_depth:p.trigger_depth,captured_force:force,captured_qi:qi,before:snap(p)};
    events.push(e);
    if(card.realm<=3){
      e.condition_met=force>0||qi>0;
      if(e.condition_met){this.physique(params[0]);this.heal(params[1]);}
    }else{
      const body=force*params[1],hp=force*params[2];
      if(force>0)check(int32(body)&&int32(hp),'conversion_overflow');
      this.add_c_of_x(params[3],'agility');
      e.condition_met=force>0;
      if(e.condition_met){
        this.reduce_c_of_x(force,'force');
        this.physique(body);
        this.heal(hp);
      }
    }
    e.after=snap(p);
  };
  installed.add(game);
  return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),
    recorded_action_log:false,training_label_allowed:false}:null};
}
