// Exact identity extension; no card effects or source defaults are changed.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const evidenceSha='1e9c435feece98d8f34645d57148c585cfe87a0a79ffa12dea7bf88d6e2eecf7';
const check=(v,m)=>{if(!v)throw new Error('chase_identity_v176:'+m);};
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
export function extendChaseIdentities(root,facts,swogi) {
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-chase-identity-v176.json'));
 check(hash(bytes)===evidenceSha,'evidence_changed');
 const proof=JSON.parse(bytes),cache=new Map();
 for(const [p,h] of Object.entries(proof.source_sha256))check(hash(fs.readFileSync(path.join(root,p)))===h,'source_changed:'+p);
 for(const [p,h] of Object.entries(proof.card_evidence_sha256)){
  const raw=fs.readFileSync(path.join(root,p));check(hash(raw)===h,'card_evidence_changed:'+p);
  const d=JSON.parse(raw);cache.set(p,d);
  for(const [src,expected] of Object.entries(d.source_sha256))check(hash(fs.readFileSync(path.join(root,src)))===expected,'card_source_changed:'+src);
 }
 const patches=[];
 for(const a of proof.aliases){
  const candidates=cache.get(a.card_evidence).cards.filter(c=>c.raw_id===a.raw_id);
  check(candidates.length===1,'unique_card_required:'+a.raw_id);
  const c=candidates[0],cfg=c.config,m=facts.metadata[a.raw_id];
  check(c.runtime_id===a.runtime_id&&cfg.id===a.raw_id,'source_identity_mismatch:'+a.raw_id);
  check(m&&Object.keys(m).length===Object.keys(a.expected_metadata).length&&
   Object.entries(a.expected_metadata).every(([k,v])=>m[k]===v),'prior_metadata_mismatch:'+a.raw_id);
  check(m.runtime_id===null&&m.no_upgrade===cfg.noUpgrade&&m.hidden===cfg.hidden&&m.rarity===cfg.rarity&&
   m.name_has_thunder===cfg.name.includes('雷')&&m.desc_has_chase===cfg.desc.includes('再次行动'),'classification_mismatch:'+a.raw_id);
  check(typeof swogi[a.runtime_id]?.card_actions==='function','card_body_required:'+a.raw_id);
  patches.push([a.raw_id,{...m,runtime_id:a.runtime_id}]);
 }
 // Validate the entire extension before changing this private evidence copy.
 for(const [raw,m] of patches)facts.metadata[raw]=m;
 return {evidence_sha256:evidenceSha,raw_ids:proof.aliases.map(a=>a.raw_id)};
}
