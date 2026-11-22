// Additive current-client787 support. Old inactive healing delegates unchanged.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
function factsAt(root) {
  const raw=fs.readFileSync(path.join(root,'data/inspection/current-spirit-outburst-v30.json'));
  if(crypto.createHash('sha256').update(raw).digest('hex')!=='783658033e37aff9f76100add82cbfc30c1fdebedb89a9aab27593f3057a1089')throw new Error('Spirit outburst evidence changed');
  const facts=JSON.parse(raw);
  for(const [p,h] of Object.entries(facts.source_sha256))
    if(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')!==h)
      throw new Error('Spirit outburst source changed:'+p);
  return facts;
}
export function registerSpiritOutburst(root,swogi) {
  const f=factsAt(root).families[0];
  f.cards.forEach((c,i)=>{
    const id=f.runtime_ids[i];
    if(Object.hasOwn(swogi,id))throw new Error('Spirit outburst alias collision');
    swogi[id]=Object.freeze({...swogi['601011'],name:f.engine_name,names:[f.engine_name,c.name],
      qi_cost:0,hp_cost:0,marking:'he',is_add_qi:true,is_continuous:false,is_consumption:false,opening:undefined,
      card_actions:game=>{
        if(typeof game.current_spirit_outburst_gain!=='function')throw new Error('Spirit outburst runtime not installed');
        game.current_spirit_outburst_gain(c.otherParams[1],c.id);
        game.increase_idx_qi(0,c.anima);
        game.increase_idx_hp(0,c.otherParams[0]+game.players[0].qi);
      }});
  });
}
export function installSpiritOutburst(root,game,order=[0,1]) {
  factsAt(root);
  const players=[...game.players],state=new WeakMap(players.map(p=>[p,{remaining:0}]));
  const owner=new Map(players.map((p,i)=>[p,order[i]])),events=[];
  const emit=(p,kind,value)=>events.push({kind,player_index:owner.get(p),...value});
  game.current_spirit_outburst_gain=function(amount,rawId) {
    if(!Number.isSafeInteger(amount)||amount<=0||![4000106,4010106,4020106].includes(rawId))throw new Error('spirit_outburst_unresolved:invalid_duration');
    const p=this.players[0],s=state.get(p),before=s.remaining;
    s.remaining+=amount;
    emit(p,'card_body',{raw_id:rawId,added:amount,before,remaining:s.remaining});
  };
  game.current_spirit_outburst_damage=function(idx,amount) {
    const p=this.players[idx];
    if(state.get(p).remaining<=0)throw new Error('spirit_outburst_unresolved:inactive_damage');
    const enemy=this.players[1-idx],before={hp:enemy.hp,def:enemy.def};
    this.deal_damage_inner(amount,false,idx);
    emit(p,'overflow_damage',{requested:amount,target_index:owner.get(enemy),before,after:{hp:enemy.hp,def:enemy.def}});
  };
  const heal=game.increase_idx_hp.bind(game);
  game.increase_idx_hp=function(idx,amount) {
    if(state.get(this.players[idx]).remaining<=0)return heal(idx,amount);
    if(!Number.isSafeInteger(amount)||amount<0)throw new Error('spirit_outburst_unresolved:invalid_healing');
    return healWithOverflow.call(this,idx,amount);
  };
  // Exact fixed start boundary373 ->787 ->9. A chase never reenters sim_turn.
  let startPlayer=null;
  const reduce=game.reduce_idx_x_by_c.bind(game);
  game.reduce_idx_x_by_c=function(idx,name,amount) {
    const value=reduce(idx,name,amount);
    if(startPlayer===this.players[0]&&idx===0&&name==='god_opportunity_reversal_stacks'&&amount===1) {
      const p=startPlayer;startPlayer=null;
      const s=state.get(p);
      if(s.remaining>0){s.remaining--;emit(p,'owner_turn_start',{remaining:s.remaining});}
    }
    return value;
  };
  const turn=game.sim_turn.bind(game);
  game.sim_turn=function() {
    const previous=startPlayer;startPlayer=this.players[0];
    try{return turn();}finally{startPlayer=previous;}
  };
  return {forPlayer:p=>({...state.get(p)}),metadata:()=>events.length?{
    client_buff:787,events,remaining:players.map(p=>({player_index:owner.get(p),...state.get(p)})),
    training_label_allowed:false}:null};
}
// Pinned shared healing body, with overflow captured at the cap and emitted
// after reversal373, before dream standing firm716. The caller gates787.
function healWithOverflow(idx, amt) {
        const me = this.players[idx];
        let overflow = 0;
        if (amt === 0) {
            return 0;
        }
        amt = amt - me.indigestion;
        amt = amt + me.appetite;
        if (amt <= 0) {
            amt = 1;
        }
        const prev_hp = me.hp;
        if (me.prevent_gain_hp_stacks > 0) {
            this.log("prevented " + amt + " hp gain");
            return 0;
        }
        if (me.got_void_split_speared && me.hp <= 0) {
            this.log("void split spear prevented " + amt + " hp gain");
            return 0;
        }
        if (me.metal_spirit_chokehold_stacks > 0) {
            this.log("refusing to heal a player with metal_spirit_chokehold_stacks");
            return 0;
        }
        if (me.m_metal_spirit_seal_stacks > 0) {
            this.increase_idx_penetrate(idx, amt);
            this.log("M - Metal Spirit Seal: converted " + amt + " HP gain to Penetrate");
            return 0;
        }
        if (me.hp <= 0) return 0; // ordinary healing is not revival
        for (let i=0; i<me.p2_rejuvenation_stacks; i++) {
            this.increase_idx_max_hp(idx, 3);
        }
        for (let i=0; i<me.p3_rejuvenation_stacks; i++) {
            this.increase_idx_max_hp(idx, 4);
        }
        for (let i=0; i<me.p4_rejuvenation_stacks; i++) {
            this.increase_idx_max_hp(idx, 5);
        }
        for (let i=0; i<me.p5_rejuvenation_stacks; i++) {
            this.increase_idx_max_hp(idx, 6);
        }
        if (me.god_opportunity_conform_stacks > 0) {
            amt = Math.ceil(amt * 14 / 10);
        }
        if (me.wild_crossing_seal_stacks > 0 && idx === 0) {
            this.do_wild_crossing_seal_chase();
        }
        me.hp += amt;
        me.hp_gained += amt;
        me.hp_gained_this_turn += amt;
        if (me.hp > me.max_hp) {
            if (me.vitality_blossom_stacks > 0) {
                const exccess_hp = me.hp - me.max_hp;
                this.increase_idx_max_hp(idx, exccess_hp);
            }
            if (me.hp > me.max_hp)
            {
                if (me.vitality_blossom_stacks <= 0) overflow = me.hp - me.max_hp;
                me.hp = me.max_hp;
            }
        }
        if (prev_hp !== me.hp) {
            for (let i=0; i<me.birdie_wind_stacks; i++) {
                this.increase_idx_def(idx, 1);
            }
        }
        this.log("healed " + amt + " hp. Went from " + prev_hp + " to " + me.hp);
        if (me.god_opportunity_reversal_stacks > 0) {
            const dmg_amt = Math.floor(amt / 2);
            if (dmg_amt > 0) {
                this.deal_damage_inner(dmg_amt, false, idx);
            }
        }
        if (overflow > 0) this.current_spirit_outburst_damage(idx, overflow);
        if (me.dream_standing_firm_def_hp_damage_pct > 0 && !me.dream_standing_firm_triggering) {
            me.dream_standing_firm_triggering = 1;
            const dmg = Math.floor(amt * me.dream_standing_firm_def_hp_damage_pct / 100);
            if (dmg > 0) {
                this.deal_damage_inner(dmg, false, idx);
            }
            me.dream_standing_firm_triggering = 0;
        }
    }
