// Owner-scoped extensions of the pinned reference callbacks. No old owner path
// is replaced; source-derived timing is verified separately from replay endpoints.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {FIST_STANCE} from '../external/yisim/card_info.js';
const digest='ec3a1caec911fe34999fbb27742a52c6cc4261143db9e953bb54d58716e53fa1',cache=new Map(),installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('character_passives_unresolved:'+why);};
const fields=['internal_injury','weaken','flaw','decrease_atk','entangle','wound','styx','indigestion'];
function factsAt(root){
 if(cache.has(root))return cache.get(root);
 const b=fs.readFileSync(path.join(root,'data/inspection/current-character-passives-v64.json'));
 check(crypto.createHash('sha256').update(b).digest('hex')===digest,'evidence_changed');const f=JSON.parse(b);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,f);return f;
}
export function registerCharacterPassives(root,swogi){
 for(const c of factsAt(root).cards){
  check(!Object.hasOwn(swogi,c.runtime_id),'alias_collision');
  swogi[c.runtime_id]=Object.freeze({...swogi['601011'],name:c.config.name,names:[c.config.name],marking:'dx',
   qi_cost:0,hp_cost:c.config.hpCost,is_add_qi:c.base_id===416,opening:undefined,
   is_sword:false,is_spirit_sword:false,is_cloud_sword:false,is_spirit_seal_or_formation:false,
   is_continuous:c.config.cardType===3,is_consumption:false,
   card_actions:g=>{
    if(c.base_id===415)g.increase_idx_debuff(0,'styx',c.config.otherParams[0]);
    else if(c.base_id===416){
     g.increase_idx_qi(0,c.config.anima);g.increase_idx_x_by_c(0,'agility',c.config.otherParams[1]);
     g.add_current_lingxuan_762(c.config.otherParams[0]);g.continuous();
    }else{
     g.increase_idx_x_by_c(0,'agility',c.config.otherParams[0]);
     g.increase_idx_x_by_c(0,'overwhelming_power_stacks',c.config.otherParams[1]);g.continuous();
    }
   }});
 }
}
const snap=p=>Object.fromEntries(['hp','max_hp','physique','max_physique','qi','agility','force','def','overwhelming_power_stacks',...fields].map(k=>[k,p[k]]));
export function installCharacterPassives(root,game,swogi,order=[0,1]){
 check(!installed.has(game),'already_installed');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(x=>x===0||x===1),'invalid_order');
 const f=factsAt(root),byId=new Map(f.cards.map(c=>[c.runtime_id,c]));
 const seats=new Map(game.players.map((p,i)=>[p,order[i]])),state=new Map(game.players.map(p=>[p,{lingxuan:0}])),events=[];
 const owns=(p,id)=>p.cards.some(c=>byId.get(c)?.base_id===id);
 const physique=(g,idx,x,amount)=>{
  if(amount===0||!owns(g.players[idx],415))return;
  check(fields.includes(x)&&Number.isSafeInteger(amount)&&amount>0,'invalid_debuff_delta');
  const p=g.players[idx],e={kind:'415_debuff_change',player_index:seats.get(p),field:x,actual_layers:amount,before:snap(p)};
  events.push(e);g.increase_idx_physique(idx,amount);e.after=snap(p);
 };
 const increase=game.increase_idx_debuff.bind(game);
 game.increase_idx_debuff=function(idx,x,amt){
  if(!owns(this.players[idx],415))return increase(idx,x,amt);
  return gainDebuff.call(this,idx,x,amt,physique);
 };
 const reduce=game.reduce_idx_x_by_c.bind(game);
 game.reduce_idx_x_by_c=function(idx,x,c){
  const p=this.players[idx];
  if(!owns(p,415)||!fields.includes(x))return reduce(idx,x,c);
  check(Number.isSafeInteger(c)&&c>=0&&Number.isSafeInteger(p[x])&&p[x]>=0,'invalid_debuff_removal');
  const amount=Math.min(c,p[x]);if(!amount)return;
  p[x]-=amount;if(idx===0)p.total_debuff_lost+=amount;
  if(x==='flaw'&&p.drunken_fist_stance_stacks>0)this.increase_idx_x_by_c(idx,'increase_atk',amount*p.drunken_fist_stance_stacks);
  physique(this,idx,x,amount);
  if(x==='styx'){
   if(p.character==='dx3')this.increase_idx_hp(idx,amount*3);
   else this.reduce_idx_hp(idx,amount*3,false);
  }
  this.log('lost '+amount+' '+x+'. Now have '+p[x]+' '+x);
 };
 const force=game.reduce_idx_force.bind(game);
 game.reduce_idx_force=function(idx,amt){
  const p=this.players[idx];if(!owns(p,418))return force(idx,amt);
  check(Number.isSafeInteger(amt)&&amt>=0,'invalid_force_removal');
  const amount=Math.min(amt,p.force);if(!amount)return;
  p.force-=amount;if(idx===0)p.total_force_lost+=amount;
  // Client353 refills at ModifyBuffValue0x794, before362 at0xfec.
  if(p.force===0&&p.endless_force_stacks>0)this.increase_idx_force(idx,p.endless_force_stacks);
  if(p.overwhelming_power_stacks>0)this.deal_damage_inner(amount*p.overwhelming_power_stacks,false,idx);
  this.log('lost '+amount+' force. Now have '+p.force+' force');
 };
 game.add_current_lingxuan_762=function(n){
  check(Number.isSafeInteger(n)&&n>0,'invalid762_gain');state.get(this.players[0]).lingxuan+=n;
 };
 // OnAfterExecuted0x36c skips these callbacks for temporary cards. Reuse the
 // outer extra-attack zone, after crash cleanup and fierce-attack, before377/378.
 const avoid=game.do_god_luck_avoid.bind(game),approach=game.do_god_luck_approach.bind(game);
 const active=p=>owns(p,416)||state.get(p).lingxuan>0;
 game.do_god_luck_avoid=function(card){if(!active(this.players[0]))return avoid(card);};
 game.do_god_luck_approach=function(card){
  const p=this.players[0],s=state.get(p);
  if(active(p)&&p.trigger_depth===1){
   if(s.lingxuan>0){
    const count=fields.reduce((n,k)=>{check(Number.isSafeInteger(p[k])&&p[k]>=0,'invalid_debuff_count');return n+p[k];},0);
    const amount=s.lingxuan+Math.floor(count/2),e={kind:'762_after_card',player_index:seats.get(p),runtime_id:card,stacks:s.lingxuan,debuff_layers:count,base_attack:amount,trigger_depth:p.trigger_depth,before:snap(p)};
    events.push(e);this.atk(amount,true);e.after=snap(p);
   }
   avoid(card);
  }
  return approach(card);
 };
 const body=game.just_do_the_card_and_nothing_else.bind(game);
 game.just_do_the_card_and_nothing_else=function(card){
  const p=this.players[0],id=p.currently_triggering_card_id,c=byId.get(id);
  if(!c)return body(card);check(card===swogi[id],'card_identity');
  const e={kind:'card_body',player_index:seats.get(p),raw_id:c.raw_id,runtime_id:id,trigger_depth:p.trigger_depth,before:snap(p)};
  events.push(e);const r=body(card);e.after=snap(p);e.lingxuan_stacks=state.get(p).lingxuan;return r;
 };
 installed.add(game);
 return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),recorded_action_log:false,training_label_allowed:false}:null};
}

