// Card263 only: return used intent and its bonus together at card cleanup.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const digest='95708e55fe5fab0dd220c33bf81d48310cfaffb9f6ea44b361fbe8c76b4af13e';
const checked=new Map(), installed=new WeakSet();
const check=(ok,why)=>{if(!ok)throw new Error('phantom_flying_fang_v169:'+why);};
const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
function factsAt(root){
  if(checked.has(root))return checked.get(root);
  const bytes=fs.readFileSync(path.join(root,'data/inspection/current-phantom-flying-fang-v169.json'));
  check(hash(bytes)===digest,'evidence_changed');
  const facts=JSON.parse(bytes);
  for(const [p,h] of Object.entries(facts.source_sha256))
    check(hash(fs.readFileSync(path.join(root,p)))===h,'source_changed:'+p);
  checked.set(root,facts);return facts;
}

export function registerPhantomFlyingFang(root,swogi){
  for(const c of factsAt(root).cards){
    check(typeof swogi[c.runtime_id]?.card_actions==='function','card_missing:'+c.runtime_id);
    check(c.config.attackCount===1&&c.config.actionAgain===true,'card_contract');
    swogi[c.runtime_id]=Object.freeze({...swogi[c.runtime_id],card_actions:g=>{
      check(typeof g.current_phantom_flying_fang_v169==='function','handler_required');
      return g.current_phantom_flying_fang_v169(c.runtime_id);
    }});
  }
}

export function installPhantomFlyingFang(root,game,order){
  check(!installed.has(game),'already_installed');
  check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(x=>x===0||x===1),'order');
  const byId=new Map(factsAt(root).cards.map(c=>[c.runtime_id,c]));
  const seats=new Map(game.players.map((p,i)=>[p,order[i]])),events=[];
  game.current_phantom_flying_fang_v169=function(id){
    const c=byId.get(id),p=this.players[0];
    check(c&&p.currently_triggering_card_id===id,'active_card_identity');
    const before=p.sword_intent;
    this.atk(c.config.attack);
    const used=p.sword_intent_to_lose;
    check(Number.isSafeInteger(used)&&used>=0,'used_intent_marker');
    const priorRefund=p.sword_intent_to_regain;
    check(Number.isSafeInteger(priorRefund)&&priorRefund>=0,'refund_marker');
    if(used>0){
      this.regain_sword_intent();
      // Native cleanup already consumes/protects the used intent before refund.
      // Queue the478 bonus with307; do not trigger intent-gain hooks in the body.
      p.sword_intent_to_regain+=c.config.otherParams[0];
    }
    this.chase();
    events.push({player_index:seats.get(p),raw_id:c.raw_id,slot:p.currently_triggering_card_idx,
      trigger_depth:p.trigger_depth,intent_before_attack:before,used_intent:used,
      refund_before:priorRefund,refund_queued:p.sword_intent_to_regain,
      extra_intent_queued:used>0?c.config.otherParams[0]:0,
      intent_after_body:p.sword_intent,bonus_phase:'card_cleanup'});
  };
  installed.add(game);
  return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),
    current_server_verified:false,training_label_allowed:false}:null};
}
