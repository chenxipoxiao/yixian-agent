import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));
await ready;
let checked=0;
function fresh(length=8) {
 const g=new GameState(undefined,undefined,'star-fate-software-v22');
 for(const p of g.players) {
  Object.assign(p,{cards:Array(length).fill('601011'),hp:1000,max_hp:1000,qi:0,def:0});
  p.reset_can_play();
 }
 return g;
}
for(const seat of [0,1]) {
 const g=fresh();g.players[seat].star_moon_folding_fan_stacks=1;
 g.apply_p5_fates_setup(seat);
 assert.deepEqual(g.players[seat].is_star_point,[false,false,true,false,false,true,true,false]);
 assert.equal(g.players[1-seat].is_star_point[6],false);
 assert.equal(g.players[seat].qi,0);checked++;
}
// Re-adding an existing star slot gives one qi in both client and native engine.
{
 const g=fresh();g.players[0].star_moon_folding_fan_stacks=1;
 g.players[0].is_star_point[6]=true;g.apply_p5_fates_setup(0);
 assert.equal(g.players[0].qi,1);checked++;
}
// Short boards are not silently padded; an unexposed slot cannot affect attacks.
{
 const g=fresh(6);g.players[0].star_moon_folding_fan_stacks=1;
 g.apply_p5_fates_setup(0);assert.equal(g.players[0].is_star_point.length,6);
 assert.equal(g.players[0].cards.length,6);checked++;
}
// Actual native damage, not a mocked attack counter: Hit3 receives star power
// on its two7 attacks and enables its third9 attack only on a star slot.
for(const [owned,damage] of [[false,14],[true,47]]) {
 const g=fresh();g.players[0].cards[6]='123023';g.players[0].star_power=8;
 if(owned)g.players[0].star_moon_folding_fan_stacks=1;
 g.apply_p5_fates_setup(0);g.play_card('123023',6);
 assert.equal(g.players[1].hp,1000-damage);checked++;
}
process.stdout.write(JSON.stringify({passed:true,scenarios:checked}));
