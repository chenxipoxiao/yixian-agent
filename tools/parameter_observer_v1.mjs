// Observe effective consumers without changing their arguments or results.
export function observeParameterConsumers(game){
 const bodies=[],reads=[],calls=[],stack=[];let inPost=0,rngCalls=0;
 const targets=new Set(['714031','714032','714033','125121','125122','125123']);
 const snap=()=>{const p=game.players[0];return {card:p.currently_triggering_card_id,slot:p.currently_triggering_card_idx,
   hp:p.hp,max_hp:p.max_hp,qi:p.qi,def:p.def,hexagram:p.hexagram,hp_gained:p.hp_gained};};
 const body=game.just_do_the_card_and_nothing_else;
 game.just_do_the_card_and_nothing_else=function(card){
  const id=this.players[0].currently_triggering_card_id,e=targets.has(id)?{id,body:String(card.card_actions),before:snap(),calls:[]}:null;
  if(e)bodies.push(e);stack.push(e);
  try{return Reflect.apply(body,this,[card]);}finally{if(e)e.after=snap();stack.pop();}
 };
 for(const name of ['atk','increase_idx_hp','increase_idx_def','add_c_of_x','spirit_sword_deck_count','chase']){
  const original=game[name];game[name]=function(...args){
   const e=stack.at(-1),c=e?{method:name,args:structuredClone(args)}:null;
   const result=Reflect.apply(original,this,args);if(c){if(result!==undefined)c.result=result;e.calls.push(c);}return result;
  };
 }
 const post=game.if_post_action;
 game.if_post_action=function(...args){inPost++;try{return Reflect.apply(post,this,args);}finally{inPost--;}};
 const pct=game.if_c_pct;
 game.if_c_pct=function(...args){
  const before=snap(),result=Reflect.apply(pct,this,args);
  reads.push({method:'if_c_pct',within_post_action:inPost>0,threshold:args[0],before,after:snap(),result});return result;
 };
 const rng=game.rng;game.rng=function(...args){rngCalls++;return Reflect.apply(rng,this,args);};
 return ()=>({bodies,reads,rng_calls:rngCalls,training_label_allowed:false,
  scope:'observed simulator consumers, not independent client action logs or bound random streams'});
}
