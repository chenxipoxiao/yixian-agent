// Versioned current character-card values; reference sources stay frozen.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='2376d52efa55e907d15db8af168e90f3f98c41b575766ddd9b43b1db8c5a41da',cache=new Map(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('bow_raven_v96:'+why);};
export function bow_ravenFacts(root){
 if(cache.has(root))return cache.get(root);
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-bow-raven-v96.json'));
 check(crypto.createHash('sha256').update(bytes).digest('hex')===digest,'evidence_changed');
 const facts=JSON.parse(bytes);
 for(const [p,h] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,facts);return facts;
}
export function registerBowRaven(root,swogi){
 check(!installed.has(swogi),'already_registered');
 for(const c of bow_ravenFacts(root).cards){
  const prior=swogi[c.runtime_id];check(prior&&typeof prior.card_actions==='function','missing_native_card');
  swogi[c.runtime_id]={...prior,card_actions:g=>{
   const me=g.players[0],params=c.config.otherParams;
   if(c.kind==='phantom_raven'){
    g.atk(c.config.attack);
    if(me.qi>0){const amount=me.qi*params[0];g.increase_idx_def(0,c.config.rarity===2?amount:Math.min(amount,params[2]));}
    if(g.spirit_sword_deck_count(params[1])>=params[1])g.chase();
   }else{
    if(!me.can_post_action[me.currently_playing_card_idx]){
     g.add_c_of_x(params[0],'max_hp');g.increase_idx_hp(0,params[0]);
    }
    if(me.hp_gained>0&&g.if_post_action())g.atk(c.config.attack+Math.floor(me.hp_gained/params[1]));
    if(g.if_c_pct(params[2]))g.chase();
   }
  }};
 }
 installed.add(swogi);
}
