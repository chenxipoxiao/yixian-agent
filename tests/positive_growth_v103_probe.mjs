import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {installPositiveGrowth} from '../tools/current_positive_growth_v103.mjs';
import {installSpiritOutburst} from '../tools/current_spirit_outburst_v83.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(path.join(root,'external/yisim'));
const {GameState,ready}=await import(pathToFileURL(path.join(process.cwd(),'gamestate_full.js')));await ready;
function fixture(){
 const g=new GameState(undefined,undefined,'positive-growth-software');
 for(const p of g.players)Object.assign(p,{hp:20,max_hp:100,cards:['601011']});
 const observer=installPositiveGrowth(root,g,{players:[true,false]},[0,1]);
 const overflow=installSpiritOutburst(root,g,[0,1]);observer.attachHealing(overflow);
 return {g,p:g.players[0],q:g.players[1],observer};
}
let scenarios=0;
{
 const {g,p,observer}=fixture();assert.equal(p.hp,20);assert.equal(p.max_hp,100);
 g.increase_idx_hp(0,5);assert.equal(p.hp,26);g.increase_idx_max_hp(0,5);assert.equal(p.max_hp,106);
 assert.equal(observer.metadata().events.filter(e=>e.kind==='positive_healing').length,1);scenarios++;
}
{
 const {g,p,observer}=fixture();g.increase_idx_hp(0,0);g.increase_idx_max_hp(0,0);assert.equal(p.hp,20);assert.equal(p.max_hp,100);assert.equal(observer.metadata().events.length,0);scenarios++;
}
{
 const {g,p}=fixture();p.indigestion=7;g.increase_idx_hp(0,5);assert.equal(p.hp,21);scenarios++;
}
{
 const {g,p}=fixture();p.god_opportunity_conform_stacks=1;g.increase_idx_hp(0,5);assert.equal(p.hp,29);g.increase_idx_max_hp(0,5);assert.equal(p.max_hp,109);scenarios++;
}
{
 const {g,p,observer}=fixture();p.p2_rejuvenation_stacks=1;p.p5_rejuvenation_stacks=1;g.increase_idx_hp(0,5);assert.equal(p.max_hp,110);assert.equal(observer.metadata().events.filter(e=>e.kind==='positive_max_hp').length,1);scenarios++;
}
{
 const {g,p}=fixture();p.m_metal_spirit_seal_stacks=1;p.indigestion=7;p.appetite=10;g.increase_idx_hp(0,5);assert.equal(p.penetrate,5);assert.equal(p.hp,20);assert.equal(p.max_hp,100);scenarios++;
}
for(const field of ['prevent_gain_hp_stacks','metal_spirit_chokehold_stacks']){
 const {g,p,observer}=fixture();p[field]=1;g.increase_idx_hp(0,5);assert.equal(p.hp,20);assert.equal(observer.metadata().events.length,0);scenarios++;
}
{
 const {g,p,q,observer}=fixture();p.hp=99;g.current_spirit_outburst_gain(2,4000106);g.increase_idx_hp(0,5);
 assert.equal(p.hp,100);assert.equal(q.hp,15);assert.equal(observer.metadata().events[0].overflow,5);scenarios++;
}
{
 const {g,p}=fixture();p.hp=-2;g.increase_idx_hp(0,5);assert.equal(p.hp,4);scenarios++;
}
{
 const {g,p,q,observer}=fixture();g.players.reverse();g.increase_idx_hp(0,5);assert.equal(q.hp,25);assert.equal(p.hp,20);
 g.increase_idx_hp(1,5);assert.equal(p.hp,26);assert.equal(observer.metadata().events[0].player_index,0);scenarios++;
}
{
 const {g,p}=fixture();assert.throws(()=>g.increase_idx_hp(0,-1),/nonnegative_int32/);assert.throws(()=>g.increase_idx_max_hp(0,2147483647),/nonnegative_int32/);assert.equal(p.hp,20);assert.equal(p.max_hp,100);scenarios++;
}
process.stdout.write(JSON.stringify({passed:true,scenarios,scope:'software boundaries only'}));
