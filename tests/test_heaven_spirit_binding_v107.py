from copy import deepcopy
from pathlib import Path
import json,unittest
from unittest.mock import patch
from yixian import combat_start_context_bindings_v7 as binding
from yixian import combat_start_context_bindings_v6 as legacy
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'runs/stages/20261115T115500Z-s2-heaven-spirit-preparation'
read=lambda p:json.loads(p.read_text('utf8'))

class HeavenSpiritSourceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  plan=read(S/'source-plan-v7.json');cls.rows={r['id']:r for r in map(json.loads,(ROOT/plan['rows']).read_text('utf8').splitlines())}
  cls.old=read(ROOT/plan['previous_contexts']);cls.ctx=read(S/'source-intake/combat-context.json')
  cls.admitted=read(S/'source-intake/admitted-records.json');cls.legacy=read(ROOT/plan['legacy_admitted']);cls.rid=next(iter(cls.admitted))

 def fixture(self):
  row=deepcopy(self.rows[self.rid]);ctx=deepcopy(self.old[self.rid]);source=deepcopy(row['source']);turn={'round':row['round']}
  for i,slot in enumerate(('p1','p2')):
   owned=row['players'][i]['candidate_start']['xian_mo_strategies'];temp=deepcopy(ctx[legacy.FIELD]['players'][i]['present_values'])
   if 1001 in owned:temp['1001']=1
   ctx[legacy.FIELD]['players'][i]['complete_temp_map_sha256']=binding.digest_json(temp)
   turn[slot]={'publicData':{'lastRoundData':{'xianMoStrategies':owned}},'privateData':{'xianMoData':{'strategies':[{'selected':x} for x in owned],'tempDatas':temp}}}
  expected={'receipt_sha256':binding.digest_json(ctx[legacy.FIELD]),'snapshot_sha256':ctx[legacy.FIELD]['snapshot_sha256']}
  return turn,source,row,ctx,expected

 def test_real_additions_preserve_all_old_context(self):
  self.assertEqual(binding.validate_additions(list(self.rows.values()),self.old,self.ctx,set(self.admitted),self.legacy),self.admitted)
  self.assertEqual(len(self.admitted),5)

 def test_missing_map_not_defaulted(self):
  turn,source,row,ctx,expected=self.fixture();del turn['p1']['privateData']['xianMoData']['tempDatas']
  with self.assertRaisesRegex(ValueError,'complete_map_required'):binding.bind_heaven_spirit(turn,source,row,ctx,expected)

 def test_explicit_zero_nonzero_and_absent_are_distinct(self):
  for value in [None,0,1,-1,True]:
   with self.subTest(value=value):
    turn,source,row,ctx,expected=self.fixture();i=next(i for i,p in enumerate(row['players']) if 1001 in p['candidate_start']['xian_mo_strategies']);slot=('p1','p2')[i]
    temp=turn[slot]['privateData']['xianMoData']['tempDatas']
    if value is None:temp.pop('1001')
    else:temp['1001']=value
    ctx[legacy.FIELD]['players'][i]['complete_temp_map_sha256']=binding.digest_json(temp);expected['receipt_sha256']=binding.digest_json(ctx[legacy.FIELD])
    if value is True:
     with self.assertRaisesRegex(ValueError,'invalid_value'):binding.bind_heaven_spirit(turn,source,row,ctx,expected)
     continue
    result=binding.bind_heaven_spirit(turn,source,row,ctx,expected);r=result[binding.FIELD]
    e={'receipt_sha256':binding.digest_json(r),'snapshot_sha256':r['snapshot_sha256'],'legacy_receipt_sha256':r['legacy_receipt_sha256']}
    plain,switches=binding.validate_receipt(row,result,e,expected)
    self.assertEqual(plain,ctx);self.assertEqual(switches[i]['temp_data'],{} if value is None else {'1001':value})
    self.assertEqual(r['players'][i]['absent_keys'],['1001'] if value is None else [])

 def test_raw_round_ownership_and_old_map_hash_guards(self):
  for kind in ['raw','round','ownership','map']:
   with self.subTest(kind=kind):
    turn,source,row,ctx,expected=self.fixture()
    if kind=='raw':source['raw_sha256']='0'*64
    elif kind=='round':turn['round']+=1
    elif kind=='ownership':turn['p1']['privateData']['xianMoData']['strategies']=[]
    else:turn['p1']['privateData']['xianMoData']['tempDatas']['new']=1
    with self.assertRaises(ValueError):binding.bind_heaven_spirit(turn,source,row,ctx,expected)

 def test_snapshot_and_old_receipt_tampering_rejected(self):
  for kind in ['board','new_receipt','old_receipt']:
   with self.subTest(kind=kind):
    row=deepcopy(self.rows[self.rid]);ctx=deepcopy(self.ctx[self.rid])
    if kind=='board':row['players'][0]['candidate_start']['board'].reverse()
    elif kind=='new_receipt':ctx[binding.FIELD]['players'][0]['complete_temp_map_present']=False
    else:ctx[legacy.FIELD]['players'][0]['complete_temp_map_present']=False
    with self.assertRaises(ValueError):binding.validate_receipt(row,ctx,self.admitted[self.rid],self.legacy[self.rid])

 def test_outcomes_are_not_source_inputs(self):
  turn,source,row,ctx,expected=self.fixture();before=binding.bind_heaven_spirit(turn,source,row,ctx,expected)
  turn.update(winner='changed',hpDelta=99999,turnCount=99999);row['outcome']={'hp_delta':-99999}
  for slot in ['p1','p2']:turn[slot]['publicData']['destiny']=-99999
  self.assertEqual(before,binding.bind_heaven_spirit(turn,source,row,ctx,expected))

 def test_versioned_translation_keeps_legacy_contract(self):
  from yixian import full_battle_v107 as engine
  row=self.rows[self.rid];ctx=self.ctx[self.rid]
  with patch.object(engine.legacy_engine.previous,'compile_start',return_value={'battle':{},'effect_players':[{},{}]}) as lower:
   result=engine.compile_start(row,combat_context=ctx)
   projected=lower.call_args.args[0];translated=lower.call_args.kwargs['combat_context']
   self.assertNotIn(binding.FIELD,translated);self.assertNotIn(legacy.FIELD,translated)
   self.assertEqual(translated['players'][0]['heaven_spirit_switch']['temp_data'],{'1001':1})
   self.assertEqual(result['original_preparation_context_v105']['receipt_sha256'],self.legacy[self.rid]['receipt_sha256'])
   self.assertEqual(result['effect_players'][0]['season_choices'],row['players'][0]['candidate_start']['xian_mo_strategies'])
  self.assertEqual(ctx,self.ctx[self.rid])
  initiative=engine.derive_start_initiative(row,game_mode=3)
  first=None if initiative['candidate_first_index'] is not None else {'p1':0,'p2':1}[row['outcome']['first_player_snapshot_slot']]
  with self.assertRaisesRegex(engine.UnresolvedBattle,'heaven_spirit_preparation_switch_required'):
   engine.previous.compile_start(row,first_player=first,seed='diagnostic-'+self.rid,game_mode=3,season_mec=10,combat_context=ctx)

 def test_unselected_exact_delegate_and_unregistered_receipt(self):
  from yixian import full_battle_v107 as engine
  rid=next(r for r in self.rows if r not in self.admitted);row=self.rows[rid];ctx=self.ctx[rid]
  with patch.object(engine.previous,'compile_start',return_value={'unchanged':True}) as old:
   self.assertEqual(engine.compile_start(row,combat_context=ctx),{'unchanged':True});old.assert_called_once_with(row,combat_context=ctx)
  changed=deepcopy(ctx);changed[binding.FIELD]={}
  with self.assertRaisesRegex(engine.UnresolvedBattle,'unregistered_receipt'):engine.compile_start(row,combat_context=changed)

if __name__=='__main__':unittest.main()
