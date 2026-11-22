// Optional callbacks at fixed client callsites. Ownership and every private
// start value are supplied by the source-bound v124 compiler, never a terminal.
import {FIST_STANCE,STICK_STANCE} from '../external/yisim/card_info.js';
const check=(ok,why)=>{if(!ok)throw new Error('season_batch_unresolved:'+why);};
export function installSeasonCallbacks(game,api,swogi){
 if(!api)return;
 const {facts,has,state,param,enabled,effective,card,actualSlot,add,counter,setCounter,consume,raiseHp,replace,upgrade,deckElements,deckElementCount,activate,emit}=api;
 const owner=idx=>game.players[idx];
 const positive=n=>{check(Number.isSafeInteger(n)&&n>=0&&n<=2147483647,'positive_client_int');return n;};
 game.currentSeasonForceGain=(idx,n)=>{const p=owner(idx),extra=counter(p,769);if(n>0&&extra>0){setCounter(p,769,0);emit(p,7087,'first_force',{extra});return positive(n+extra);}return n;};
 game.currentSeasonHexagramGain=(idx,n)=>{const p=owner(idx);if(n>0&&consume(p,764)){emit(p,7077,'positive_hexagram');return positive(n+1);}return n;};
 game.currentSeasonConvertStar=(idx,n)=>{const p=owner(idx);if(n>0&&has(p,23069)&&enabled(p,23069)){game.increase_idx_debuff(1-idx,'internal_injury',n);emit(p,23069,'convert_star',{amount:n});return true;}return false;};
 game.currentSeasonPhysiqueGain=(idx,n)=>{const p=owner(idx),s=state(p);if(n>0&&has(p,7042)&&!s.physiqueQi){s.physiqueQi=true;game.increase_idx_qi(idx,1);emit(p,7042,'first_physique_in_turn');}};
 game.currentSeasonReactivation=(idx,field,n)=>{const p=owner(idx),s=state(p);if(n>0&&p[field]>1&&has(p,7048)&&!s.reactivated){s.reactivated=true;game.increase_idx_qi(idx,1);emit(p,7048,'reactivation_before7084',{field});}};
 game.currentSeasonBuffAdded=(idx,field,n)=>{const p=owner(idx);if(field==='agility'&&n>0&&consume(p,771)){game.increase_idx_physique(idx,1);emit(p,7091,'positive_agility');}};
 game.currentSeasonDefGain=(idx,n)=>{const p=owner(idx);return n>0&&has(p,7133)&&effective(p,7133)?positive(n+1):n;};
 game.currentSeasonDebuffBefore=(idx,field,n)=>{const p=owner(idx);if(field==='internal_injury'&&n>0&&consume(p,753)){emit(p,7063,'incoming_internal_injury');return positive(n+1);}return n;};
 game.currentSeasonDebuffAccepted=(idx,field,n)=>{const p=owner(1-idx);if(n>0&&has(p,7080)&&['internal_injury','weaken','flaw'].includes(field)){game.increase_idx_qi(1-idx,1);emit(p,7080,'opponent_debuff_accepted',{field,amount:n});}};
 game.currentSeasonStyxHeals=p=>has(p,27021);
 game.currentSeasonAttackBonus=(idx,isExtra)=>{
  const p=owner(idx),id=p.currently_triggering_card_id;
  let result=0;
  if(!isExtra&&(has(p,3003)||has(p,7088))){const slot=actualSlot(p,id);if(has(p,3003)&&slot>=param(3003))result+=param(3003,1);if(has(p,7088)&&slot===7)result+=Math.trunc(game.get_debuff_count(idx)/param(7088));}
  if(!isExtra&&has(p,7092)&&game.is_crash_fist(id))result+=Math.min(param(7092,1),Math.trunc(p.qi/param(7092)));
  if(has(p,7101)){const c=card(id,['desc','anima']);if(c.desc.includes('灵气')||c.anima<0)result+=param(7101);}
  return positive(result);
 };
 // 574 is checked at the beginning of CalculateAttack, before smash-def.
 game.currentSeasonBeforeAttack=idx=>{const p=owner(idx),id=p.currently_triggering_card_id;if(counter(p,574)>0&&card(id,['name']).name.includes('雷')){const n=counter(p,574);setCounter(p,574,0);add(idx,'smash_def',1);game.increase_idx_debuff(1-idx,'wound',n);emit(p,7127,'first_thunder_attack');}};
 game.currentSeasonDamageReduction=idx=>state(owner(idx)).turn===3&&game.players.some(p=>has(p,1010)&&enabled(p,1010))?40:0;
 game.currentSeasonAfterHit=(idx,amount)=>{const p=owner(idx);if(amount>0&&consume(p,770)){game.increase_idx_debuff(1-idx,p.stance===FIST_STANCE?'decrease_atk':'weaken',1);emit(p,7104,'first_attack_injury',{amount});}};
 game.currentSeasonTurnStart=()=>{const p=owner(0),s=state(p);s.turn++;s.physiqueQi=false;s.reactivated=false;setCounter(p,754,0);};
 game.currentSeasonNoAttackTurnEnd=()=>{const p=owner(0);if(has(p,7002)&&!p.this_turn_attacked){add(0,'sword_intent',param(7002));emit(p,7002,'turn_end_without_attack');}};
 game.currentSeasonWaterDefense=()=>{const p=owner(0);if(has(p,7138)){const n=Math.trunc(p.force_of_water/param(7138));if(n>0)game.increase_idx_def(0,n);emit(p,7138,'water_defense',{amount:n});}};
 game.currentSeasonCloudSeaConsumed=()=>{const p=owner(0);if(has(p,7010)){game.increase_idx_qi(0,1);emit(p,7010,'noncloud_preserved_chain');}};
 game.currentSeasonAfterCard=id=>{const p=owner(0),n=counter(p,768);if(n>0&&card(id,['name']).name.includes('火灵')){setCounter(p,768,0);game.atk(n,true);emit(p,7099,'first_fire_after_card',{attack:n});}};
 game.currentSeasonWoodCost=(id,n)=>{const p=owner(0);if(n>0&&has(p,23066)&&card(id,['name']).name.includes('木灵')){const paid=positive(n*param(23066));game.reduce_idx_hp(0,paid,true);emit(p,23066,'wood_qi_as_hp_cost',{qi_cost:n,hp_cost:paid});return 0;}return n;};
 game.currentSeasonStyxCost=(id,n)=>{const p=owner(0),shortfall=n-p.qi;if(shortfall>0&&has(p,7115)&&p.styx>=shortfall){game.reduce_idx_x_by_c(0,'styx',shortfall);emit(p,7115,'styx_qi_shortfall',{card:id,amount:shortfall});return p.qi;}return n;};
 game.currentSeasonAfterHpCost=id=>{const p=owner(0);if(has(p,7118)&&card(id,['hpCost']).hpCost>0&&counter(p,754)===0){setCounter(p,754,1);game.increase_idx_qi(0,1);game.increase_idx_hp(0,3);emit(p,7118,'first_hp_cost_card_in_turn');}};
 game.currentSeasonAfterBody=id=>{const p=owner(0);if(has(p,7071)&&card(id,['raw_id']).raw_id===19){const n=p.qi;game.reduce_idx_x_by_c(0,'qi',n);add(0,'sword_qi',n);emit(p,7071,'clear_heart_qi_conversion',{amount:n});}};
 game.currentSeasonBeforePot=slot=>{const p=owner(0),c=card(p.cards[slot],['sect','noUpgrade'],{player:p,slot});if(counter(p,792)>0&&c.sect===3&&!c.noUpgrade){upgrade(p,slot);consume(p,792);emit(p,11003,'first_upgradable_five_elements',{slot});}};
 game.currentSeasonSkipSelected=()=>{
  const p=owner(0);let skips=0;
  const advance=()=>{check(++skips<=p.cards.length*2,'no_executable_card_after_skip');game.advance_next_card_index();};
  if(has(p,7116)&&enabled(p,7116))while(p.next_card_index===4){const id=p.cards[p.next_card_index];if(swogi[id].is_astral_move){game.increase_idx_qi(0,1);game.increase_idx_hp(0,param(7116));}emit(p,7116,'skip_fifth',{card:id});advance();}
  if(has(p,5010)&&enabled(p,5010))while(p.next_card_index>=5&&card(p.cards[p.next_card_index],['base_id'],{player:p,slot:p.next_card_index}).base_id!==0){emit(p,5010,'skip_last_three',{slot:p.next_card_index});advance();}
 };
 const reduceHp=game.reduce_idx_hp.bind(game);
 game.reduce_idx_hp=function(idx,n,isCost,...args){const p=owner(idx),guard=p.guard_up;const out=reduceHp(idx,n,isCost,...args);const s=state(p);s.pendingGuard=Math.max(0,s.pendingGuard-Math.max(0,guard-p.guard_up));if(isCost&&n>0&&has(p,7102)){this.increase_idx_physique(idx,1);emit(p,7102,'hp_cost');}return out;};
 const decay=game.do_def_decay.bind(game);
 game.do_def_decay=function(...args){const p=owner(0),s=state(p);if(s.pendingGuard>0){const n=s.pendingGuard;s.pendingGuard=0;this.reduce_idx_x_by_c(0,'guard_up',n);emit(p,23079,'temporary_guard_expired',{amount:n});}return decay(...args);};
 const cloudHit=game.if_cloud_hit.bind(game);
 game.if_cloud_hit=function(){return has(owner(0),11001)||cloudHit();};
 const unrestrained=game.is_unrestrained_sword.bind(game);
 game.is_unrestrained_sword=function(id){const p=owner(0);if(has(p,7049)&&card(id,['career']).career===3)return true;if(has(p,7068)&&card(id,['desc']).desc.includes('[击伤]'))return true;return unrestrained(id);};
 for(const element of ['wood','fire','earth','metal','water']){const name='if_'+element+'_spirit',before=game[name].bind(game);game[name]=function(...args){return has(owner(0),11003)||before(...args);};}
 const countElements=game.get_n_different_five_elements.bind(game);
 game.get_n_different_five_elements=function(idx){return has(owner(idx),7085)?deckElementCount(owner(idx)):countElements(idx);};
 // These run in the ordinary startup phases, before seasonal opening effects.
 const phase1=game.apply_p1_fates_setup.bind(game);
 game.apply_p1_fates_setup=function(idx){const p=owner(idx);if(p.character==='dx5'||has(p,27023)){if(has(p,7111))p.stance=STICK_STANCE;else if(has(p,27023))p.stance=FIST_STANCE;}return phase1(idx);};
 const vase=game.do_five_elements_pure_vase.bind(game);
 game.do_five_elements_pure_vase=function(idx){const out=vase(idx),p=owner(idx);if(has(p,23058)&&p.five_elements_pure_vase_stacks>0){const raws=state(p).input.vase;check(Array.isArray(raws)&&raws.length===3,'explicit_vase_for23058');const c=facts.raw_cards[raws[1]];check(c,'vase_second_raw_identity');for(const [name,element] of [['金灵','metal'],['水灵','water'],['木灵','wood'],['火灵','fire'],['土灵','earth']])if(c.name.includes(name))activate(idx,element);emit(p,23058,'vase_second_activation');}return out;};
 const gold=game.do_solitary_void_golden_scroll_fate.bind(game);
 game.do_solitary_void_golden_scroll_fate=function(idx){const p=owner(idx);if(!has(p,7061))return gold(idx);for(let slot=0;slot<p.cards.length;slot++){if(card(p.cards[slot],['base_id'],{player:p,slot}).base_id!==215)continue;let ups=2;const len=p.cards.length,prev=(slot+len-p.card_play_direction)%len,next=(slot+len+p.card_play_direction)%len;if(card(p.cards[prev],['base_id'],{player:p,slot:prev}).base_id===0){replace(p,prev,216);ups--;}if(card(p.cards[next],['base_id'],{player:p,slot:next}).base_id===0){replace(p,next,217);ups--;}for(let n=0;n<ups;n++)if(!upgrade(p,slot))break;emit(p,7061,'golden_scroll_start',{slot,upgrades:ups});}};
 const stance=game.switch_stance.bind(game);
 game.switch_stance=function(){const p=owner(0);if(has(p,7111)){this.increase_idx_physique(0,param(7111));this.increase_idx_def(0,param(7111,1));p.stance=STICK_STANCE;emit(p,7111,'switch_to_stick');}else stance();if(has(p,7113)){this.deal_damage(param(7113));emit(p,7113,'stance_switch_damage');}if(has(p,7090)){if(p.stance===FIST_STANCE)this.increase_idx_force(0,param(7090));else add(0,'increase_atk',param(7090,1));emit(p,7090,'stance_switch_bonus');}};
 const setup=game.start_of_game_setup.bind(game);
 game.start_of_game_setup=function(){const out=setup();const p=owner(1);if(has(p,7110)){setCounter(p,335,counter(p,335)+1);emit(p,7110,'second_player_post_action');}return out;};
 const post=game.if_post_action.bind(game);
 game.if_post_action=function(){const p=owner(0),idx=p.currently_playing_card_idx;if(!p.can_post_action[idx]&&counter(p,335)>0){this.do_post_strike(p.currently_triggering_card_id,idx);consume(p,335);emit(p,7110,'consume_first_post_action');return true;}return post();};
 const body=game.just_do_the_card_and_nothing_else.bind(game);
 game.just_do_the_card_and_nothing_else=function(c){const p=owner(0),id=p.currently_triggering_card_id;if(!has(p,7082)||card(id,['base_id']).base_id!==7000073)return body(c);const raw=card(id,['raw_id']).raw_id,cfg=facts.raw_cards[raw];if(cfg.anima>0)this.increase_idx_qi(0,cfg.anima);if(cfg.def>0)this.increase_idx_def(0,cfg.def);const count=deckElementCount(p,true);if(count===1||count===2)add(0,'five_elements_heavenly_marrow_rhythm_stacks',cfg.otherParams[0]);emit(p,7082,'heavenly_marrow_body',{card:id,count});};
 // 772 is the final revive branch, after all earlier revive sources and 612.
 const revive=game.check_idx_for_revive.bind(game);
 game.check_idx_for_revive=function(idx){const result=revive(idx),p=owner(idx);if(p.hp>0||p.got_void_split_speared||counter(p,772)<=0)return result;const n=positive((p.star_power+p.hexagram)*counter(p,772));setCounter(p,772,0);if(n>0){p.star_power=0;p.hexagram=0;raiseHp(idx,n);p.just_revived=true;}emit(p,7093,'revive_after597',{amount:n,hp:p.hp,max_hp:p.max_hp});return result||n>0;};
 // The client sword-qi OR adds the cloud-sword branch without a second hit
 // when the same card also qualifies through Dharma/other native sources.
 game.currentSeasonSwordQiQualifies=id=>(has(owner(0),7067)&&game.is_cloud_sword(id))||(has(owner(0),7071)&&card(id,['raw_id']).raw_id===19);
 //742 is read after all ordinary repeats and the main ExecuteEffect. It
 // executes a first-rarity copy on the same physical grid (isTemp=false),
 // preserves hadUsed, and restores the actual card before280 is evaluated.
 const play=game.play_card.bind(game),ultimate=game.do_ultimate_overcome_formation.bind(game);
 let deferUltimate=false;
 game.do_ultimate_overcome_formation=function(idx){if(!deferUltimate)return ultimate(idx);};
 game.play_card=function(id,idx){
  const p=owner(0);
  if(counter(p,742)<=0||!card(id,['name']).name.includes('灵阵'))return play(id,idx);
  check(p.trigger_depth===0&&p.cards[idx]===id,'742_physical_card_required');
  check(!deferUltimate,'742_nested_outer_execution');
  deferUltimate=true;
  try{
   play(id,idx);
   if(counter(p,742)>0){
    const current=p.cards[idx],rawCurrent=state(p).rawCards[idx],c=card(current,['base_id','rarity'],{player:p,slot:idx});
    if(c.rarity>0)replace(p,idx,c.base_id);
    const replay=p.cards[idx];consume(p,742);
    p.currently_playing_card_idx=idx;
    p.this_card_attacked=false;p.this_card_directly_attacked=false;
    try{
     this.trigger_card(replay,idx);
     if(p.this_card_attacked)this.reduce_idx_x_by_c(0,'m_sinking_qi_stacks',1);
     p.can_post_action[idx]=true;
     emit(p,7031,'first_spirit_formation_replay',{slot:idx,actual:current,replay});
    }finally{p.cards[idx]=current;state(p).rawCards[idx]=rawCurrent;p.currently_playing_card_idx=undefined;}
   }
  }finally{deferUltimate=false;}
  ultimate(idx);
 };
 // Additional engraving branches are inserted into the existing sorted
 // first-use ledger; this callback is not a second independent ledger.
 game.currentSeasonEngraving=(id,slot)=>{
  const p=owner(0),c=card(p.cards[slot],undefined,{player:p,slot});
  if(id===13005)game.increase_idx_def(0,param(id)*deckElementCount(p));
  else if(id===13010){let at=slot;for(let i=0;i<param(id);i++){at=game.get_next_idx(at);if(p.is_star_point[at])game.increase_idx_qi(0,1);else p.is_star_point[at]=true;}}
  else if(id===13011){if(c.name.includes('金灵'))game.increase_idx_penetrate(0,param(id));if(c.name.includes('水灵')||c.name.includes('木灵'))game.increase_idx_qi(0,param(id,1));if(c.name.includes('火灵')||c.name.includes('土灵'))game.increase_idx_def(0,param(id,2));}
  else if(id===13012){add(0,'max_force',1);add(0,'majestic_qi_stacks',param(id));}
  else if(id===13014){game.increase_idx_physique(0,param(id));game.increase_idx_def(0,Math.trunc(p.physique/param(id,1)));}
  else if(id===13018){if(c.name.includes('水灵'))add(0,'m_water_spirit_billows_stacks',1);if(c.name.includes('木灵')&&p.increase_atk>0){const n=Math.min(2,p.increase_atk);game.reduce_idx_x_by_c(0,'increase_atk',n);add(0,'wood_thorn',n);}}
  else check(false,'unknown_engraving:'+id);
  emit(p,id,'engraving_first_use',{slot});
 };
}
