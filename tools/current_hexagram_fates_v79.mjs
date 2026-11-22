//195 marker lifecycle and197 original-board condition. No acquisition rewards.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='8b72242479a1b7748b2b873af020d7b8e15859ddb2578f63119dc06fce5f4b1e',cache=new Map(),installed=new WeakSet(),registered=new WeakSet();
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const check=(v,m)=>{if(!v)throw new Error('hexagram_fates_unresolved:'+m);};
export function hexagramFatesFacts(root){
 if(cache.has(root))return cache.get(root);
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-hexagram-fates-v79.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');const f=JSON.parse(raw);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,f);return f;
}
export function registerHexagramFates(root,swogi){
 if(registered.has(swogi))return;
 for(const c of hexagramFatesFacts(root).cards){
  check(typeof swogi[c.runtime_id]?.card_actions==='function','missing_base_card');
  const before=swogi[c.runtime_id].card_actions;
  swogi[c.runtime_id]={...swogi[c.runtime_id],card_actions:g=>{
   if(g.current_hexagram_fates_card?.(c.runtime_id)===true)return;
   return before(g);
  }};
 }
 registered.add(swogi);
}
export function installHexagramFates(root,game,swogi,value,order=[0,1]){
 if(value===undefined)return null;
 check(object(value)&&Object.keys(value).length===1&&Array.isArray(value.players)&&value.players.length===2,'explicit_players_required');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(x=>x===0||x===1),'invalid_order');
 check(!installed.has(game),'already_installed');
 const f=hexagramFatesFacts(root),cards=new Map(f.cards.map(c=>[c.runtime_id,c])),hexRaw=new Set(f.cards.map(c=>c.raw_id));
 const states=new Map();
 game.players.forEach((p,seat)=>{
  const e=value.players[order[seat]];
  check(object(e)&&Object.keys(e).length===2&&Object.hasOwn(e,'fate_ids')&&Object.hasOwn(e,'starting_raw_cards'),'invalid_entry');
  check(Array.isArray(e.fate_ids)&&new Set(e.fate_ids).size===e.fate_ids.length&&e.fate_ids.every(x=>[195,197].includes(x)),'invalid_ownership');
  check(Array.isArray(e.starting_raw_cards)&&e.starting_raw_cards.length===p.cards.length&&e.starting_raw_cards.every((x,i)=>Number.isSafeInteger(x)&&Object.hasOwn(f.raw_to_runtime,x)&&f.raw_to_runtime[x]===p.cards[i]),'starting_mapping_mismatch');
  check(p.spirit_hexagram_evolves_stacks===0&&!p.spirit_hexagram_evolves_triggered&&p.hexagrams_explain_stacks===0,'legacy_fate_state_conflict');
  const count=e.starting_raw_cards.filter(x=>hexRaw.has(x)).length;
  states.set(p,{index:order[seat],ids:new Set(e.fate_ids),count,explain:e.fate_ids.includes(197)&&count===2,pending439:false});
 });
 check([...states.values()].some(s=>s.ids.size),'empty_ownership');
 const events=[],snap=p=>({hp:p.hp,max_hp:p.max_hp,qi:p.qi,hexagram:p.hexagram,def:p.def,weaken:p.weaken,flaw:p.flaw,internal_injury:p.internal_injury});
 game.current_hexagram_fates_qi_gain=function(idx,amount){
  check([0,1].includes(idx)&&Number.isSafeInteger(amount),'invalid_qi_callback');
  const p=this.players[idx],s=states.get(p);
  if(amount<=0||!s.ids.has(195)||s.pending439)return;
  s.pending439=true;events.push({fate_id:195,phase:'positive_qi_add439',player_index:s.index,active_player_index:states.get(this.players[0]).index,amount});
 };
 game.current_hexagram_fates_turn_end=function(){
  const p=this.players[0],s=states.get(p);if(!s.pending439)return;
  const e={fate_id:195,phase:'owner_turn_end_add_hexagram_then_remove439',player_index:s.index,before:snap(p)};events.push(e);
  this.increase_idx_hexagram(0,1);
  // Keep439 present throughout gain callbacks, then remove it, as client does.
  s.pending439=false;e.after=snap(p);
 };
 game.current_hexagram_fates_card=function(id){
  const p=this.players[0],q=this.players[1],s=states.get(p);if(!s.explain)return false;
  const c=cards.get(id);check(c,'unknown_hexagram_card');
  const e={fate_id:197,phase:'qualified_card_body',player_index:s.index,raw_id:c.raw_id,base_id:c.base_id,qualifying_start_count:s.count,before:snap(p),target_before:snap(q)};events.push(e);
  const a=c.config;
  switch(c.base_id){
   case 4000001:this.increase_idx_qi(0,a.anima);this.increase_idx_hexagram(0,a.guaXiang);this.increase_idx_qi(0,4);break;
   case 4000002:this.increase_idx_def(0,a.def);this.increase_idx_hexagram(0,a.guaXiang);this.increase_idx_debuff(1,'weaken',2);break;
   case 4000003:this.atk(a.attack);this.increase_idx_hexagram(0,a.guaXiang);this.increase_idx_debuff(1,'flaw',4);break;
   case 4000015:{
    this.increase_idx_hexagram(0,a.guaXiang);
    // CardItem.gridNumber is the currently triggered physical slot, including
    // temporary calls; the ordinary playing slot may differ for nested cards.
    let slot=p.currently_triggering_card_idx;
    check(Number.isInteger(slot)&&slot>=0&&slot<p.cards.length,'physical_grid_required');e.star_slots=[];
    for(let i=0;i<a.otherParams[0]+4;i++){slot=this.get_next_idx(slot);e.star_slots.push(slot);this.become_idx_star_point(0,slot);}break;
   }
   case 4000016:this.increase_idx_hexagram(0,a.guaXiang);this.increase_idx_max_hp(0,a.otherParams[0]);this.increase_idx_hp(0,a.otherParams[0]);this.increase_idx_max_hp(0,10);this.increase_idx_hp(0,10);break;
   case 4000025:this.increase_idx_hexagram(0,a.guaXiang);this.increase_idx_qi(0,a.otherParams[0]);this.increase_idx_qi(1,a.otherParams[0]);this.increase_idx_debuff(1,'internal_injury',3);break;
   case 4000026:this.increase_idx_qi(0,a.anima);this.increase_idx_hexagram(0,a.guaXiang);this.chase();e.chase_requested=true;break;
   case 4000034:this.increase_idx_hexagram(0,a.guaXiang);this.reduce_enemy_hp(a.otherParams[0]);this.reduce_enemy_max_hp(a.otherParams[0]);this.increase_idx_hexagram(0,1);break;
   default:check(false,'unknown_hexagram_base');
  }
  e.after=snap(p);e.target_after=snap(q);return true;
 };
 installed.add(game);
 return {metadata:()=>({evidence_sha256:digest,events:structuredClone(events),players:[...states.values()].map(s=>({player_index:s.index,fate_ids:[...s.ids],qualifying_start_count:s.count,explain_active:s.explain,pending439:s.pending439})),recorded_action_log:false,training_label_allowed:false})};
}
