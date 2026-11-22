import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createPaperMixedQueue} from '../tools/current_paper_mixed_queue_v101.mjs';
const facts=JSON.parse(fs.readFileSync('data/inspection/current-paper-mixed-parameters-v101.json','utf8'));
const therapy=facts.cards.find(c=>c.id===4010017),rooster=facts.cards.find(c=>c.id===4000020);
function fixture(stream,owners=[true,false],order=[0,1]){
 const swogi=Object.fromEntries(facts.cards.map(c=>[c.runtime_id,{}]));
 const players=[0,1].map(()=>({hp:100,max_hp:100,def:0,qi:0,weaken:0,hexagram:1,triggered_hexagram_count:0,currently_triggering_card_idx:0}));
 const game={players,used_randomness:false,do_plant_start_permanent_buffs(){},
  trigger_hexagram(){if(this.players[0].hexagram>0){this.players[0].hexagram--;this.players[0].triggered_hexagram_count++;return true;}return false;},
  increase_idx_max_hp(i,n){this.players[i].max_hp+=n;},increase_idx_hp(i,n){this.players[i].hp=Math.min(this.players[i].max_hp,this.players[i].hp+n);},
  increase_idx_def(i,n){this.players[i].def+=n;},increase_idx_debuff(i,k,n){this.players[i][k]=(this.players[i][k]??0)+n;},
  if_post_action(){return false;},just_do_the_card_and_nothing_else(c){if(c===swogi[rooster.runtime_id])return this.if_c_pct(11);}};
 for(const m of facts.blocked_random_entrypoints)if(!game[m])game[m]=()=>{throw new Error('unexpected mock fallback:'+m);};
 const q=createPaperMixedQueue(swogi,game,stream,order,facts,owners);q.installReaders();
 return {q,game,players,play(c){game.players[0].currently_triggering_card_id=c.runtime_id;return game.just_do_the_card_and_nothing_else(swogi[c.runtime_id]);}};
}
const a=fixture([1,22,0]);a.game.do_plant_start_permanent_buffs();
assert.equal(a.players[0].hexagram,1);assert.equal(a.players[0].def,10);
a.play(therapy);assert.equal(a.players[0].hexagram,0);assert.equal(a.play(rooster),true);a.q.verifyTerminal();
assert.deepEqual(a.q.metadata().events.map(e=>[e.type,e.queue_index,e.value,e.forced_by_hexagram]),[['opening_branch',0,1,false],['range',1,22,true],['probability',2,0,false]]);
const b=fixture([2,3],[true,true],[1,0]);b.game.do_plant_start_permanent_buffs();b.game.players.reverse();b.game.do_plant_start_permanent_buffs();b.q.verifyTerminal();
assert.deepEqual(b.q.metadata().events.map(e=>e.player_index),[1,0]);assert.equal(b.q.metadata().pending_match_rewards[0].authoritative_credit_applied,false);
const c=fixture([1,22,0]);assert.throws(()=>c.play(therapy),/card_before_openings/);
const d=fixture([1,21]);d.game.do_plant_start_permanent_buffs();assert.throws(()=>d.play(therapy),/forced_magnitude_mismatch/);
const e=fixture([1,22,0]);e.game.do_plant_start_permanent_buffs();e.play(therapy);assert.throws(()=>e.q.verifyTerminal(),/unused_parameters/);
const f=fixture([1]);f.game.do_plant_start_permanent_buffs();assert.throws(()=>f.play(therapy),/parameter_underflow/);
const g=fixture([1,22]);g.game.do_plant_start_permanent_buffs();assert.throws(()=>g.game.random_int(),/unsupported_consumer/);
