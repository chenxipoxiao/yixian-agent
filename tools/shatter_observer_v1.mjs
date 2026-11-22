// Observation only. Do not change arguments, state transitions or return values.
export function observeShatter(game){
 const events=[],frames=[];
 const body=game.just_do_the_card_and_nothing_else;
 game.just_do_the_card_and_nothing_else=function(card){
  const id=this.players[0].currently_triggering_card_id;
  const e=['145091','145092','145093'].includes(id)?{runtime_id:id,body:String(card.card_actions),attacks:[],hp_cost_stacks:this.players[0].crash_fist_shatter_stacks}:null;
  if(e)events.push(e);frames.push(e);
  try{return Reflect.apply(body,this,[card]);}finally{frames.pop();}
 };
 const attack=game.atk;
 game.atk=function(...args){
  if(frames.at(-1))frames.at(-1).attacks.push(structuredClone(args));
  return Reflect.apply(attack,this,args);
 };
 return ()=>({events,training_label_allowed:false,scope:'observed simulator calls, not client action logs'});
}
