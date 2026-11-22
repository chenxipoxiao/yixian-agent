// Versioned current character-card values; reference sources stay frozen.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='439186e91131587b57a754069c06e58c6f28d6ab0ffd23ba6517a8dd81fec9af',cache=new Map(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('unceasing_v94:'+why);};
export function unceasingFacts(root){
 if(cache.has(root))return cache.get(root);
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-unceasing-v94.json'));
 check(crypto.createHash('sha256').update(bytes).digest('hex')===digest,'evidence_changed');
 const facts=JSON.parse(bytes);
 for(const [p,h] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,facts);return facts;
}
export function registerUnceasing(root,swogi){
 check(!installed.has(swogi),'already_registered');
 for(const c of unceasingFacts(root).cards){
  const prior=swogi[c.runtime_id];check(prior&&typeof prior.card_actions==='function','missing_native_card');
  // The current client reads attack once, gains physique, then heals separately.
  swogi[c.runtime_id]={...prior,card_actions:g=>{
   g.atk(c.config.attack);
   g.add_c_of_x(c.config.physique,'physique');
   g.increase_idx_hp(0,c.config.otherParams[0]);
  }};
 }
 installed.add(swogi);
}
