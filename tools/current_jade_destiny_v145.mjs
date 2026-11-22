// Read-only combat ledger. Existing card bodies and balance mutations are kept.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='fa61611721da09eb81f27b4b600b50de8a980995d11790f4ea83146ad1722fb9';
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const check=(ok,why)=>{if(!ok)throw new Error('combat_destiny_v145:'+why);};
const installed=new WeakSet();
let cached;
function proof(root){
 if(cached)return cached;
 const bytes=fs.readFileSync(path.join(root,'data/inspection/combat-net-destiny-v145.json'));
 check(hash(bytes)===digest,'proof_changed');
 const facts=JSON.parse(bytes);
 for(const [p,h] of Object.entries(facts.source_sha256))check(hash(fs.readFileSync(path.join(root,p)))===h,'source_changed:'+p);
 cached=facts;return facts;
}
export function installJadeDestinyObserver(root,game,swogi,order,input){
 const facts=proof(root);
 check(!installed.has(game),'already_installed');
 const originals=[...game.players],events=[];
 const byCard=new Map(facts.cards.map(c=>[swogi[c.runtime_id],c]));
 check(byCard.size===3&&!byCard.has(undefined),'three_native_cards_required');
 const original=game.just_do_the_card_and_nothing_else.bind(game);
 game.just_do_the_card_and_nothing_else=function(card){
  const fact=byCard.get(card);
  if(fact===undefined)return original(card);
  const player=this.players[0],runtimeSeat=originals.indexOf(player);
  check(runtimeSeat>=0,'unknown_player');
  const before=player.destiny,hpBefore=player.hp;
  const value=original(card);
  events.push({player_index:order[runtimeSeat],raw_card:fact.raw_id,runtime_card:fact.runtime_id,
   phase:'card_body_after_hp_recovery',configured_gain:fact.destiny_gain,
   native_destiny_before:before,native_destiny_after:player.destiny,
   observed_gain:player.destiny-before,hp_before:hpBefore,hp_after:player.hp,
   authoritative_match_state_mutated:false});
  return value;
 };
 installed.add(game);
 return {metadata:()=>{
  const end=[null,null];originals.forEach((p,i)=>end[order[i]]=p.destiny);
  return {evidence_sha256:digest,events:structuredClone(events),
   native_destiny_before:input.players.map(p=>p.destiny),native_destiny_after:end,
   observed_jade_gains:[0,1].map(i=>events.filter(e=>e.player_index===i).reduce((s,e)=>s+e.observed_gain,0)),
   battle_bodies_changed:false,authoritative_match_state_mutated:false,training_label_allowed:false};
 }};
}
