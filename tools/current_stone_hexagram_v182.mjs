// Versioned current-client parameters for Card175 and Card11000014.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='0150352c21a3f3b084ba082edc445b53d7637c21e72b73c4349d24422c628f5e',registered=new WeakSet(),games=new WeakMap();
const check=(ok,why)=>{if(!ok)throw new Error('stone_hexagram_v182:'+why);};
const int32=n=>Number.isInteger(n)&&n>=-2147483648&&n<=2147483647;
export function registerStoneHexagram(root,swogi){
 check(!registered.has(swogi),'already_registered');
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-stone-hexagram-v182.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');
 const facts=JSON.parse(raw);
 for(const [p,h] of Object.entries(facts.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 for(const c of facts.cards){
  const cfg=c.config,old=swogi[c.runtime_id];
  check(old&&typeof old.card_actions==='function','missing_card_identity');
  check((old.hp_cost===undefined?0:old.hp_cost)===cfg.hpCost,'hp_cost_mismatch');
  if(c.raw_id===175){
   check(cfg.cardType===1&&old.qi_cost===-cfg.anima&&old.gather_qi===cfg.chargeQi,'stone_cost_or_type_mismatch');
   swogi[c.runtime_id]={...old,is_consumption:true,card_actions:g=>{
    const state=games.get(g),p=g.players[0];check(state&&state.seats.has(p),'observer_required');
    check(p.currently_triggering_card_id===c.runtime_id,'actual_card_identity_required');
    check(Number.isInteger(p.trigger_depth)&&p.trigger_depth>=1,'invalid_trigger_depth');
    const slot=p.currently_playing_card_idx,hp=p.hp,max=p.max_hp;
    g.add_c_of_x(cfg.otherParams[0],'max_hp');
    g.add_c_of_x(cfg.otherParams[0],'hp');
    g.add_c_of_x(cfg.otherParams[1],'nuwa_stone_stacks');
    g.consumption();
    state.events.push({kind:'stone_card',player_index:state.seats.get(p),raw_id:c.raw_id,runtime_id:c.runtime_id,
     slot,trigger_depth:p.trigger_depth,hp_before:hp,max_hp_before:max,hp_after:p.hp,max_hp_after:p.max_hp,
     next_owner_turn_stacks:p.nuwa_stone_stacks,outer_slot_consumed:p.trigger_depth===1&&!p.can_play[slot]});
   }};
  }else{
   check(cfg.cardType===0&&cfg.anima===0&&old.qi_cost===0&&cfg.otherParams[1]===6,'hexagram_config_mismatch');
   swogi[c.runtime_id]={...old,opening:[['def',cfg.otherParams[2]]],card_actions:g=>{
    const state=games.get(g),p=g.players[0];check(state&&state.seats.has(p),'observer_required');
    check(p.currently_triggering_card_id===c.runtime_id,'actual_card_identity_required');
    const before=p.def;
    g.increase_idx_def(0,cfg.def);
    g.add_enemy_c_of_x(cfg.otherParams[0],'nothing_is_appropriate_stacks');
    state.events.push({kind:'hexagram_card',player_index:state.seats.get(p),raw_id:c.raw_id,runtime_id:c.runtime_id,
     defense_before:before,defense_after:p.def,base_defense:cfg.def,stacks_added:cfg.otherParams[0],attack_reduction:cfg.otherParams[1]});
   }};
  }
 }
 registered.add(swogi);
}
export function installStoneHexagram(game,order){
 check(!games.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'invalid_order');
 const state={seats:new Map(game.players.map((p,i)=>[p,order[i]])),events:[]};games.set(game,state);
 const previous=game.do_nuwa_stone;
 check(typeof previous==='function','missing_owner_turn_handler');
 game.do_nuwa_stone=function(){
  const p=this.players[0],n=p.nuwa_stone_stacks;
  // Runtime zero represents absence; this does not import a missing replay buff as zero.
  if(n===0)return;
  check(int32(n)&&n>0&&int32(p.hp)&&p.hp>=0,'unsupported_stone_owner_turn_state');
  const hp=p.hp;
  this.heal(hp);
  this.reduce_c_of_x(1,'nuwa_stone_stacks');
  state.events.push({kind:'stone_owner_turn',player_index:state.seats.get(p),raw_id:175,runtime_id:'906011',
   hp_before:hp,requested_healing:hp,hp_after:p.hp,stacks_before:n,stacks_after:p.nuwa_stone_stacks});
 };
 return {metadata:()=>state.events.length?{evidence_sha256:digest,events:structuredClone(state.events),training_label_allowed:false}:null};
}
