import {installPaperMixedParameters as previousInstall} from './current_paper_mixed_parameters_v101.mjs';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {createFlagPaperMixedQueue} from './current_flag_paper_queue_v102.mjs';
const digest='1486e926ce04d9d0ff241da40f664b17f803beaf53ea7629fd88acb49ed7d411',installed=new WeakSet();
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const check=(ok,why)=>{if(!ok)throw new Error('flag_paper_parameters_unresolved:'+why);};
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const canonical=x=>Array.isArray(x)?'['+x.map(canonical).join(',')+']':object(x)?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}':JSON.stringify(x);
export function installPaperMixedParameters(root,swogi,game,value,order,battle){
 if(value===undefined)return null;
 const routeBytes=fs.readFileSync(path.join(root,'data/inspection/current-flag-paper-parameters-v102.json'));
 check(hash(routeBytes)===digest,'evidence_changed');
 if(!Object.hasOwn(JSON.parse(routeBytes).admitted_records,value?.record_binding?.record_id))return previousInstall(root,swogi,game,value,order,battle);
 check(!installed.has(game),'already_installed');
 check(object(value)&&Object.keys(value).sort().join(',')==='battle_sha256,owners,record_binding,stream','explicit_bound_stream_required');
 check(object(battle)&&battle.first_player===order[0]&&!Object.keys(battle).some(k=>k!=='paper_mixed_parameters'&&(k.includes('parameter')||k==='falling_paper')),'exclusive_bound_initiative_required');
 const plain=Object.fromEntries(Object.entries(battle).filter(([k])=>k!=='paper_mixed_parameters'));
 check(hash(canonical(plain))===value.battle_sha256,'compiled_battle_binding_mismatch');
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-flag-paper-parameters-v102.json'));
 check(hash(bytes)===digest,'evidence_changed');const facts=JSON.parse(bytes);
 for(const [p,h] of Object.entries(facts.source_sha256))check(hash(fs.readFileSync(path.join(root,p)))===h,'source_changed:'+p);
 const expected=facts.admitted_records[value.record_binding?.record_id];
 check(expected!==undefined&&canonical(expected.binding)===canonical(value.record_binding),'unaudited_record_binding');
 check(expected.compiled_battle_sha256===value.battle_sha256,'unaudited_compiled_start');
 check(canonical(expected.owners)===canonical(value.owners),'opening_owners_mismatch');
 check(hash(canonical(value.stream))===expected.binding.stream_sha256,'recorded_stream_mismatch');
 const flagFacts=JSON.parse(fs.readFileSync(path.join(root,'data/inspection/current-element-flag-v62r2.json')));
 const queue=createFlagPaperMixedQueue(swogi,game,value.stream,order,facts,value.owners,battle.element_flag?.hands,flagFacts);
 installed.add(game);
 return {version:102,installReaders:()=>queue.installReaders(),verifyTerminal:()=>queue.verifyTerminal(),metadata:()=>({binding_evidence_sha256:digest,
  ...queue.metadata(),record_binding:structuredClone(value.record_binding),
  policy_observation_allowed:false,training_label_allowed:false,counterfactual_reuse_allowed:false})};
}
