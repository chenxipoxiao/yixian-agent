import {installMixedParameters as previousInstall} from './current_mixed_parameters_v98.mjs';
// New exact-record bindings; the existing reader implementations stay frozen.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {createMixedQueue} from './current_mixed_queue_v98.mjs';
const digest='5a80a728fe11e2d9402af54e4c7ab810558f76de56891031dbed51fd048d68f6',installed=new WeakSet();
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const check=(ok,why)=>{if(!ok)throw new Error('mixed_parameters_unresolved:'+why);};
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const canonical=x=>Array.isArray(x)?'['+x.map(canonical).join(',')+']':object(x)?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}':JSON.stringify(x);
export function installMixedParameters(root,swogi,game,value,order,battle){
 if(value===undefined)return null;
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-cloud-parameters-v100.json'));
 check(hash(bytes)===digest,'evidence_changed');const facts=JSON.parse(bytes);
 if(!Object.hasOwn(facts.admitted_records,value?.record_binding?.record_id))return previousInstall(root,swogi,game,value,order,battle);
 check(!installed.has(game),'already_installed');
 check(object(value)&&Object.keys(value).sort().join(',')==='battle_sha256,record_binding,stream','explicit_bound_stream_required');
 check(object(battle)&&battle.first_player===order[0]&&!Object.keys(battle).some(k=>k!=='mixed_parameters'&&(k.includes('parameter')||k==='falling_paper')),'exclusive_bound_initiative_required');
 const plain=Object.fromEntries(Object.entries(battle).filter(([k])=>k!=='mixed_parameters'));
 check(hash(canonical(plain))===value.battle_sha256,'compiled_battle_binding_mismatch');
 for(const [p,h] of Object.entries(facts.source_sha256))check(hash(fs.readFileSync(path.join(root,p)))===h,'source_changed:'+p);
 const expected=facts.admitted_records[value.record_binding?.record_id];
 check(expected!==undefined&&canonical(expected.binding)===canonical(value.record_binding),'unaudited_record_binding');
 check(expected.compiled_battle_sha256===value.battle_sha256,'unaudited_compiled_start');
 check(hash(canonical(value.stream))===expected.binding.stream_sha256,'recorded_stream_mismatch');
 const queue=createMixedQueue(swogi,game,value.stream,order,facts);
 installed.add(game);
 return {version:100,verifyTerminal:()=>queue.verifyTerminal(),metadata:()=>({binding_evidence_sha256:digest,
  reader_mode:expected.mode,...queue.metadata(),record_binding:structuredClone(value.record_binding),
  policy_observation_allowed:false,training_label_allowed:false,counterfactual_reuse_allowed:false})};
}
