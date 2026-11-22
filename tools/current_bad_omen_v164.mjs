// Exact current-client Bad Omen bodies; previous runtime and reference files remain frozen.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='a035aeba5096e3d1eaa500e59d578556d26205cbc1cb273ef67b3ce19f0ac7a0',installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('bad_omen_v164:'+why);};
export function registerBadOmen(root,swogi){
 check(!installed.has(swogi),'already_registered');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-bad-omen-v164.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');
 const facts=JSON.parse(raw);
 for(const [p,h] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 for(const c of facts.cards){
  const p=swogi[c.runtime_id];check(p&&typeof p.card_actions==='function','missing_metadata');
  check(p.qi_cost===0&&(p.hp_cost??0)===0&&c.config.cardType===0,'unsupported_cost_or_type');
  const amount=c.config.otherParams[0];check(Number.isInteger(amount)&&amount>0,'invalid_count');
  swogi[c.runtime_id]=Object.freeze({...p,card_actions:g=>g.add_enemy_c_of_x(amount,'bad_omen_stacks')});
 }
 installed.add(swogi);
}
