// Exact identities for already executable cards; no card effects are changed.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {extendChaseIdentities as previousChase} from './current_chase_identity_v179.mjs';
const evidenceSha='0e7d2fba68dfff90245d24a577fa79d1c7ef20e72f2401fe5900e689a36c368c',cache=new Map();
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const check=(v,m)=>{if(!v)throw new Error('season_card_identity_v183:'+m);};
function load(root){
 if(cache.has(root))return cache.get(root);
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-season-card-identities-v183.json'));
 check(hash(raw)===evidenceSha,'evidence_changed');
 const proof=JSON.parse(raw),cards=new Map();
 for(const [p,h] of Object.entries(proof.source_sha256))check(hash(fs.readFileSync(path.join(root,p)))===h,'source_changed:'+p);
 for(const [p,h] of Object.entries(proof.card_evidence_sha256)){
  const raw=fs.readFileSync(path.join(root,p));check(hash(raw)===h,'card_evidence_changed:'+p);
  const f=JSON.parse(raw);cards.set(p,f.cards);
  for(const [src,expected] of Object.entries(f.source_sha256))check(hash(fs.readFileSync(path.join(root,src)))===expected,'card_source_changed:'+src);
 }
 const result={proof,cards};cache.set(root,result);return result;
}
function cardFor(a,all,swogi){
 const matches=all.get(a.card_evidence).filter(c=>c.raw_id===a.raw_id);
 check(matches.length===1,'unique_source_identity:'+a.raw_id);
 const c=matches[0];check(c.runtime_id===a.runtime_id&&c.config.id===a.raw_id,'source_identity_mismatch:'+a.raw_id);
 check(typeof swogi[a.runtime_id]?.card_actions==='function','card_body_required:'+a.raw_id);
 return c;
}
export function extendSeasonIdentities(root,facts,swogi){
 const {proof,cards}=load(root),candidate=structuredClone(facts);
 for(const a of proof.season_aliases){
  const c=cardFor(a,cards,swogi),raw=candidate.raw_cards[a.raw_id];
  check(JSON.stringify(raw)===JSON.stringify(c.config),'raw_configuration_mismatch:'+a.raw_id);
  check(candidate.raw_to_runtime[a.raw_id]===undefined&&!candidate.runtime_cards[a.runtime_id],'existing_season_identity:'+a.raw_id);
  candidate.raw_to_runtime[a.raw_id]=a.runtime_id;
  candidate.runtime_cards[a.runtime_id]=[{...raw,raw_id:a.raw_id,base_id:a.base_id,upgrade_runtime:a.upgrade_runtime}];
 }
 for(const a of proof.season_aliases){
  if(a.upgrade_runtime===null){check(candidate.raw_cards[a.raw_id].noUpgrade,'last_grade_upgrade:'+a.raw_id);continue;}
  check(!candidate.raw_cards[a.raw_id].noUpgrade&&candidate.raw_to_runtime[a.raw_id+10000]===a.upgrade_runtime&&
   typeof swogi[a.upgrade_runtime]?.card_actions==='function','season_upgrade_closure:'+a.raw_id);
 }
 facts.raw_to_runtime=candidate.raw_to_runtime;facts.runtime_cards=candidate.runtime_cards;
 return {evidence_sha256:evidenceSha,raw_ids:proof.season_aliases.map(a=>a.raw_id)};
}
export function extendChaseIdentities(root,facts,swogi){
 const {proof,cards}=load(root),candidate=structuredClone(facts),old=previousChase(root,candidate,swogi),added=[];
 for(const a of proof.chase_aliases){
  const c=cardFor(a,cards,swogi),cfg=c.config,m=candidate.metadata[a.raw_id];
  check(m&&Object.keys(m).length===Object.keys(a.expected_metadata).length&&
   Object.entries(a.expected_metadata).every(([k,v])=>k==='runtime_id'?(m[k]===null||m[k]===a.runtime_id):m[k]===v),'prior_metadata_mismatch:'+a.raw_id);
  check(m.no_upgrade===cfg.noUpgrade&&m.hidden===cfg.hidden&&m.rarity===cfg.rarity&&
   m.name_has_thunder===cfg.name.includes('雷')&&m.desc_has_chase===cfg.desc.includes('再次行动'),'classification_mismatch:'+a.raw_id);
  // The existing mirror branch can already have bound this exact alias.
  if(m.runtime_id===null){candidate.metadata[a.raw_id]={...m,runtime_id:a.runtime_id};added.push(a.raw_id);}
 }
 for(const a of proof.chase_aliases){
  const m=candidate.metadata[a.raw_id];
  if(a.upgrade_runtime===null){check(m.no_upgrade,'last_grade_upgrade:'+a.raw_id);continue;}
  check(!m.no_upgrade&&candidate.metadata[a.raw_id+10000]?.runtime_id===a.upgrade_runtime&&
   typeof swogi[a.upgrade_runtime]?.card_actions==='function','chase_upgrade_closure:'+a.raw_id);
 }
 facts.metadata=candidate.metadata;
 return {...old,new_raw_ids:added,new_evidence_sha256:evidenceSha};
}
