// Current client card bodies; keep the pinned reference files and metadata intact.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='db9c8d5fe6a0317feeb0cd0204d472b45761593dee3f8ec445a130ccd95f44d3',cache=new Map(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('native_card_values_v85:'+why);};
export function nativeCardValuesFacts(root){
 if(cache.has(root))return cache.get(root);
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-native-card-values-v85.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');
 const facts=JSON.parse(raw);
 for(const [name,h] of Object.entries(facts.source_sha256))
  check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,name))).digest('hex')===h,'source_changed:'+name);
 cache.set(root,facts);return facts;
}
export function registerNativeCardValues(root,swogi){
 check(!installed.has(swogi),'already_registered');
 const facts=nativeCardValuesFacts(root);
 for(const c of facts.cards){
  const old=swogi[c.runtime_id];check(old&&typeof old.card_actions==='function','missing_native_card');
  // Replace only the body. Costs, category flags, identity and transform lookup
  // remain shared with every existing scheduler and temporary-card mechanism.
  swogi[c.runtime_id]={...old,card_actions:g=>{
   if(c.family==='axe'){
    for(let i=0;i<c.config.attackCount;i++)g.atk(c.config.attack);
    g.add_enemy_c_of_x(c.config.otherParams[1],'metal_spirit_chokehold_stacks');
    if(g.if_injured())g.add_enemy_c_of_x(c.config.otherParams[0],'pangu_axe_stacks');
   }else if(c.family==='weaken'){
    g.add_enemy_c_of_x(c.config.otherParams[0],'weaken');g.consumption();
   }else if(c.family==='dragon_cloud'){
    g.continuous();
    g.add_c_of_x(1,'dragon_devours_clouds_stacks');
    g.add_c_of_x(c.config.otherParams[0],'unrestrained_sword_count');
   }else throw new Error('native_card_values_v85:unknown_family');
  }};
 }
 installed.add(swogi);
 return {evidence_sha256:digest,raw_card_ids:facts.cards.map(c=>c.raw_id)};
}
