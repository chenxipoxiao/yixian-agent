// New exact-record bindings; the existing reader implementations stay frozen.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {installReplayParameters as previousInstall} from './current_preparation_parameters_v106.mjs';
import {createProbabilityQueue} from './current_probability_parameters_v88.mjs';
const digest='39d54f78bc905d8de2045f2cb5142b0dbcf967313a68a3dc704adcd20210fed5',installed=new WeakSet();
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const check=(ok,why)=>{if(!ok)throw new Error('replay_parameters_unresolved:'+why);};
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const canonical=x=>Array.isArray(x)?'['+x.map(canonical).join(',')+']':object(x)?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}':JSON.stringify(x);
export function installReplayParameters(root,swogi,game,value,order,battle){
 if(value===undefined)return null;
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-capacity-parameters-v110.json'));
 check(hash(bytes)===digest,'evidence_changed');const facts=JSON.parse(bytes);
 if(!Object.hasOwn(facts.admitted_records,value?.record_binding?.record_id))return previousInstall(root,swogi,game,value,order,battle);
 check(!installed.has(game),'already_installed');
 check(object(value)&&Object.keys(value).sort().join(',')==='battle_sha256,record_binding,stream','explicit_bound_stream_required');
 check(object(battle)&&battle.first_player===order[0]&&!Object.keys(battle).some(k=>k!=='replay_parameters'&&(k.includes('parameter')||k==='falling_paper')),'exclusive_bound_initiative_required');
 const plain=Object.fromEntries(Object.entries(battle).filter(([k])=>k!=='replay_parameters'));
 check(hash(canonical(plain))===value.battle_sha256,'compiled_battle_binding_mismatch');
 for(const [p,h] of Object.entries(facts.source_sha256))check(hash(fs.readFileSync(path.join(root,p)))===h,'source_changed:'+p);
 const expected=facts.admitted_records[value.record_binding?.record_id];
 check(expected!==undefined&&canonical(expected.binding)===canonical(value.record_binding),'unaudited_record_binding');
 check(expected.compiled_battle_sha256===value.battle_sha256,'unaudited_compiled_start');
 check(hash(canonical(value.stream))===expected.binding.stream_sha256,'recorded_stream_mismatch');
 const reader=facts.readers[expected.mode];check(reader!==undefined,'unknown_reader_mode');
 const readerBytes=fs.readFileSync(path.join(root,reader.path));check(hash(readerBytes)===reader.sha256,'reader_changed');
 const readerFacts=JSON.parse(readerBytes);
 for(const [p,h] of Object.entries(readerFacts.source_sha256))check(hash(fs.readFileSync(path.join(root,p)))===h,'reader_source_changed:'+p);
 const factory=expected.mode==='probability'?createProbabilityQueue:null;
 check(factory!==null,'unknown_reader_mode');const queue=factory(swogi,game,value.stream,order,readerFacts);
 installed.add(game);
 return {version:110,verifyTerminal:()=>queue.verifyTerminal(),metadata:()=>({binding_evidence_sha256:digest,
  reader_mode:expected.mode,...queue.metadata(),record_binding:structuredClone(value.record_binding),
  policy_observation_allowed:false,training_label_allowed:false,counterfactual_reuse_allowed:false})};
}
