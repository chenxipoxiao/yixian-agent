// One typed, record-bound GetNextParam consumer. No hand-count default.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='d5f8ff76183b4f499eb9e418b7106f892ed85aa1e314cf1e82c0c7204bacacff',installed=new WeakSet();
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const check=(ok,why)=>{if(!ok)throw new Error('cloud_parameter_unresolved:'+why);};
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const canonical=x=>Array.isArray(x)?'['+x.map(canonical).join(',')+']':object(x)?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}':JSON.stringify(x);
const snap=p=>({hp:p.hp,max_hp:p.max_hp,qi:p.qi,def:p.def,increase_atk:p.increase_atk});

export function installCloudParameter(root,swogi,game,value,order,battle) {
  if(value===undefined)return null;
  check(!installed.has(game),'already_installed');
  check(object(value)&&Object.keys(value).sort().join(',')==='battle_sha256,consumers,record_binding,stream','explicit_bound_stream_required');
  check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
  check(object(battle)&&battle.first_player===order[0]&&battle.falling_paper===undefined&&battle.typed_parameters===undefined,'exclusive_bound_initiative_required');
  const plain=Object.fromEntries(Object.entries(battle).filter(([k])=>k!=='cloud_sword_parameters'));
  check(hash(canonical(plain))===value.battle_sha256,'compiled_battle_binding_mismatch');
  const bytes=fs.readFileSync(path.join(root,'data/inspection/current-cloud-parameter-v81.json'));
  check(hash(bytes)===digest,'evidence_changed');const facts=JSON.parse(bytes);
  for(const [p,h] of Object.entries(facts.source_sha256))check(hash(fs.readFileSync(path.join(root,p)))===h,'source_changed:'+p);
  const admitted=Object.values(facts.admitted_records).find(e=>canonical(e.binding)===canonical(value.record_binding));
  check(admitted!==undefined&&battle.first_player===value.record_binding.first_player,'record_binding_mismatch');
  check(value.battle_sha256===admitted.compiled_battle_sha256,'unaudited_compiled_start');
  check(Array.isArray(value.stream)&&value.stream.length>0&&value.stream.length<=256&&value.stream.every(x=>Number.isSafeInteger(x)&&x>=0&&x<=2147483647),'invalid_complete_stream');
  check(hash(canonical(value.stream))===value.record_binding.stream_sha256,'recorded_stream_mismatch');
  check(canonical(value.consumers)===canonical(admitted.consumers)&&value.consumers.length===value.stream.length,'consumer_manifest_mismatch');
  const cards=new Map(facts.cards.map(c=>[c.runtime_id,c]));
  const seats=new Map(game.players.map((p,i)=>[p,order[i]]));
  for(const p of game.players)if(p.cards.some(id=>cards.has(id))) {
    // An explicit null prevents anyone accidentally using native default17.
    p.cloud_sword_hand_count=null;
  }
  let cursor=0;const events=[];
  const noOther=()=>check(!game.used_randomness,'other_random_consumer');
  game.remnant_cloud_sky_sealing_sword_extra_atk=function(_ignoredDefault) {
    noOther();const p=this.players[0],id=p.currently_triggering_card_id;
    const card=cards.get(id),expected=value.consumers[cursor];
    check(card!==undefined,'unknown_cloud_card');
    check(expected!==undefined,'parameter_underflow');
    check(expected.player_index===seats.get(p)&&expected.runtime_id===id&&expected.raw_id===card.raw_id&&expected.slot===p.currently_triggering_card_idx,'consumer_order_or_identity_mismatch');
    const extra=value.stream[cursor];check(card.attack+extra<=2147483647,'attack_overflow');
    events.push({kind:'cloud_sword_extra_attack',queue_index:cursor++,player_index:seats.get(p),
      raw_card_id:card.raw_id,runtime_card_id:id,slot:p.currently_triggering_card_idx,
      value:extra,base_attack:card.attack,before:snap(p),target_before:snap(this.players[1])});
    return extra;
  };
  for(const method of facts.blocked_random_entrypoints) {
    check(typeof game[method]==='function','missing_random_guard:'+method);
    game[method]=()=>{throw new Error('cloud_parameter_unresolved:unsupported_consumer:'+method);};
  }
  game.rng=()=>{throw new Error('cloud_parameter_unresolved:other_random_consumer');};
  installed.add(game);
  return {verifyTerminal:()=>{noOther();check(cursor===value.stream.length,'unused_parameters');},
    metadata:()=>({evidence_sha256:digest,record_conditioned:true,consumed:cursor,total_parameters:value.stream.length,
      events:structuredClone(events),hand_count_default_used:false,server_hand_classifier_recovered:false,
      other_rng_allowed:false,recorded_action_log:false,distribution_verified:false,
      counterfactual_reuse_allowed:false,training_label_allowed:false})};
}
