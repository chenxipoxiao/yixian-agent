import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='b74720cb0b54d5a581558906037ebcd54f17148c252b09303e38563a88520d8a';
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const check=(ok,why)=>{if(!ok)throw new Error('engraving_wood_identity_v183r2:'+why);};
const cache=new Map();
function load(root){
 if(cache.has(root))return cache.get(root);
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-engraving-wood-identities-v183r2.json'));
 check(hash(bytes)===digest,'evidence_changed');const p=JSON.parse(bytes);
 for(const [name,h] of Object.entries(p.source_sha256))check(hash(fs.readFileSync(path.join(root,name)))===h,'source_changed:'+name);
 const cards=JSON.parse(fs.readFileSync(path.join(root,p.card_evidence)));
 for(const [name,h] of Object.entries(cards.source_sha256))check(hash(fs.readFileSync(path.join(root,name)))===h,'card_source_changed:'+name);
 const result={p,cards:cards.cards};cache.set(root,result);return result;
}
export function extendEngravingWoodIdentities(root,facts,swogi){
 const {p,cards}=load(root),candidate=structuredClone(facts.transform_cards);
 for(const a of p.aliases){
  const matches=cards.filter(c=>c.raw_id===a.raw_id);
  check(matches.length===1,'unique_identity:'+a.raw_id);const c=matches[0],cfg=c.config;
  check(c.runtime_id===a.runtime_id&&cfg.id===a.raw_id,'source_identity:'+a.raw_id);
  check(cfg.hidden===a.hidden&&cfg.noUpgrade===a.no_upgrade&&cfg.rarity===a.rarity,'source_classification:'+a.raw_id);
  check(a.upgrade_raw_id===(cfg.noUpgrade?null:a.raw_id+10000)&&a.downgrade_raw_id===(cfg.rarity>=1?a.raw_id-10000:null),'source_grade_links:'+a.raw_id);
  check(!Object.hasOwn(candidate,a.raw_id),'existing_identity:'+a.raw_id);
  check(!Object.values(candidate).some(c=>c.runtime_id===a.runtime_id),'runtime_alias_collision:'+a.raw_id);
  check(typeof swogi[a.runtime_id]?.card_actions==='function','card_body_required:'+a.raw_id);
  const {raw_id,...metadata}=a;candidate[raw_id]=metadata;
 }
 for(const a of p.aliases)for(const key of ['upgrade_raw_id','downgrade_raw_id']){
  if(a[key]===null)continue;
  check(candidate[a[key]]&&typeof swogi[candidate[a[key]].runtime_id]?.card_actions==='function','grade_closure:'+a.raw_id);
 }
 facts.transform_cards=candidate;
 return {evidence_sha256:digest,raw_ids:p.aliases.map(a=>a.raw_id)};
}
