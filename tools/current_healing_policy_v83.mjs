// Fixed local client OpenConfig74. This is not a missing-field default.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
export function requireHealingPolicy(root) {
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-nonpositive-healing-v83.json'));
 const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
 if(hash(raw)!=='dba6ecef00b482e5368b02ec2e4320a68d31eea0306cebf2004d9f93370670b4')throw new Error('healing_v83:evidence_changed');
 const facts=JSON.parse(raw);
 if(facts.feature.id!==74||facts.feature.envs.length!==4||facts.feature.envs.some(v=>v!==true))
  throw new Error('healing_v83:explicit_enabled_feature_required');
 for(const [p,h] of Object.entries(facts.source_sha256))
  if(hash(fs.readFileSync(path.join(root,p)))!==h)throw new Error('healing_v83:source_changed:'+p);
 return facts;
}
