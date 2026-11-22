// Current-client ordinary Echo prefix; no upstream or previous-version edits.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
function factsAt(root) {
  const raw=fs.readFileSync(path.join(root,'data/inspection/current-echo-formation-v31.json'));
  if(crypto.createHash('sha256').update(raw).digest('hex')!=='9a399c23570b4ac2b4ed25ac7b37e44e7cc854dd95e22e4c9af4b9a86515a775')throw new Error('Echo formation evidence changed');
  const facts=JSON.parse(raw);
  for(const [p,h] of Object.entries(facts.source_sha256))
    if(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')!==h)
      throw new Error('Echo formation source changed:'+p);
  return facts;
}
const installed=new WeakSet();
export function installCurrentEcho(root,game,order=[0,1]) {
  const facts=factsAt(root);
  if(installed.has(game))throw new Error('Echo formation already installed');
  if(typeof game.do_echo_formation_thing!=='function')throw new Error('Missing native Echo implementation');
  installed.add(game);
  const owner=new Map(game.players.map((p,i)=>[p,order[i]])),events=[];
  const original=game.do_echo_formation_thing.bind(game);
  game.do_echo_formation_thing=function(upgrade) {
    const card=facts.cards.find(c=>c.upgrade_times===upgrade);
    if(!card)throw new Error('echo_formation_unresolved:invalid_grade');
    const p=this.players[0],before={hp:p.hp,max_hp:p.max_hp};
    this.increase_idx_max_hp(0,card.hp_and_max_hp);
    this.increase_idx_hp(0,card.hp_and_max_hp);
    events.push({kind:'card_prefix',player_index:owner.get(p),raw_id:card.raw_id,
      upgrade_times:upgrade,requested:card.hp_and_max_hp,before,before_repeat:{hp:p.hp,max_hp:p.max_hp}});
    return original(upgrade);
  };
  return {metadata:()=>events.length?{events,scope:'ordinary_echo_prefix',training_label_allowed:false}:null};
}
