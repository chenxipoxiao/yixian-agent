import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='b2198cc8ad3b1df7319725394d3d8f673d9a240bc002c163eac7e4fa298c0203',installed=new WeakSet();
const check=(v,m)=>{if(!v)throw new Error('palm_vigor_unresolved:'+m);};
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
export function createPalmVigor(root,game,swogi,value,order=[0,1]) {
 if(value===undefined)return null;
 check(object(value)&&Object.keys(value).length===1&&Array.isArray(value.players)&&value.players.length===2,'explicit_players_required');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 check(value.players.every(a=>Array.isArray(a)&&new Set(a).size===a.length&&a.every(id=>[7089,15018].includes(id))),'invalid_ownership');
 check(value.players.some(a=>a.length),'empty_ownership');check(!installed.has(game),'already_installed');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-palm-vigor-v72.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');const facts=JSON.parse(raw);
 for(const [p,h] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 const states=new Map(game.players.map((p,i)=>[p,{index:order[i],ids:new Set(value.players[order[i]]),opened:false}]));
 for(const [p,s] of states)if(s.ids.has(15018))check(Number.isSafeInteger(p.hand_count)&&p.hand_count>=0,'explicit_hand_count_required');
 const events=[],boundaries=new Set();
 const emit=(p,id,phase,extra)=>events.push({player_index:states.get(p).index,strategy_id:id,phase,...extra});
 installed.add(game);
 return {
  installOpening(){
   check(!boundaries.has('opening'),'duplicate_opening_boundary');boundaries.add('opening');
   const previous=game.do_plant_start_permanent_buffs.bind(game);
   game.do_plant_start_permanent_buffs=function(...args){
    const p=this.players[0],s=states.get(p);
    if(s.ids.has(15018)){
     check(!s.opened,'opening_repeated');
     check(Number.isSafeInteger(p.hand_count)&&p.hand_count>=0,'explicit_hand_count_required');
     const before={hp:p.hp,max_hp:p.max_hp},eligible=p.hand_count>0;
     // The client uses current HP at this point, not maximum or terminal HP.
     // Refuse overflow/negative opening HP rather than approximating int32.
     check(Number.isSafeInteger(p.hp)&&p.hp>0&&p.hp*12<=2147483647,'opening_hp_outside_supported_range');
     const amount=eligible?Math.trunc(p.hp*12/100):0;s.opened=true;
     if(eligible){this.increase_idx_max_hp(0,amount);this.increase_idx_hp(0,amount);}
     emit(p,15018,'late_season_opening_before_plants',{hand_count:p.hand_count,eligible,requested:amount,before,after:{hp:p.hp,max_hp:p.max_hp}});
    }
    return previous(...args);
   };
  },
  installPlayBoundary(){
   check(!boundaries.has('play'),'duplicate_play_boundary');boundaries.add('play');
   const previous=game.do_cloud_sword_softheart_and_friends.bind(game);
   game.do_cloud_sword_softheart_and_friends=function(card){
    const p=this.players[0],s=states.get(p);
    if(s.ids.has(7089)){
     check(p.currently_triggering_card_id===card,'actual_card_identity_required');
     check(Object.hasOwn(facts.runtime_classification,card)&&typeof swogi[card]?.card_actions==='function','unknown_card:'+card);
     if(facts.runtime_classification[card].palm){
      const before=p.agility;this.increase_idx_x_by_c(0,'agility',2);
      emit(p,7089,'season_before_card_body',{card,trigger_depth:p.trigger_depth,before,requested:2,after:p.agility});
     }
    }
    return previous(card);
   };
  },
  metadata:()=>({evidence_sha256:digest,events:structuredClone(events),training_label_allowed:false})
 };
}
