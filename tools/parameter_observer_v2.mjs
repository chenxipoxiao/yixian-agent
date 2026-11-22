// Read-only observation of effective random entrypoints in the v96 battle.
export function observeParameterConsumersV2(game, order) {
 const reads=[], stack=[], seats=new Map(game.players.map((p,i)=>[p,order[i]]));
 let insidePost=0,rngCalls=0;
 const snapshot=()=>{
  const p=game.players[0];return {player_index:seats.get(p),card:p.currently_triggering_card_id,
   slot:p.currently_triggering_card_idx,hp:p.hp,max_hp:p.max_hp,qi:p.qi,def:p.def,
   hexagram:p.hexagram,triggered_hexagram_count:p.triggered_hexagram_count};
 };
 const post=game.if_post_action;
 game.if_post_action=function(...args){insidePost++;try{return Reflect.apply(post,this,args);}finally{insidePost--;}};
 for(const name of ['rand_range','if_c_pct','trigger_hexagram','random_int','random_debuff_from_pool',
  'add_random_debuff','reduce_idx_random_debuff_by_c_n_times','convert_random_debuffs_to_increase_atk',
  'transfer_random_debuff','trigger_random_sect_card','trigger_random_unrestrained_card','do_endless_crash',
  'trigger_replay_card_from_next_random_outcome']){
  const original=game[name];if(typeof original!=='function')throw new Error('observer_missing_method:'+name);
  game[name]=function(...args){
   const item={method:name,args:structuredClone(args),before:snapshot(),within_post_action:insidePost>0,parent:stack.at(-1)??null};
   const index=reads.length;reads.push(item);stack.push(index);
   try{const result=Reflect.apply(original,this,args);if(result!==undefined)item.result=structuredClone(result);return result;}
   finally{item.after=snapshot();stack.pop();}
  };
 }
 const rng=game.rng;game.rng=function(...args){rngCalls++;return Reflect.apply(rng,this,args);};
 return ()=>({reads,rng_calls:rngCalls,training_label_allowed:false,
  scope:'Effective simulator reads only; not client action logs or proof of random distribution.'});
}
