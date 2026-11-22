import assert from 'node:assert/strict';
import fs from 'node:fs';
import {installFlagParameterReader} from '../tools/current_flag_parameter_reader_v102.mjs';
const facts=JSON.parse(fs.readFileSync('data/inspection/current-element-flag-v62r2.json','utf8'));
function fixture(value,{target='133091',slot=0,hand=[7000029,7000020],duplicates=1}={}){
 const p={cards:[],hand_count:hand.length,trigger_depth:1,currently_triggering_card_id:'762001',currently_triggering_card_idx:slot,currently_playing_card_idx:slot};p.cards[slot]='762001';
 const game={players:[p,{}],effects:0,current_element_flag(){for(let i=0;i<duplicates;i++)this.trigger_card(target,slot);},trigger_card(){this.effects++;}};
 const calls=[];const reader=installFlagParameterReader(game,{'133091':{card_actions(){}}},[hand,null],[0,1],facts,e=>{calls.push(e);assert.equal(value,e.expected_value,'selected-card mismatch');});
 return {game,calls,reader};
}
const a=fixture(7000029);a.game.current_element_flag(7000111);a.reader.verifyIdle();assert.equal(a.game.effects,1);assert.equal(a.calls[0].selection.raw,7000029);assert.equal(a.calls[0].forced_by_hexagram,false);
const b=fixture(7010029);assert.throws(()=>b.game.current_element_flag(7000111),/selected-card mismatch/);assert.equal(b.game.effects,0);
const c=fixture(7000029,{target:'133092'});assert.throws(()=>c.game.current_element_flag(7000111),/flag_selected_runtime_mismatch/);assert.equal(c.game.effects,0);
const d=fixture(7000029,{slot:1});assert.throws(()=>d.game.current_element_flag(7000111),/even_slot_seal_reader_not_admitted/);assert.equal(d.calls.length,0);
const e=fixture(7000029,{duplicates:2});assert.throws(()=>e.game.current_element_flag(7000111),/flag_selected_runtime_mismatch/);
