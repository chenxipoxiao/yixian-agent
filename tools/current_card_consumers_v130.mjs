// New exact-record bindings; the existing reader implementations stay frozen.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {installReplayParameters as previousInstall} from './current_mirror_parameters_v129r3.mjs';
import {createNestedCardQueue} from './current_nested_card_parameters_v89.mjs';
import {createFlagMixedQueue} from './current_flag_mixed_queue_v130.mjs';
const digest='86f5d71698bde147f85bcb519bfa8f3b7a992481537dbd72996cc9c900f89cb5',installed=new WeakSet();
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const check=(ok,why)=>{if(!ok)throw new Error('replay_parameters_unresolved:'+why);};
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const canonical=x=>Array.isArray(x)?'['+x.map(canonical).join(',')+']':object(x)?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}':JSON.stringify(x);
export function installReplayParameters(root,swogi,game,value,order,battle){
 if(value===undefined)return null;
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-mirror-card-consumers-v130.json'));
 check(hash(bytes)===digest,'evidence_changed');const facts=JSON.parse(bytes);
 if(!Object.hasOwn(facts.random_bindings,value?.record_binding?.record_id))return previousInstall(root,swogi,game,value,order,battle);
 check(!installed.has(game),'already_installed');
 check(object(value)&&Object.keys(value).sort().join(',')==='battle_sha256,record_binding,stream','explicit_bound_stream_required');
 check(object(battle)&&battle.first_player===order[0]&&!Object.keys(battle).some(k=>k!=='replay_parameters'&&(k.includes('parameter')||k==='falling_paper')),'exclusive_bound_initiative_required');
 const plain=Object.fromEntries(Object.entries(battle).filter(([k])=>k!=='replay_parameters'));
 check(hash(canonical(plain))===value.battle_sha256,'compiled_battle_binding_mismatch');
 for(const [p,h] of Object.entries(facts.source_sha256))check(hash(fs.readFileSync(path.join(root,p)))===h,'source_changed:'+p);
 const expected=facts.random_bindings[value.record_binding?.record_id];
 check(expected!==undefined&&canonical(expected.binding)===canonical(value.record_binding),'unaudited_record_binding');
 check(expected.compiled_battle_sha256===value.battle_sha256,'unaudited_compiled_start');
 check(hash(canonical(value.stream))===expected.binding.stream_sha256,'recorded_stream_mismatch');
 check(['nested_identity','flag_selected'].includes(expected.mode),'unknown_reader_mode');
 const queue=expected.mode==='nested_identity'?createNestedCardQueue(swogi,game,value.stream,order,facts.nested_reader):createFlagMixedQueue(swogi,game,value.stream,order,facts.mixed_reader,facts.flag_reader,battle.element_flag?.hands);
 installed.add(game);
 return {version:130,verifyTerminal:()=>queue.verifyTerminal(),metadata:()=>({binding_evidence_sha256:digest,
  ...queue.metadata(),reader_mode:expected.mode,record_binding:structuredClone(value.record_binding),
  policy_observation_allowed:false,training_label_allowed:false,counterfactual_reuse_allowed:false})};
}
