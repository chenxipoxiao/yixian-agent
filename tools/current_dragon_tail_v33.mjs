// Current Dragon Tail. The frozen shared scheduler and healing remain intact.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='9526634c4d4c90d874465560dc4949f0edcfbf2153007975df0f0940998a096a';
const installed=new WeakSet();
const unresolved=why=>{throw new Error('dragon_tail_unresolved:'+why);};
function factsAt(root) {
  const bytes=fs.readFileSync(path.join(root,'data/inspection/current-dragon-tail-v33.json'));
  if(crypto.createHash('sha256').update(bytes).digest('hex')!==digest)throw new Error('Dragon Tail evidence changed');
  const facts=JSON.parse(bytes);
  for(const [p,h] of Object.entries(facts.source_sha256))
    if(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')!==h)throw new Error('Dragon Tail source changed:'+p);
  return facts;
}
export function registerDragonTail(root,swogi) {
  const facts=factsAt(root);
  for(const c of facts.cards) {
    if(Object.hasOwn(swogi,c.runtime_id))throw new Error('Dragon Tail alias collision');
    swogi[c.runtime_id]=Object.freeze({...swogi['122091'],name:'Current Dragon Tail',names:['Current Dragon Tail',c.name],
      qi_cost:0,hp_cost:0,marking:'he',is_continuous:false,is_consumption:false,is_post_action:true,
      is_add_qi:false,opening:undefined,
      card_actions:game=>{
        if(typeof game.current_dragon_tail!=='function')unresolved('runtime_not_installed');
        game.current_dragon_tail(c.raw_id,c.runtime_id,c.heal,c.divisor);
      }});
  }
}
export function installDragonTail(root,game,order=[0,1]) {
  const facts=factsAt(root);
  if(installed.has(game))unresolved('already_installed');
  if(order.length!==2||new Set(order).size!==2||!order.every(i=>i===0||i===1))unresolved('invalid_order');
  const owners=new Map(game.players.map((p,i)=>[p,order[i]])),pending=new WeakMap(),events=[];
  installed.add(game);
  game.current_dragon_tail=function(raw,id,heal,divisor) {
    const c=facts.cards.find(c=>c.raw_id===raw),me=this.players[0],slot=me.currently_playing_card_idx;
    if(!c||c.runtime_id!==id||c.heal!==heal||c.divisor!==divisor)unresolved('invalid_grade');
    // Client temporary CardItem identity must be recovered separately before admitting copies.
    if(me.trigger_depth!==1||!Number.isInteger(slot)||me.cards[slot]!==id)unresolved('temporary_card_identity');
    const first=!me.can_post_action[slot],before={hp:me.hp,def:me.def,healing_this_turn:me.hp_gained_this_turn};
    this.increase_idx_hp(0,heal);
    if(first)pending.set(me,(pending.get(me)??0)+1);
    // CheckHouZhao may itself heal through post-strike; read495 only after it returns.
    const post=this.if_post_action();
    const counted=me.hp_gained_this_turn,defense=post?Math.trunc(counted/divisor):0;
    if(post)this.increase_idx_def(0,defense);
    events.push({kind:'card_body',player_index:owners.get(me),raw_id:raw,slot,first_use:first,
      post_action:post,heal_requested:heal,healing_count:counted,defense_requested:defense,before,
      after:{hp:me.hp,def:me.def,healing_this_turn:me.hp_gained_this_turn}});
  };
  const play=game.play_card.bind(game);
  game.play_card=function(id,slot) {
    const me=this.players[0];
    const result=play(id,slot);
    const count=pending.get(me)??0;
    if(count) {
      const before=me.next_card_index;
      for(let n=0;n<count;n++)this.move_cursor_to_previous_card();
      pending.delete(me);
      events.push({kind:'cursor_after_card',player_index:owners.get(me),count,before,after:me.next_card_index});
    }
    return result;
  };
  return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),
    copied_temporary_identity_supported:false,training_label_allowed:false}:null};
}
