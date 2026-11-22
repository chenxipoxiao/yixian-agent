import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {lightningRepeatFacts,registerLightningRepeat,installLightningRepeat} from '../tools/current_lightning_repeat_v116.mjs';
import {registerHexagramThunder,installHexagramThunder} from '../tools/current_hexagram_thunder_v116.mjs';
import {installCurrentQiPayment} from '../tools/current_qi_payment_v79.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
const {swogi}=await import(pathToFileURL(path.join(process.cwd(),'card_info.js')));
const saved=new Map(Object.entries(swogi)),facts=lightningRepeatFacts(root);registerLightningRepeat(root,swogi);registerHexagramThunder(root,swogi);
for(const [id,c] of saved)assert.equal(swogi[id],c);
assert.throws(()=>registerLightningRepeat(root,swogi),/already_registered/);
const fixture=(id='811601')=>{
 const g=new GameState(undefined,undefined,'lightning-repeat-software');
 for(const p of g.players)Object.assign(p,{character:'he2',hp:500,max_hp:500,qi:20,cards:[id,'125041','601011']});
 installCurrentQiPayment(g);const obs=installLightningRepeat(root,g,swogi,[0,1]);
 g.start_of_game_setup();return {g,obs,p:g.players[0],q:g.players[1]};
};
let scenarios=0;
for(const c of facts.cards){
 const {g,p,obs}=fixture(c.runtime_id);g.play_card(c.runtime_id,0);
 assert.equal(p.hexagram,c.config.guaXiang);assert.equal(p.played_card_count,1);
 assert.equal(obs.metadata().events.length,1);assert.equal(obs.metadata().events[0].pending_after,1);scenarios++;
 const f=fixture(c.runtime_id);f.g.sim_turn();assert.equal(f.p.qi,19);assert.equal(f.p.hexagram,c.config.guaXiang);
 assert.equal(f.p.played_card_count,1);scenarios++;
}
{
 const {g,p}=fixture();p.strike_twice_stacks=1;
 assert.throws(()=>g.play_card('811601',0),/other_repeat_interaction/);assert.equal(p.strike_twice_stacks,1);scenarios++;
}
{
 const {g,p,obs}=fixture();p.trigger_depth=1;g.trigger_card('811601',0);p.trigger_depth=0;
 assert.equal(obs.metadata().events[0].pending_after,1);assert.equal(obs.metadata().events.length,1);
 g.play_card('811601',0);assert.equal(p.hexagram,6);assert.equal(obs.metadata().events[1].pending_after_main,2);scenarios++;
}
{
 const {g,p,obs}=fixture();g.play_card('811601',0);g.play_card('601011',2);
 assert.equal(obs.metadata().events.length,1);assert.equal(p.played_card_count,2);scenarios++;
}
{
 const {g,p,obs}=fixture();g.play_card('811601',0);g.play_card('811601',0);
 assert.equal(p.hexagram,6);assert.equal(p.played_card_count,3);
 const e=obs.metadata().events[1];assert.equal(e.pending_before,1);assert.equal(e.pending_after_repeat,1);assert.equal(e.pending_after_main,2);scenarios++;
}
{
 const {g,p}=fixture();g.play_card('811601',0);p.cards[2]='unknown';
 assert.throws(()=>g.play_card('unknown',2),/unknown_card_name/);scenarios++;
}
{
 const {g,p}=fixture();g.play_card('811601',0);p.ultimate_overcome_formation_stacks=1;
 assert.throws(()=>g.play_card('125041',1),/280_repeat_interaction/);scenarios++;
}
{
 const {g,p}=fixture();p.cards=['767011','811601','601011'];const h=installHexagramThunder(root,g,swogi,[0,1]);
 g.play_card('767011',0);assert.equal(h.metadata().events.find(e=>e.kind==='card_body').as_attack,true);scenarios++;
}
{
 const {g,p,q,obs}=fixture();g.play_card('811601',0);p.hexagram=10;q.hp=1;
 const qi=p.qi;g.play_card('125041',1);
 assert.equal(p.qi,qi);assert.equal(p.played_card_count,3);assert.equal(p.hexagram,0);
 assert.equal(obs.metadata().events[1].pending_after_main,0);assert.ok(q.hp<0);scenarios++;
}
process.stdout.write(JSON.stringify({passed:true,scenarios,scope:'scheduler and grade software checks, not replay acceptance'}));
