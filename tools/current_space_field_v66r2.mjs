import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='f7e5c5c5747506fb80f94695b46da9846ebebebea125c270ad62e2c0f8d717bb',cache=new Map(),installed=new WeakSet(),ID='D26035';
const check=(ok,why)=>{if(!ok)throw new Error('space_field_unresolved:'+why);};
function factsAt(root){
 if(cache.has(root))return cache.get(root);
 const b=fs.readFileSync(path.join(root,'data/inspection/current-space-field-v66.json'));
 check(crypto.createHash('sha256').update(b).digest('hex')===digest,'evidence_changed');const f=JSON.parse(b);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,f);return f;
}
export function registerSpaceField(root,swogi){
 factsAt(root);const c=swogi[ID];
 check(c?.name==='Dream - Space Spiritual Field'&&typeof c.card_actions==='function'&&c.qi_cost===0&&(c.hp_cost===undefined||c.hp_cost===0)&&!c.is_continuous&&!c.is_consumption,'native_card_binding');
 // Pinned reference omits zero hp_cost; local CardConfig explicitly supplies0.
 swogi[ID]=Object.freeze({...c,hp_cost:0});
}
export function installSpaceField(root,game,swogi,order=[0,1]){
 const owners=game.players.filter(p=>p.cards.includes(ID));if(!owners.length)return null;
 factsAt(root);check(!installed.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(x=>x===0||x===1),'invalid_order');
 const seats=new Map(game.players.map((p,i)=>[p,order[i]])),events=[];
 for(const p of owners){
  check(p.cards.length>=2&&p.cards.length<=8,'unsupported_deck_length');
  const setup=p.post_deck_setup.bind(p);
  p.post_deck_setup=function(...a){
   const r=setup(...a);
   for(let i=0;i<this.cards.length;i++)if(this.cards[i]===ID&&i+2>=this.cards.length){
    check(this.skip_one_play[i]===1,'unexpected_native_first_skip');this.skip_one_play[i]=0;
   }
   return r;
  };
 }
 const skip=game.do_skip_next_card.bind(game);
 game.do_skip_next_card=function(...a){
  let r=skip(...a);const p=this.players[0];let n=0;
  while(p.cards[p.next_card_index]===ID&&p.next_card_index+2>=p.cards.length&&!p.can_post_action[p.next_card_index]){
   check(n++<p.cards.length,'skip_cycle');const slot=p.next_card_index;
   check(p.can_play[slot]===true,'inactive_actual_card');
   const before={qi:p.qi,hp:p.hp,chases:p.chases,cloud:p.cloud_sword_chain_count};
   p.can_post_action[slot]=true;this.advance_next_card_index();
   events.push({kind:'first_use_skip',player_index:seats.get(p),slot,next_slot:p.next_card_index,had_used:true,before,
    after:{qi:p.qi,hp:p.hp,chases:p.chases,cloud:p.cloud_sword_chain_count}});
   r=skip(...a);
  }
  return r;
 };
 const body=game.just_do_the_card_and_nothing_else.bind(game);
 game.just_do_the_card_and_nothing_else=function(card){
  const p=this.players[0];
  if(p.currently_triggering_card_id===ID){
   check(card===swogi[ID],'card_identity');events.push({kind:'empty_body_executed',player_index:seats.get(p),slot:p.currently_triggering_card_idx,trigger_depth:p.trigger_depth});
  }
  return body(card);
 };
 installed.add(game);
 return {metadata:()=>({evidence_sha256:digest,events:structuredClone(events),recorded_action_log:false,training_label_allowed:false}),
  postBattle:terminated=>[...seats].flatMap(([p,index])=>p.cards.flatMap((id,slot)=>id===ID?[{
   raw_card_id:350,player_index:index,slot,status:terminated?'postbattle_resource_resolution_pending':'combat_not_terminal',
   applied:false,next_battle_allowed:false,training_label_allowed:false,
   pending:['cultivation_payment','eligible_level1_regular_card_pool','copy_selection','one_time_receipt'],
   current_battle_cultivation_modified:false}]:[]))};
}
