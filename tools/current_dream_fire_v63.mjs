// Reuse pinned native dream bodies and successful-chase callbacks. New slash
// preserves maxHP-before-HP; a hidden dream's grade is never an upgrade level.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='2be2802df323d4c925226bb94d8aecc4e05928be883fa8042311a8f05deba11f',cache=new Map(),installed=new WeakSet(),openInstalled=new WeakSet();
const check=(ok,reason)=>{if(!ok)throw new Error('dream_fire_unresolved:'+reason);};
function factsAt(root){
 if(cache.has(root))return cache.get(root);
 const b=fs.readFileSync(path.join(root,'data/inspection/current-dream-fire-v63.json'));
 check(crypto.createHash('sha256').update(b).digest('hex')===digest,'evidence_changed');const f=JSON.parse(b);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,f);return f;
}
export function registerDreamFire(root,swogi){
 for(const c of factsAt(root).cards){
  if(c.raw_id>=7000090){
   const card=swogi[c.runtime_id];
   check(card?.name==='Dream - Fire Spirit Formation'&&typeof card.card_actions==='function'&&card.qi_cost===0&&c.config.hidden&&c.config.noUpgrade,'native_dream_binding');
   continue;
  }
  check(!Object.hasOwn(swogi,c.runtime_id),'alias_collision');
  swogi[c.runtime_id]=Object.freeze({...swogi['601011'],name:c.config.name,names:[c.config.name],marking:'no_marking',
   qi_cost:0,hp_cost:0,opening:undefined,is_fire_spirit:true,is_sword:false,is_spirit_sword:false,
   is_cloud_sword:false,is_spirit_seal_or_formation:false,is_continuous:false,is_consumption:false,
   card_actions:g=>{
    const me=g.players[0],other=g.players[1],n=other.times_max_hp_reduced;
    check(Number.isSafeInteger(n)&&n>=0,'invalid_max_hp_reduction_count');
    g.atk(c.config.attack+c.config.otherParams[0]*n);
    if(g.if_fire_spirit()){
     const hit=me.damage_dealt_to_hp_by_this_card_atk;
     check(Number.isSafeInteger(hit)&&hit>=0,'invalid_card_hp_damage');
     const amount=Math.floor(hit/c.config.otherParams[1]);
     if(amount>0){g.reduce_idx_max_hp(1,amount);g.reduce_idx_hp(1,amount);}
    }
   }});
 }
}
export function usesDreamFlag(root,value){
 if(value===undefined)return false;
 const f=factsAt(root);
 return Array.isArray(value?.hands)&&value.hands.some(h=>Array.isArray(h)&&f.cards.some(c=>c.raw_id>=7000090&&h.find(raw=>f.hand_metadata[raw]?.kind==='formation')===c.raw_id));
}
const snap=(g,p)=>({hp:p.hp,max_hp:p.max_hp,def:p.def,fire:p.activate_fire_spirit_stacks,dream_fire:p.dream_fire_formation_stacks,
 opponent_hp:g.players[1].hp,opponent_max_hp:g.players[1].max_hp,opponent_reductions:g.players[1].times_max_hp_reduced});
export function installDreamFire(root,game,swogi,order=[0,1]){
 check(!installed.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(x=>x===0||x===1),'invalid_order');
 const f=factsAt(root),byId=new Map(f.cards.map(c=>[c.runtime_id,c])),seats=new Map(game.players.map((p,i)=>[p,order[i]])),events=[];
 const body=game.just_do_the_card_and_nothing_else.bind(game);
 game.just_do_the_card_and_nothing_else=function(card){
  const p=this.players[0],id=p.currently_triggering_card_id,c=byId.get(id);
  if(!c)return body(card);
  check(card===swogi[id],'card_identity');
  const event={player_index:seats.get(p),raw_id:c.raw_id,runtime_id:id,slot:p.currently_triggering_card_idx,trigger_depth:p.trigger_depth,before:snap(this,p)};
  events.push(event);const r=body(card);event.after=snap(this,p);return r;
 };
 installed.add(game);
 return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),recorded_action_log:false,training_label_allowed:false}:null};
}
export function installSeasonStarOpening(root,game,value,order=[0,1]){
 if(value===undefined)return null;
 factsAt(root);check(!openInstalled.has(game),'opening_already_installed');
 check(value&&Object.keys(value).length===1&&Array.isArray(value.players)&&value.players.length===2
  &&value.players.every(a=>Array.isArray(a)&&(a.length===0||a.length===1&&a[0]===11002))&&value.players.some(a=>a.length),'explicit11002_owners_required');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(x=>x===0||x===1),'invalid_order');
 const states=new Map(game.players.map((p,i)=>[p,{index:order[i],owned:value.players[order[i]].length===1,opened:false}])),events=[];
 const previous=game.do_plant_start_permanent_buffs.bind(game);
 game.do_plant_start_permanent_buffs=function(...args){
  const p=this.players[0],s=states.get(p);
  if(s.owned&&!s.opened){
   check(Array.isArray(p.is_star_point)&&p.is_star_point.every(x=>typeof x==='boolean'),'explicit_star_grid_required');s.opened=true;
   const before={hexagram:p.hexagram,star_power:p.star_power,qi:p.qi,stars:[...p.is_star_point]};
   this.increase_idx_x_by_c(0,'hexagram',1);
   const added=[];for(let i=2;i<8;i++)if(p.is_star_point[i]!==true){p.is_star_point[i]=true;added.push(i);}
   events.push({strategy_id:11002,player_index:s.index,phase:'owner_season_opening_after7112',before,added,
    after:{hexagram:p.hexagram,star_power:p.star_power,qi:p.qi,stars:[...p.is_star_point]}});
  }
  return previous(...args);
 };
 openInstalled.add(game);
 return {metadata:()=>({evidence_sha256:digest,events:structuredClone(events),acquisition_rewards_reapplied:false,training_label_allowed:false})};
}
