//3004 opens at its own seasonal boundary;7121 is a deferred match reward.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='54ed50a5ad0af3587d5ed85a389f3ee41c4be517c6ab22160b86da23f3e1bb56',installed=new WeakSet();
const check=(v,m)=>{if(!v)throw new Error('dragon_season_unresolved:'+m);};
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
export function createDragonSeason(root,game,value,order=[0,1]) {
 if(value===undefined)return null;
 check(object(value)&&Object.keys(value).length===1&&Array.isArray(value.players)&&value.players.length===2,'explicit_players_required');
 check(value.players.every(a=>Array.isArray(a)&&new Set(a).size===a.length&&a.every(id=>[3004,7121].includes(id))),'invalid_ownership');
 check(value.players.some(a=>a.length),'owner_required');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 check(!installed.has(game),'already_installed');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-dragon-season-v65.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');const facts=JSON.parse(raw);
 for(const [p,h] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 const players=[...game.players],states=new Map(players.map((p,i)=>[p,{index:order[i],ids:new Set(value.players[order[i]]),opened:false,pending:0}]));
 const events=[],boundaries=new Set();
 const emit=(p,kind,extra={})=>events.push({player_index:states.get(p).index,kind,...extra});
 //Install after native attack-preparation hooks:441/442 occur in atk before
 //this inner call. Non-attack damage never consumes784. Native12 percentage
 //calculation and owner-turn cleanup remain unchanged.
 const damage=game.deal_damage_inner.bind(game);
 game.deal_damage_inner=function(amount,isAttack,sourceIdx,...rest){
  check(sourceIdx===0||sourceIdx===1,'invalid_damage_source');
  const target=this.players[1-sourceIdx],state=states.get(target);
  if(isAttack&&state.pending>0){
   const turns=state.pending,before=target.water_spirit_dive_stacks;
   state.pending=0;
   this.increase_idx_x_by_c(1-sourceIdx,'water_spirit_dive_stacks',turns);
   emit(target,'first_received_attack_784_to_12',{turns,dive_before:before,dive_after:target.water_spirit_dive_stacks,requested_attack:amount});
  }
  return damage(amount,isAttack,sourceIdx,...rest);
 };
 installed.add(game);
 return {
  installOpening(){
   check(!boundaries.has(3004),'duplicate_opening');boundaries.add(3004);
   const previous=game.do_plant_start_permanent_buffs.bind(game);
   game.do_plant_start_permanent_buffs=function(...args){
    const p=this.players[0],state=states.get(p);
    if(state.ids.has(3004)&&!state.opened){state.opened=true;state.pending=facts.effects['3004'].dive_turns;emit(p,'season_opening_3004',{client_buff:784,pending:state.pending});}
    return previous(...args);
   };
  },
  postBattle(terminated){
   check(typeof terminated==='boolean','explicit_termination_required');
   //A proposal for the future authoritative match ledger, never battle healing.
   //Do not guess cap/overflow or interaction with ordinary fate177 rewards.
   return players.flatMap(p=>{
    const s=states.get(p);if(!s.ids.has(7121))return [];
    if(!terminated)return [{player_index:s.index,strategy_id:7121,status:'combat_not_terminal',next_battle_allowed:false}];
    const counts=Object.fromEntries(facts.debuff_fields.map(k=>{check(Number.isSafeInteger(p[k])&&p[k]>=0,'invalid_terminal_debuff:'+k);return [k,p[k]];}));
    const total=Object.values(counts).reduce((a,b)=>a+b,0);check(Number.isSafeInteger(total),'debuff_sum_overflow');
    return [{player_index:s.index,strategy_id:7121,status:'pending_authoritative_match_reward',terminal_debuffs:counts,total_debuff_layers:total,
     requested_physique:Math.floor(total/facts.effects['7121'].layers_per_physique),requested_permanent_max_hp:total>=facts.effects['7121'].hp_threshold?1:0,
     applied:false,battle_hp_modified:false,next_battle_allowed:false,training_label_allowed:false}];
   });
  },
  metadata:()=>({evidence_sha256:digest,events:structuredClone(events),pending:players.map(p=>({player_index:states.get(p).index,buff784:states.get(p).pending})),training_label_allowed:false})
 };
}
