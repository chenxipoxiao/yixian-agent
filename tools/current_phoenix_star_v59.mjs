// Owner-bound current 7064/7079. Temporary native reference slots are not real grids.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='4d1c6f567a03f44bea2d5ab11856f8fbc05fc466eb7e0d1fd77dc5bcb622c696',installed=new WeakSet();
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const check=(ok,message)=>{if(!ok)throw new Error('phoenix_star_unresolved:'+message);};
export function createPhoenixStar(root,game,value,order=[0,1]) {
 if(value===undefined)return null;
 check(object(value)&&Object.keys(value).length===1&&Array.isArray(value.players)&&value.players.length===2,'explicit_players_required');
 check(value.players.every(a=>Array.isArray(a)&&new Set(a).size===a.length&&a.every(id=>[7064,7079].includes(id)))&&value.players.some(a=>a.length),'invalid_ownership');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 check(!installed.has(game),'already_installed');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-phoenix-star-v59.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');const facts=JSON.parse(raw);
 for(const [file,hash] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,file))).digest('hex')===hash,'source_changed:'+file);
 const states=new Map(game.players.map((p,i)=>[p,{index:order[i],ids:new Set(value.players[order[i]]),opened:new Set(),phoenix:false,star:0}]));
 for(const [p,s] of states)if(s.ids.has(7064))check(Number.isSafeInteger(p.round_number)&&p.round_number>=1,'explicit_round_required');
 const events=[],openings=[],boundaries=new Set();
 const emit=(p,id,phase,extra={})=>events.push({player_index:states.get(p).index,strategy_id:id,phase,...extra});
 // Installed BEFORE the engraving wrapper: its temporary745 guard removal
 // runs first. This is before DEF decay and every turn-start damage/heal.
 // Supported native counter decays preceding this point change neither HP
 // nor guard. Legacy344 and unsupported resonance branches stay excluded.
 const decay=game.do_def_decay.bind(game);
 game.do_def_decay=function(...args){
  const p=this.players[0],s=states.get(p);
  if(s.ids.has(7064)){
   check(s.opened.has(7064),'opening_not_applied');
   if(s.phoenix&&p.hp<=facts.effects['7064'].hp_limit&&p.round_number>=facts.effects['7064'].effect_round){
    const before=p.guard_up;s.phoenix=false;
    this.increase_idx_x_by_c(0,'guard_up',1);
    emit(p,7064,'turn_start_after745_before_def_decay',{hp:p.hp,round:p.round_number,guard_before:before,guard_after:p.guard_up,remaining:0});
   }
  }
  return decay(...args);
 };
 installed.add(game);
 return {
  installOpening(id){
   check([7064,7079].includes(id)&&!boundaries.has(id),'duplicate_or_unknown_opening');boundaries.add(id);
   const previous=game.do_plant_start_permanent_buffs.bind(game);
   game.do_plant_start_permanent_buffs=function(...args){
    const p=this.players[0],s=states.get(p);
    if(s.ids.has(id)&&!s.opened.has(id)){
     s.opened.add(id);if(id===7064)s.phoenix=true;else s.star=facts.effects['7079'].charges;
     openings.push({player_index:s.index,strategy_id:id,phase:'owner_season_start',charges:id===7064?1:s.star});
    }
    return previous(...args);
   };
  },
  installBeforeEngraving(){
   check(!boundaries.has('before'),'duplicate_before_boundary');boundaries.add('before');
   const previous=game.do_cloud_sword_softheart_and_friends.bind(game);
   game.do_cloud_sword_softheart_and_friends=function(card){
    const p=this.players[0],s=states.get(p);
    if(s.ids.has(7079)){
     check(s.opened.has(7079),'opening_not_applied');
     if(s.star>0){
      const slot=p.currently_triggering_card_idx;
      // Repeated real-card executions retain their own grid and each count.
      // A nested trigger_card only carries a reference slot: fail closed while
      // any charges remain, even when that reference slot is not a star.
      check(p.trigger_depth===1&&Number.isInteger(slot)&&slot>=0&&slot<p.cards.length&&p.currently_playing_card_idx===slot&&p.cards[slot]===card,'temporary_or_unknown_card_grid');
      check(typeof p.is_star_point[slot]==='boolean','star_grid_unresolved');
      if(p.is_star_point[slot]){
       const target=this.players[1],before={charges:s.star,internal_injury:target.internal_injury,hexproof:target.hexproof};s.star--;
       this.increase_idx_debuff(1,'internal_injury',1);
       emit(p,7079,'star_before_engraving',{card,slot,trigger_depth:p.trigger_depth,before,after:{charges:s.star,internal_injury:target.internal_injury,hexproof:target.hexproof}});
      }
     }
    }
    return previous(card);
   };
  },
  metadata:()=>({evidence_sha256:digest,openings:structuredClone(openings),events:structuredClone(events),
   remaining:[...states.values()].filter(s=>s.ids.size).map(s=>({player_index:s.index,phoenix:s.phoenix,star:s.star})).sort((a,b)=>a.player_index-b.player_index),
   temporary_card_grid_supported:false,training_label_allowed:false})
 };
}
