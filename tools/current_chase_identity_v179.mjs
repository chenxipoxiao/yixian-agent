// Exact flag identities layered on the unchanged v176 extension.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {extendChaseIdentities as previous} from './current_chase_identity_v176.mjs';
const evidenceSha='9b3a3574a94516e989318a28d8daf7625657fec37e7ec8ecd8a6be1f3ad87be4';
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const check=(v,m)=>{if(!v)throw new Error('chase_identity_v179:'+m);};
export function extendChaseIdentities(root,facts,swogi) {
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-flag-chase-identity-v179.json'));
 check(hash(bytes)===evidenceSha,'evidence_changed');
 const proof=JSON.parse(bytes);
 for(const [p,h] of Object.entries(proof.source_sha256))check(hash(fs.readFileSync(path.join(root,p)))===h,'source_changed:'+p);
 const raw=fs.readFileSync(path.join(root,proof.card_evidence));
 check(hash(raw)===proof.card_evidence_sha256,'card_evidence_changed');
 const cards=JSON.parse(raw).cards;
 // Even the previous extension is staged so an invalid new identity is atomic.
 const candidate=structuredClone(facts),old=previous(root,candidate,swogi);
 for(const a of proof.aliases){
  const selected=cards.filter(c=>c.raw_id===a.raw_id);check(selected.length===1,'unique_card_required:'+a.raw_id);
  const card=selected[0],cfg=card.config,m=candidate.metadata[a.raw_id];
  check(cfg.id===a.raw_id&&card.runtime_id===a.runtime_id,'source_identity_mismatch:'+a.raw_id);
  check(m&&Object.keys(m).length===Object.keys(a.expected_metadata).length&&
    Object.entries(a.expected_metadata).every(([k,v])=>m[k]===v),'prior_metadata_mismatch:'+a.raw_id);
  check(m.runtime_id===null&&m.no_upgrade===cfg.noUpgrade&&m.hidden===cfg.hidden&&m.rarity===cfg.rarity&&
    m.name_has_thunder===cfg.name.includes('雷')&&m.desc_has_chase===cfg.desc.includes('再次行动'),'classification_mismatch:'+a.raw_id);
  check(typeof swogi[a.runtime_id]?.card_actions==='function','card_body_required:'+a.raw_id);
  candidate.metadata[a.raw_id]={...m,runtime_id:a.runtime_id};
 }
 for(const [raw,target] of Object.entries(proof.grade_closure)){
  const m=candidate.metadata[raw];
  if(target===null){check(m.no_upgrade===true,'last_grade_must_not_upgrade:'+raw);continue;}
  check(!m.no_upgrade&&Number(raw)+10000===target&&typeof swogi[candidate.metadata[target]?.runtime_id]?.card_actions==='function','upgrade_target_required:'+raw);
 }
 facts.metadata=candidate.metadata;
 return {...old,added_raw_ids:proof.aliases.map(a=>a.raw_id),added_evidence_sha256:evidenceSha};
}
