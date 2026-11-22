import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installCurrentEngravings} from '../tools/current_engraving_effects_v18.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
let checked=0;
function fresh(effects,fields={},enemy={}) {
 const g=new GameState(undefined,undefined,'boundary-v18');
 Object.assign(g.players[0],{cards:['601011','601011','601011'],hp:50,max_hp:100,qi:0,def:0},fields);
 Object.assign(g.players[1],{cards:['601011'],hp:1000,max_hp:1000,qi:0,def:0},enemy);
 const ledger=installCurrentEngravings(root,g,{players:[effects,[]]},[0,1]);
 return [g,ledger];
}
// Trigger at selected slot before the card action; repeat cycles do not repeat it.
for(const slot of [0,1,2,7]) {
 const [g,l]=fresh([{strategy_id:13009,slot}]);
 for(let pass=0;pass<2;pass++)for(let i=0;i<3;i++)g.play_card_inner('601011',i);
 assert.equal(g.players[0].def,slot<3?6:0);
 assert.equal(g.players[0].moon_water_sword_formation_stacks,slot<3?2:0);
 assert.equal(l.forPlayer(g.players[0])[0].used,slot<3);checked++;
}
// Positive existing sword intent is read after the +2; ordinary damage is not
// multiplied by attack buffs and does not itself consume sword intent.
for(const intent of [0,1,2,7]) {
 const [g,l]=fresh([{strategy_id:13016,slot:0}],{sword_intent:intent,increase_atk:20});
 const actions=[],damage=g.deal_damage.bind(g),body=g.just_do_the_card_and_nothing_else.bind(g);
 g.deal_damage=n=>{actions.push(['ordinary',n,g.players[0].sword_intent]);return damage(n);};
 g.just_do_the_card_and_nothing_else=c=>{actions.push(['body',g.players[0].sword_intent]);return body(c);};
 g.play_card_inner('601011',0);
 assert.deepEqual(actions,[['ordinary',Math.trunc((intent+2)/2),intent+2],['body',intent+2]]);
 assert.equal(g.players[0].sword_intent,0);assert.equal(l.forPlayer(g.players[0])[0].used,true);checked++;
}
// This marker represents prior real use, even if no fresh effect-use record was
// created. Temporary nested executions never consume a slot's first real use.
{
 const [g,l]=fresh([{strategy_id:13009,slot:1}]);g.players[0].trigger_depth=1;
 g.trigger_card('601011',1);g.players[0].trigger_depth=0;
 assert.equal(g.players[0].def,0);assert.equal(l.forPlayer(g.players[0])[0].used,false);
 g.play_card_inner('601011',1);assert.equal(g.players[0].def,6);checked++;
}
{
 const [g,l]=fresh([{strategy_id:13009,slot:0}]);g.players[0].can_post_action[0]=true;
 g.play_card_inner('601011',0);assert.equal(g.players[0].def,0);assert.equal(l.forPlayer(g.players[0])[0].used,false);checked++;
}
{
 const [g,l]=fresh([{strategy_id:13009,slot:0}],{strike_twice_stacks:1});g.play_card('601011',0);
 assert.equal(g.players[0].def,6);assert.equal(g.players[0].moon_water_sword_formation_stacks,2);checked++;
}
// Defense is granted before the water-moon charges and before the card body.
// Water-moon suppresses the next two own-turn defense decays, not damage.
{
 const [g]=fresh([{strategy_id:13009,slot:0}]);const calls=[];
 const def=g.increase_idx_def.bind(g),add=g.add_c_of_x.bind(g),body=g.just_do_the_card_and_nothing_else.bind(g);
 g.increase_idx_def=(...a)=>{calls.push(['def',g.players[0].moon_water_sword_formation_stacks]);return def(...a);};
 g.add_c_of_x=(n,key)=>{if(key==='moon_water_sword_formation_stacks')calls.push(['moon',n]);return add(n,key);};
 g.just_do_the_card_and_nothing_else=c=>{calls.push(['body',g.players[0].moon_water_sword_formation_stacks]);return body(c);};
 g.play_card_inner('601011',0);assert.deepEqual(calls,[['def',0],['moon',2],['body',2]]);checked++;
 g.do_def_decay();assert.equal(g.players[0].def,6);
 g.do_def_decay();assert.equal(g.players[0].def,6);
 g.do_def_decay();assert.equal(g.players[0].def,3);checked++;
}
// Seat swaps and opposite initiative preserve ownership.
{
 const [g,l]=fresh([{strategy_id:13009,slot:0}]);const owner=g.players[0];
 g.players.reverse();g.play_card_inner('601011',0);assert.equal(owner.def,0);
 g.players.reverse();g.play_card_inner('601011',0);assert.equal(owner.def,6);assert.equal(l.forPlayer(owner)[0].used,true);checked++;
}
for(const invalid of [null,{players:[[],[]],extra:1},{players:[[{strategy_id:13008,slot:0}],[]]},
 {players:[[{strategy_id:13009,slot:-1}],[]]},{players:[[{strategy_id:13009,slot:8}],[]]},
 {players:[[{strategy_id:13009,slot:0},{strategy_id:13009,slot:0}],[]]},
 {players:[[{strategy_id:13009,slot:0,used:true}],[]]}]) {
 assert.throws(()=>installCurrentEngravings(root,new GameState(),invalid,[0,1]));checked++;
}
console.log(JSON.stringify({passed:true,checked}));
