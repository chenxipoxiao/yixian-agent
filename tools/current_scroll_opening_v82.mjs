// Battle-only fate198. Acquisition and the authoritative board stay outside.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='4cc90c92b7bba5d2103178a7677cf30c9db6863500a68d1bede2b62b691ca177',cache=new Map(),installed=new WeakSet();
const check=(value,message)=>{if(!value)throw new Error('scroll_opening_unresolved:'+message);};
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
export function scrollOpeningFacts(root){
 if(cache.has(root))return cache.get(root);
 const raw=fs.readFileSync(path.join(root,'data/inspection/current-scroll-opening-v82.json'));
 check(crypto.createHash('sha256').update(raw).digest('hex')===digest,'evidence_changed');const f=JSON.parse(raw);
 for(const [name,h] of Object.entries(f.source_sha256))check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,name))).digest('hex')===h,'source_changed:'+name);
 cache.set(root,f);return f;
}
export function installScrollOpening(root,game,swogi,value,order=[0,1]){
 if(value===undefined)return null;
 check(object(value)&&Object.keys(value).length===1&&Array.isArray(value.players)&&value.players.length===2,'explicit_players_required');
 check(Array.isArray(order)&&order.length===2&&new Set(order).size===2&&order.every(x=>x===0||x===1),'invalid_order');
 check(!installed.has(game),'already_installed');
 const facts=scrollOpeningFacts(root),states=new Map(),events=[];
 game.players.forEach((p,seat)=>{
  const e=value.players[order[seat]];
  check(object(e)&&Object.keys(e).length===3&&Array.isArray(e.fate_ids)&&new Set(e.fate_ids).size===e.fate_ids.length&&e.fate_ids.every(x=>x===198),'invalid_ownership');
  check(Number.isInteger(e.unlocked_slots)&&e.unlocked_slots===p.cards.length&&e.unlocked_slots>=1&&e.unlocked_slots<=8,'invalid_grids');
  check(Array.isArray(e.starting_raw_cards)&&e.starting_raw_cards.length===p.cards.length&&e.starting_raw_cards.every((x,i)=>Number.isSafeInteger(x)&&facts.raw_to_runtime[x]===p.cards[i]),'original_board_mismatch');
  check(p.solitary_void_golden_scroll_fate_stacks===0,'legacy_ownership_conflict');
  states.set(p,{index:order[seat],owns:e.fate_ids.includes(198),opened:false});
 });
 check([...states.values()].some(s=>s.owns),'empty_ownership');
 // Native storage for441/442 is on the opposite player: the audited card
 // bodies and atk reader use that same representation. They request chase.
 for(const id of ['625041','625051'])check(typeof swogi[id]?.card_actions==='function','generated_card_missing');
 const upgrade=game.try_upgrade_card.bind(game);
 game.try_upgrade_card=function(idx,slot){
  if(['625041','625051'].includes(this.players[idx].cards[slot]))return false;
  return upgrade(idx,slot);
 };
 // Native placement occurs inside p5 before remaining ordinary fates. The
 // client places198 after ordinary startup effects and before season startup.
 // Keep the native method dormant and execute once at the end of that stage.
 const setup=game.apply_p5_fates_setup.bind(game);
 game.apply_p5_fates_setup=function(idx){
  const p=this.players[idx],state=states.get(p);
  check(state,'unknown_player');
  if(state.owns)check(!state.opened,'opening_reentered');
  const result=setup(idx);
  if(!state.owns)return result;
  state.opened=true;
  check(p.card_play_direction===1||p.card_play_direction===-1,'unknown_grid_direction');
  const before=[...p.cards],operations=[],n=p.cards.length;
  for(let slot=0;slot<n;slot++){
   if(!['625031','625032','625033'].includes(p.cards[slot]))continue;
   let upgrades=2;
   const prev=(slot+n-p.card_play_direction)%n,next=(slot+n+p.card_play_direction)%n;
   // Inspect current cards, not an empty-slot bitmap saved before other
   // opening effects. Previous placement is visible to the next check.
   for(const [neighbor,id] of [[prev,'625041'],[next,'625051']]){
    if(p.cards[neighbor]==='601011'){
     p.cards[neighbor]=id;upgrades--;operations.push({kind:'place',slot:neighbor,card:id,scroll_slot:slot});
    }
   }
   for(let j=0;j<upgrades;j++){
    const card=p.cards[slot];
    if(card==='625033')break;
    check(card==='625031'||card==='625032','scroll_identity_changed');
    p.cards[slot]=card==='625031'?'625032':'625033';
    operations.push({kind:'upgrade',slot,from:card,to:p.cards[slot]});
   }
  }
  events.push({player_index:state.index,fate_id:198,phase:'ordinary_opening_end',before,after:[...p.cards],operations});
  return result;
 };
 installed.add(game);
 return {metadata:()=>({evidence_sha256:digest,events:structuredClone(events),battle_only:true,acquisition_reward_replayed:false,recorded_action_log:false,training_label_allowed:false})};
}