function gainDebuff(idx, x, amt, physique) {
        if (amt === 0) {
            return;
        }
        const me = this.players[idx];
        if (x !== "styx")
        {
            amt += me.gain_extra_debuff;
            me.gain_extra_debuff = 0;
        }
        if (me.m_flower_sentient_stacks > 0 && x === "internal_injury") {
            amt += 2;
        }
        if (me.snake_shadow > 0 && (x === "internal_injury" || x === "wound")) {
            amt += me.snake_shadow;
        }
        if (me.indomitable_will_stacks > 0) {
            if (me.stance === FIST_STANCE) {
                if (x === "wound") {
                    amt -= 1;
                }
            } else {
                if (x === "decrease_atk") {
                    amt -= 1;
                }
            }
        }
        if (me.fresh_fruit_zongzi_stacks > 0 &&
            (x === "internal_injury" || x === "indigestion")) {
            this.reduce_idx_x_by_c(idx, "fresh_fruit_zongzi_stacks", 1);
            this.increase_idx_x_by_c(idx, "regen", amt);
            return;
        }
        if (amt <= 0) {
            return;
        }
        const to_sub = Math.min(amt, me.hexproof);
        if (to_sub > 0) {
            this.reduce_idx_x_by_c(idx, "hexproof", to_sub);
            amt -= to_sub;
        }
        if (amt === 0) {
            return;
        }
        me[x] += amt;
        this.log("gained " + amt + " " + x + ". Now have " + me[x] + " " + x);
        for (let i=0; i<me.unwavering_soul_stacks; i++) {
            this.increase_idx_hp(idx, amt);
        }
        if (me.mystic_snowdrop_stacks > 0) {
            this.reduce_idx_x_by_c(idx, "mystic_snowdrop_stacks", 1);
            this.increase_idx_x_by_c(1 - idx, x, amt);
        }
        if (idx === 0
            && me.dream_elusive_footwork_stacks > 0
            && me.dream_elusive_footwork_trigger_count < me.dream_elusive_footwork_stacks) {
            me.dream_elusive_footwork_trigger_count += 1;
            const reflect_amt = Math.min(amt, me.dream_elusive_footwork_reflect_cap);
            this.increase_idx_debuff(1, x, reflect_amt);
        }
        if (me.m_ruthless_water_stacks > 0
            && x !== "internal_injury"
            && x !== "styx"
        ) {
            const ii_amt = amt * me.m_ruthless_water_stacks;
            this.increase_idx_x_by_c(idx, "internal_injury", ii_amt);
        }
        physique(this,idx,x,amt);
        if (x === "styx") {
            if (me.character === "dx3") {
                this.increase_idx_hp(idx, amt * 3);
            } else {
                this.reduce_idx_hp(idx, amt * 3, false);
            }
        }
    }

