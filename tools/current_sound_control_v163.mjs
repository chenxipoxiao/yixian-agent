import {dreamFormationFacts} from './current_dream_formations_v163.mjs';
// Current preparation toggles and owner-ordered sound effects. No outcome inputs.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='3ac8d98433a3186bf86df7dcc7f9e7337ea7b418639093bfa1c6aec7d8549001',installed=new WeakSet();
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const check=(v,m)=>{if(!v)throw new Error('sound_control_unresolved:'+m);};
export function createSoundControl(root,game,swogi,value,order=[0,1]) {
 if(value===undefined)return null;
 check(object(value)&&Object.keys(value).length===2&&Array.isArray(value.players)&&value.players.length===2
  &&value.players.every(a=>Array.isArray(a)&&new Set(a.map(e=>e?.strategy_id)).size===a.length
   &&a.every(e=>object(e)&&Object.keys(e).length===2&&[1003,1005,1007].includes(e.strategy_id)&&typeof e.enabled==='boolean')),
  'explicit_ownership_and_switch_required');
 check(value.players.some(a=>a.length),'owner_required');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 check(!installed.has(game),'already_installed');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-sound-control-v52.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');
 const facts=JSON.parse(raw);
 for(const [p,h] of Object.entries(facts.source_sha256))
  check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 check(Array.isArray(value.raw_boards)&&value.raw_boards.length===2,'explicit_raw_boards_required');
 const extraRaw=fs.readFileSync(path.join(root,'data/inspection/current-twin-dependencies-v54.json'));
 if(crypto.createHash('sha256').update(extraRaw).digest('hex')!=='239aa5c70297af9209d66c881c03bc1815e09203d0e23dbe8985f27f2f9f9038')throw new Error('twin_dependencies_unresolved:identity_evidence_changed');
 for(const [id,c] of Object.entries(JSON.parse(extraRaw).extra_metadata)){if(Object.hasOwn(facts.metadata,id))throw new Error('twin_dependencies_unresolved:duplicate_identity');facts.metadata[id]=c;}
 // Versioned identity extension: old facts remain frozen and unknown IDs still fail.
 const identityRaw=fs.readFileSync(path.join(root,'data/inspection/current-sound-identity-v138.json'));
 const identityDigest='51222f2fa0445ec54c4e09f9d131dd1d687e12d682d311d5c0e93870507b615f';
 check(crypto.createHash('sha256').update(identityRaw).digest('hex')===identityDigest,'identity_evidence_changed');
 const identityFacts=JSON.parse(identityRaw);
 for(const [name,expected] of Object.entries(identityFacts.source_sha256))
  check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,name))).digest('hex')===expected,'identity_source_changed:'+name);
 for(const [id,c] of Object.entries(identityFacts.extra_metadata)) {
  check(!Object.hasOwn(facts.metadata,id),'duplicate_extra_identity');
  check(!Object.values(facts.metadata).some(old=>old.runtime_id===c.runtime_id),'extra_runtime_collision');
  facts.metadata[id]=c;
 }
 const usesExtraIdentity=value.players.some(a=>a.some(e=>e.strategy_id===1007&&e.enabled))
  &&value.raw_boards.some(a=>Array.isArray(a)&&a.some(id=>Object.hasOwn(identityFacts.extra_metadata,id)));
 // Exact Cloud Shadow identities; all old metadata and card bodies stay frozen.
 const cloudRaw=fs.readFileSync(path.join(root,'data/inspection/current-sound-identity-v162.json'));
 const cloudDigest='6e77770665e17f68ea6b8c13a31cb818c9e024e468a10fbc5f998bae1ec1cd52';
 check(crypto.createHash('sha256').update(cloudRaw).digest('hex')===cloudDigest,'cloud_identity_evidence_changed');
 const cloudFacts=JSON.parse(cloudRaw);
 for(const [name,expected] of Object.entries(cloudFacts.source_sha256))
  check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,name))).digest('hex')===expected,'cloud_identity_source_changed:'+name);
 for(const [id,c] of Object.entries(cloudFacts.extra_metadata)) {
  check(!Object.hasOwn(facts.metadata,id),'duplicate_cloud_identity');
  check(!Object.values(facts.metadata).some(old=>old.runtime_id===c.runtime_id),'cloud_runtime_collision');
  facts.metadata[id]=c;
 }
 const usesCloudIdentity=value.players.some(a=>a.some(e=>e.strategy_id===1007&&e.enabled))
  &&value.raw_boards.some(a=>Array.isArray(a)&&a.some(id=>Object.hasOwn(cloudFacts.extra_metadata,id)));
 for(const c of dreamFormationFacts(root).cards){
  check(!Object.hasOwn(facts.metadata,c.raw_id),'duplicate_dream_formation_identity');
  check(!Object.values(facts.metadata).some(x=>x.runtime_id===c.runtime_id),'dream_formation_runtime_collision');
  facts.metadata[c.raw_id]={runtime_id:c.runtime_id,hidden:true,no_upgrade:true,rarity:0,upgrade_raw_id:c.raw_id+10000,downgrade_raw_id:c.raw_id-10000};
 }
 const states=new Map(game.players.map((p,i)=>[p,{index:order[i],entries:new Map(value.players[order[i]].map(e=>[e.strategy_id,e])),opened:new Set()}]));
 const events=[],boundaries=new Set(),identities=new Map(),byRuntime=new Map();
 const enabledUpgrade=value.players.some(a=>a.some(e=>e.strategy_id===1007&&e.enabled));
 if(enabledUpgrade) {
  for(const [raw,c] of Object.entries(facts.metadata)) {
   const ids=byRuntime.get(c.runtime_id)??[];ids.push(Number(raw));byRuntime.set(c.runtime_id,ids);
  }
  game.players.forEach((p,i)=>{
   const board=value.raw_boards[order[i]];
   check(Array.isArray(board)&&board.length===p.cards.length&&board.every((id,j)=>Number.isSafeInteger(id)&&facts.metadata[id]?.runtime_id===p.cards[j]),'raw_board_mismatch');
   identities.set(p,board.map((raw,j)=>({raw,runtime:p.cards[j]})));
  });
  // Install before the engraving wrapper: first-use engraving, then281, then560.
  game.do_finishing_touch=function(idx) {
   const p=this.players[0];
   if(p.finishing_touch_stacks<=0)return;
   check(Number.isInteger(idx)&&idx>=0&&idx<p.cards.length,'invalid_upgrade_slot');
   const entry=identities.get(p)[idx],runtime=p.cards[idx];
   if(entry.runtime!==runtime) {
    const ids=byRuntime.get(runtime);check(ids?.length===1,'ambiguous_or_unknown_runtime:'+runtime);
    entry.raw=ids[0];entry.runtime=runtime;
   }
   const c=facts.metadata[entry.raw];
   // CanUpgrade only checks noUpgrade; hidden is NOT an additional condition.
   if(c.no_upgrade)return;
   const target=facts.metadata[c.upgrade_raw_id];
   check(target&&typeof swogi[target.runtime_id]?.card_actions==='function','upgrade_target_unimplemented:'+c.upgrade_raw_id);
   const from=entry.raw;
   this.reduce_idx_x_by_c(0,'finishing_touch_stacks',1);
   p.cards[idx]=target.runtime_id;entry.raw=c.upgrade_raw_id;entry.runtime=target.runtime_id;
   events.push({phase:'before_card_body_281',player_index:states.get(p).index,slot:idx,from_raw:from,to_raw:entry.raw,remaining:p.finishing_touch_stacks});
  };
 }
 if(enabledUpgrade) {
  const trigger=game.trigger_card.bind(game);
  game.trigger_card=function(cardId,idx) {
   const p=this.players[0];
   check(!(p.trigger_depth>=1&&p.finishing_touch_stacks>0),'temporary_upgrade_identity_required');
   return trigger(cardId,idx);
  };
 }
 const state=p=>({hp:p.hp,max_hp:p.max_hp,finishing_touch:p.finishing_touch_stacks,predicament:p.predicament_for_immortals_stacks});
 installed.add(game);
 return {
  installBoundary(id) {
   check([1003,1005,1007].includes(id)&&!boundaries.has(id),'duplicate_or_unknown_boundary');boundaries.add(id);
   const plants=game.do_plant_start_permanent_buffs.bind(game);
   game.do_plant_start_permanent_buffs=function(...args) {
    check(boundaries.size===3,'incomplete_boundary_installation');
    const s=states.get(this.players[0]),e=s.entries.get(id);
    if(e&&!s.opened.has(id)) {
     s.opened.add(id);
     const event={strategy_id:id,phase:'owner_ordered_opening',player_index:s.index,enabled:e.enabled,
      target_order:this.players.map(p=>states.get(p).index),before:this.players.map(state)};events.push(event);
     if(e.enabled) {
      if(id===1003) {
       check(this.players.every(p=>Number.isSafeInteger(p.hp)&&p.hp>=0&&p.hp*15<=2147483647),'invalid_healing_basis');
       // Both amounts are captured before either target's callbacks run.
       const amounts=this.players.map(p=>Math.trunc(p.hp*15/100));event.amounts=amounts;
       for(let i=0;i<2;i++){this.increase_idx_max_hp(i,amounts[i]);this.increase_idx_hp(i,amounts[i]);}
      } else for(let i=0;i<2;i++)this.increase_idx_x_by_c(i,id===1005?'predicament_for_immortals_stacks':'finishing_touch_stacks',1);
     }
     event.after=this.players.map(state);check(this.players.every(p=>p.hp>0),'opening_terminal_pending');
    }
    return plants(...args);
   };
  },
  metadata:()=>({evidence_sha256:digest,...(usesCloudIdentity?{cloud_shadow_identity_sha256:cloudDigest}:{}),...(usesExtraIdentity?{identity_extension_sha256:identityDigest}:{}),events:structuredClone(events),training_label_allowed:false,
   remaining:[...states].map(([p,s])=>({player_index:s.index,...state(p)})).sort((a,b)=>a.player_index-b.player_index)})
 };
}
