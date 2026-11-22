from copy import deepcopy
import json,unittest
from unittest.mock import patch
from yixian import full_battle_v128 as engine

STAGE=engine.ROOT/'runs/stages/20261116T093000Z-s2-sever-mortal-phase'
FIXTURE=next(iter(json.loads((STAGE/'opening-fixtures-v128.json').read_text('utf8')).values()))

class SeverMortalPhaseTests(unittest.TestCase):
    def test_preserves_ownership_resources_and_missing_action_receipts(self):
        facts=engine.extension_contract();tables=engine.catalogue();saved=deepcopy(tables)
        row,ctx=deepcopy(FIXTURE['row']),deepcopy(FIXTURE['context']);before=deepcopy((row,ctx))
        def previous(r,**kw):
            self.assertEqual(r,row);self.assertEqual(kw['combat_context'],ctx)
            self.assertEqual(kw['tables'][:3],tables[:3])
            changed={k for k in tables[3] if kw['tables'][3][k]!=tables[3][k]}
            self.assertEqual(changed,{7062})
            self.assertEqual(kw['tables'][3][7062],{**tables[3][7062],'isBattleEffect':False})
            return deepcopy(FIXTURE['compiled'])
        with patch.object(engine.previous,'compile_start',side_effect=previous):
            got=engine.compile_owned_start(row,engine.owned_ids(row),facts,combat_context=ctx,tables=tables)
        self.assertEqual(got['battle'],FIXTURE['compiled']['battle'])
        self.assertEqual(got['effect_players'],FIXTURE['compiled']['effect_players'])
        scope=got['preparation_scope_v128']
        for key in ['active_use_replayed','active_use_receipt_inferred','remaining_uses_inferred',
                    'exchange_or_pool_mutated','authoritative_resources_mutated','match_continuation_allowed','training_label_allowed']:
            self.assertFalse(scope[key],key)
        self.assertTrue(scope['pending_legal_preparation_transition'])
        self.assertEqual((row,ctx),before);self.assertEqual(tables,saved)

    def test_changed_config_and_other_unknown_effects_stay_blocked(self):
        facts=engine.extension_contract();row=deepcopy(FIXTURE['row']);tables=engine.catalogue()
        tables[3][7062]['countParam']+=1
        with self.assertRaisesRegex(engine.UnresolvedBattle,'configuration_changed'):
            engine.compile_owned_start(row,engine.owned_ids(row),facts,tables=tables)
        row['players'][0]['candidate_start']['xian_mo_strategies'].append(999999)
        with self.assertRaisesRegex(engine.UnresolvedBattle,'unknown_season_effect:999999'):
            engine.compile_start(row,combat_context=FIXTURE['context'],game_mode=3,season_mec=10,seed='diagnostic-'+row['id'])

    def test_record_binding_ignores_outcomes_but_rejects_changed_opening_or_stream(self):
        row,ctx=deepcopy(FIXTURE['row']),deepcopy(FIXTURE['context'])
        with patch.object(engine.previous,'compile_start',side_effect=lambda *a,**k:deepcopy(FIXTURE['compiled'])):
            original=engine.compile_start(row,combat_context=ctx)
            row['outcome']={'winner_snapshot_slot':'p1','recorded_hp_delta':123456}
            ctx['players'][0]['after_talent_counters']={'ignored':9999}
            self.assertEqual(original,engine.compile_start(row,combat_context=ctx))
            ctx['battle_params'][0]+=1
            with self.assertRaises(engine.UnresolvedBattle):engine.compile_start(row,combat_context=ctx)
            ctx=deepcopy(FIXTURE['context']);row['players'][0]['candidate_start']['board'].reverse()
            with self.assertRaisesRegex(engine.UnresolvedBattle,'original_snapshot_mismatch'):
                engine.compile_start(row,combat_context=ctx)
        bad=deepcopy(FIXTURE['compiled']);bad['battle']['seed']='changed'
        with patch.object(engine.previous,'compile_start',return_value=bad):
            with self.assertRaisesRegex(engine.UnresolvedBattle,'original_compiled_start_required'):
                engine.compile_start(FIXTURE['row'],combat_context=FIXTURE['context'])

    def test_unowned_or_unknown_ownership_does_not_infer_action(self):
        row=deepcopy(FIXTURE['row']);row['players'][0]['candidate_start']['xian_mo_strategies'].remove(7062)
        sentinel={'unchanged':True}
        with patch.object(engine.previous,'compile_start',return_value=sentinel) as prev:
            self.assertIs(engine.compile_start(row,combat_context=FIXTURE['context']),sentinel)
            self.assertEqual(prev.call_args.kwargs,{'combat_context':FIXTURE['context']})
        del row['players'][0]['candidate_start']['xian_mo_strategies']
        with self.assertRaisesRegex(engine.UnresolvedBattle,'explicit_season_ownership_required'):
            engine.compile_start(row,combat_context=FIXTURE['context'])

if __name__=='__main__':unittest.main()
