// A recorded selected-card ID is checked against the already restored ordered
// hand. It never chooses or constructs that hand and never spends hexagram.
const check=(ok,why)=>{if(!ok)throw new Error('flag_paper_parameters_unresolved:'+why);};
export function installFlagParameterReader(game,swogi,hands,order,facts,consume){
 check(Array.isArray(hands)&&hands.length===2,'explicit_bound_hands_required');
 const states=new Map(game.players.map((p,i)=>[p,{hand:hands[order[i]],index:order[i]}]));
 const body=game.current_element_flag,trigger=game.trigger_card;
 check(typeof body==='function'&&typeof trigger==='function','flag_runtime_required');
 let active=null;
 game.current_element_flag=function(raw){
  const p=this.players[0],s=states.get(p),c=facts.cards.find(c=>c.raw_id===raw),slot=p.currently_triggering_card_idx;
  check(c&&p.currently_triggering_card_id===c.runtime_id,'flag_card_identity');
  check(active===null&&p.trigger_depth===1&&slot===p.currently_playing_card_idx&&p.cards[slot]===c.runtime_id,'flag_outer_slot_identity');
  // Only odd-slot originals are admitted here. An even slot's later seal read
  // must be added at its real boundary, never consumed before nested effects.
  check(Number.isInteger(slot)&&slot%2===0,'even_slot_seal_reader_not_admitted');
  check(Array.isArray(s?.hand)&&s.hand.length===p.hand_count&&s.hand.every(x=>Object.hasOwn(facts.hand_metadata,x)),'invalid_original_hand');
  const source=s.hand.find(x=>facts.hand_metadata[x].kind==='formation');let selected=null;
  if(source!==undefined){
   const meta=facts.hand_metadata[source],cap=c.config.otherParams[0];let target=source;
   if(!meta.hidden&&meta.rarity>=cap)target-=10000*(meta.rarity-cap+1);
   const m=facts.hand_metadata[target];
   check(m?.kind==='formation'&&m.runtime_id&&typeof swogi[m.runtime_id]?.card_actions==='function','unmapped_first_formation:'+target);
   selected={source_raw:source,raw:target,runtime_id:m.runtime_id};
  }
  consume({kind:'element_flag_formation',type:'selected_card_id',phase:'card_body',raw_card_id:raw,runtime_card_id:c.runtime_id,
   player_index:s.index,slot,expected_value:selected?.raw??-1,selection:selected,hand_order_bound:true,forced_by_hexagram:false});
  active={p,c,slot,selected,triggers:0};
  try{
   const result=body.call(this,raw);
   check(active.triggers===(selected===null?0:1),'missing_flag_nested_execution');
   return result;
  }finally{active=null;}
 };
 game.trigger_card=function(id,slot,...rest){
  if(active&&this.players[0]===active.p&&active.p.currently_triggering_card_id===active.c.runtime_id){
   check(active.p.trigger_depth===1&&slot===active.slot&&active.triggers===0&&id===active.selected?.runtime_id,'flag_selected_runtime_mismatch');
   active.triggers++;
  }
  return trigger.call(this,id,slot,...rest);
 };
 return {verifyIdle:()=>check(active===null,'unfinished_flag_execution')};
}
