from copy import deepcopy
from pathlib import Path
import json,shutil,subprocess,unittest
from unittest.mock import patch
from yixian import full_battle
from yixian import full_battle_v126 as new

STAGE=new.ROOT/'runs/stages/20261116T082200Z-s2-postbattle-admission'
FIXTURES=json.loads((STAGE/'opening-fixtures-v126.json').read_text('utf8'))

class PostbattleAdmissionTests(unittest.TestCase):
    def test_projection_preserves_ownership_and_all_starting_resources(self):
        facts=new.extension_contract();tables=new.catalogue();saved=deepcopy(tables)
        for fixture in FIXTURES.values():
            row,ctx=deepcopy(fixture['row']),deepcopy(fixture['context']);before=deepcopy((row,ctx))
            def old(r,**kw):
                self.assertEqual(r,row);self.assertEqual(kw['combat_context'],ctx)
                self.assertEqual(kw['tables'][:3],tables[:3])
                changed={k for k in tables[3] if kw['tables'][3][k]!=tables[3][k]}
                self.assertEqual(changed,set(x for ids in new.owned_ids(row) for x in ids))
                for k in changed:self.assertEqual(kw['tables'][3][k],{**tables[3][k],'isBattleEffect':False})
                return deepcopy(fixture['compiled'])
            with patch.object(new.previous,'compile_start',side_effect=old):
                got=new.compile_owned_start(row,new.owned_ids(row),facts,combat_context=ctx,tables=tables)
            self.assertEqual(got['battle'],fixture['compiled']['battle'])
            self.assertEqual(got['effect_players'],fixture['compiled']['effect_players'])
            self.assertFalse(got['postbattle_scope_v126']['match_continuation_allowed'])
            self.assertFalse(got['postbattle_scope_v126']['authoritative_resources_mutated'])
            self.assertEqual((row,ctx),before)
        self.assertEqual(tables,saved)

    def test_configuration_and_unknown_effect_guards_are_preserved(self):
        facts=new.extension_contract();fixture=next(iter(FIXTURES.values()));row=deepcopy(fixture['row'])
        tables=new.catalogue();tables[3][7038]['countParam']+=1
        with self.assertRaisesRegex(new.UnresolvedBattle,'configuration_changed'):
            new.compile_owned_start(row,new.owned_ids(row),facts,tables=tables)
        row['players'][0]['candidate_start']['xian_mo_strategies'].append(999999)
        with patch.object(new.previous,'compile_start',side_effect=new.UnresolvedBattle('unknown_season_effect:999999')) as old:
            with self.assertRaisesRegex(new.UnresolvedBattle,'unknown_season_effect'):
                new.compile_start(row,combat_context=fixture['context'])
            self.assertIn(999999,old.call_args.args[0]['players'][0]['candidate_start']['xian_mo_strategies'])

    def test_record_binding_rejects_changed_start_without_terminal_inputs(self):
        facts=new.extension_contract();rid=next(iter(facts['random_bindings']));fixture=FIXTURES[rid]
        row,ctx=deepcopy(fixture['row']),deepcopy(fixture['context'])
        with patch.object(new.previous,'compile_start',side_effect=lambda *a,**k:deepcopy(fixture['compiled'])):
            before=new.compile_start(row,combat_context=ctx)
            row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':123456}
            ctx['players'][0]['after_talent_counters']={'ignored':9999}
            self.assertEqual(before,new.compile_start(row,combat_context=ctx))
            ctx['battle_params'][0]+=1
            with self.assertRaises(new.UnresolvedBattle):new.compile_start(row,combat_context=ctx)
            ctx=deepcopy(fixture['context']);row['players'][0]['candidate_start']['board'].reverse()
            with self.assertRaisesRegex(new.UnresolvedBattle,'original_snapshot_mismatch'):
                new.compile_start(row,combat_context=ctx)
        row=deepcopy(fixture['row']);bad=deepcopy(fixture['compiled']);bad['battle']['seed']='changed'
        with patch.object(new.previous,'compile_start',return_value=bad):
            with self.assertRaisesRegex(new.UnresolvedBattle,'original_compiled_start_required'):
                new.compile_start(row,combat_context=fixture['context'])

    def test_runtime_fifo_rejects_incomplete_and_counterfactual_bindings(self):
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',
            str(new.ROOT/'tests/postbattle_parameters_v126_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertEqual(json.loads(p.stdout)['scenarios'],8)

if __name__=='__main__':unittest.main()
