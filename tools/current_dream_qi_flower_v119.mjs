import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='3fec2bbb4ff9315b8e28c88acad2ab7ff5602845e475fbc03bffba95e0c93758',cache=new Map(),registered=new WeakSet(),installed=new WeakSet();
const check=(v,m)=>{if(!v)throw new Error('dream_qi_flower_unresolved:'+m);};
export function dreamQiFlowerFacts(root){
 if(cache.has(root))return cache.get(root);
 const b=fs.readFileSync(path.join(root,'data/inspection/current-dream-qi-flower-v119.json'));
 check(crypto.createHash('sha256').update(b).digest('hex')===digest,'evidence_changed');const f=JSON.parse(b);
 for(const [p,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')===h,'source_changed:'+p);
 cache.set(root,f);return f;
}
export function registerDreamQiFlower(root,swogi){
 check(!registered.has(swogi),'already_registered');
 for(const c of dreamQiFlowerFacts(root).cards){
  const p=swogi[c.runtime_id];check(p&&typeof p.card_actions==='function'&&p.qi_cost===0&&(p.hp_cost??0)===0,'native_metadata');
  swogi[c.runtime_id]=Object.freeze({...p,card_actions:g=>g.currentDreamQiFlowerActive?g.executeCurrentDreamQiFlower(c.runtime_id):p.card_actions(g)});
 }
 registered.add(swogi);
}
const snap=p=>Object.fromEntries(['hp','max_hp','qi','increase_atk','next_attack_deals_extra','hp_gained','internal_injury','dream_qi_perfusion_guarantee_injured'].map(k=>[k,p[k]]));
export function installDreamQiFlower(root,game,swogi,order=[0,1]){
 check(!installed.has(game),'already_installed');
 check(order.length===2&&new Set(order).size===2&&order.every(i=>i===0||i===1),'order');
 const f=dreamQiFlowerFacts(root),cards=new Map(f.cards.map(c=>[c.runtime_id,c])),states=new Map(game.players.map((p,i)=>[p,{index:order[i]}])),events=[];
 game.currentDreamQiFlowerActive=game.players.some(p=>p.cards.some(id=>cards.has(id)));
 game.executeCurrentDreamQiFlower=function(id){
  const p=this.players[0],q=this.players[1],c=cards.get(id);
  check(c&&p.currently_triggering_card_id===id,'card_identity');
  const e={kind:'card_body',raw_card_id:c.raw_id,player_index:states.get(p).index,trigger_depth:p.trigger_depth,before:snap(p),opponent_before:snap(q)};events.push(e);
  if(c.kind==='qi'){
   this.increase_idx_qi(0,c.config.anima);this.increase_idx_x_by_c(0,'increase_atk',c.config.otherParams[0]);
  }else{
   this.increase_idx_x_by_c(1,'internal_injury',c.config.otherParams[0]);
   if(c.config.level>3)this.increase_idx_hp(0,c.config.otherParams[1]);
   e.post_action=this.if_post_action();
   if(e.post_action){
    if(c.config.level<=3)this.increase_idx_hp(0,c.config.otherParams[1]);
    else{
     check(Number.isSafeInteger(p.hp_gained)&&p.hp_gained>=0&&p.hp_gained<=2147483647,'313_int32');
     e.counter313=p.hp_gained;
     // C# int division precedes conv.r4 and FloorToInt in the fixed client.
     const n=Math.floor(Math.fround(Math.trunc(p.hp_gained/c.config.otherParams[2])));e.extra_injury=n;
     if(n>0)this.increase_idx_x_by_c(1,'internal_injury',n);
    }
   }
  }
  e.after=snap(p);e.opponent_after=snap(q);
 };
 const adjacent=game.check_adjacent_effects_before_card.bind(game);
 game.check_adjacent_effects_before_card=function(idx,id){
  const p=this.players[0],neighbors=[p.cards[this.get_prev_idx(idx)],p.cards[this.get_next_idx(idx)]],high=neighbors.filter(x=>x==='D11014'||x==='D11015').length;
  const n=neighbors.filter(x=>['D11013','D11014','D11015'].includes(x)).length,result=adjacent(idx,id);
  if(high&&game.currentDreamQiFlowerActive){
   // Native OR already supplied one. v93 supplies the two-low-only case.
   if(n===2)p.dream_qi_perfusion_guarantee_injured++;
   events.push({kind:'adjacent_693',player_index:states.get(p).index,runtime_id:id,trigger_depth:p.trigger_depth,matching_neighbors:n,high_neighbors:high});
  }
  return result;
 };
 installed.add(game);return {metadata:()=>events.length?{evidence_sha256:digest,events:structuredClone(events),recorded_action_log:false,training_label_allowed:false}:null};
}
