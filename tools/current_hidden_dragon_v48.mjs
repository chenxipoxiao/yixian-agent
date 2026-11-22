// Base331 has its own Unrestrained Sword identity before any next-card buff.
// Preserve v11 card bodies and every scheduler/healing operation.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const PROOF_SHA='05ff62085bbdbe225c0049216df3cb0378c3e85eed7c7c2d73ddca607904407b';
const digest=raw=>crypto.createHash('sha256').update(raw).digest('hex');
export function registerHiddenDragonClassification(root,swogi) {
  const raw=fs.readFileSync(path.join(root,'data/inspection/current-hidden-dragon-v48.json'));
  if(digest(raw)!==PROOF_SHA)throw new Error('Hidden Dragon evidence changed');
  const facts=JSON.parse(raw);
  for(const [p,h] of Object.entries(facts.source_sha256)) {
    if(digest(fs.readFileSync(path.join(root,p)))!==h)throw new Error('Hidden Dragon source changed:'+p);
  }
  // Validate all three entries before replacing any of them.
  for(const {runtime_id:id} of facts.cards) {
    const old=swogi[id];
    if(!old || old.is_cloud_sword!==true || old.is_sword!==true ||
       old.is_unrestrained_sword!==false || typeof old.card_actions!=='function') {
      throw new Error('Unexpected Hidden Dragon registration:'+id);
    }
  }
  for(const {runtime_id:id} of facts.cards) {
    swogi[id]=Object.freeze({...swogi[id],is_unrestrained_sword:true});
  }
  return {evidence_sha256:PROOF_SHA,training_label_allowed:false};
}
