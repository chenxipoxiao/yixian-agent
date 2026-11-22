// Only the explicit current-season7065 agility threshold changes.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export function installCurrentFullMoon(root, game, value, order) {
  if(value===undefined)return;
  const valid=value!==null && typeof value==='object' && !Array.isArray(value)
    && Object.keys(value).length===1 && Array.isArray(value.players)
    && value.players.length===2 && value.players.every(ids=>Array.isArray(ids)
      && ids.length<=1 && ids.every(id=>id===7065));
  if(!valid)throw new Error('Explicit Full Moon ownership required');
  if(!Array.isArray(order)||order.length!==2||![[0,1],[1,0]].some(p=>p.every((v,i)=>v===order[i])))
    throw new Error('Explicit player order required');
  const raw=fs.readFileSync(path.join(root,'data/inspection/current-full-moon-v24.json'));
  if(crypto.createHash('sha256').update(raw).digest('hex')!=='58c7c9b199ba8dd5fea4c9cfad88c059ba9de43ecf4985ccb74ad4ddb7cc5deb')throw new Error('Full Moon evidence changed');
  const facts=JSON.parse(raw);
  for(const [p,h] of Object.entries(facts.source_sha256)) {
    if(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')!==h)
      throw new Error('Full Moon source changed:'+p);
  }
  const owners=new Set(game.players.filter((p,i)=>value.players[order[i]].includes(7065)));
  const native=game.process_this_card_chases.bind(game);
  game.process_this_card_chases=function() {
    const p=this.players[0];
    // The native dream-tune branch has priority over agility. Leave that branch
    // to native handling; no state is temporarily inflated to force a chase.
    if(owners.has(p) && p.this_card_chases<=0 && p.dream_craze_dance_tune_stacks<=0
        && p.chases<p.max_chases && p.agility>=9) {
      p.this_card_chases+=1;
      p.agility-=9;
      this.log('Spent 9 agility to chase. Agility is now '+p.agility);
    }
    return native();
  };
}
