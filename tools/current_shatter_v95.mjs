// Versioned current character-card values; reference sources stay frozen.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='e3e0c5df2f32839601bd9a91c37592a83617470b3ac30cbcf5a3ebe5daa939c3',cache=new Map(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('shatter_v95:'+why);};
export function shatterFacts(root){
 if(cache.has(root))return cache.get(root);
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-shatter-v95.json'));
 check(crypto.createHash('sha256').update(bytes).digest('hex')===digest,'evidence_changed');
 const facts=JSON.parse(bytes);
 for(const [p,h] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,facts);return facts;
}
export function registerShatter(root,swogi){
 check(!installed.has(swogi),'already_registered');
 for(const c of shatterFacts(root).cards){
  const prior=swogi[c.runtime_id];check(prior&&typeof prior.card_actions==='function','missing_native_card');
  // Client340 applies to this attack sequence;735 is granted after all hits.
  swogi[c.runtime_id]={...prior,card_actions:g=>{
   for(let i=0;i<c.config.attackCount;i++)g.atk(c.config.attack,false,true);
   g.add_c_of_x(1,'crash_fist_shatter_stacks');
  }};
 }
 installed.add(swogi);
}
