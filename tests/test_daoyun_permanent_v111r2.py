"""The new admission preserves source state; complete combat is checked separately."""
from copy import deepcopy
import unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v111 as engine,full_battle as base

class DaoYunPermanentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.tables=engine.catalogue()

    def setUp(self):
        self.row,self.context=start_fixture()
        self.row['players'][0]['candidate_start']['permanentBuffTempDatas']['10025']=1

    def compile(self,row=None,context=None):
        return engine.compile_start(self.row if row is None else row,tables=self.tables,
            combat_context=self.context if context is None else context,game_mode=3,season_mec=10,first_player=0,seed='software-only')

    def test_signed_stock_preserved_without_combat_change(self):
        plain=deepcopy(self.row);del plain['players'][0]['candidate_start']['permanentBuffTempDatas']['10025']
        old=engine.previous.compile_start(plain,tables=self.tables,combat_context=self.context,game_mode=3,season_mec=10,first_player=0,seed='software-only')
        for value in [1,0,-3,5]:
            with self.subTest(value=value):
                self.row['players'][0]['candidate_start']['permanentBuffTempDatas']['10025']=value
                compiled=self.compile();meta=compiled.pop('daoyun_permanent_context_v111')
                self.assertEqual(compiled,old)
                self.assertEqual(meta['permanent10025'],[{'present':True,'value':value},{'present':False,'value':None}])

    def test_inputs_and_global_compiler_are_unchanged(self):
        row,ctx,tables=deepcopy(self.row),deepcopy(self.context),deepcopy(self.tables);fields=set(base.PERMANENT_FIELDS)
        self.compile()
        self.assertEqual(self.row,row);self.assertEqual(self.context,ctx);self.assertEqual(self.tables,tables)
        self.assertEqual(base.PERMANENT_FIELDS,fields);self.assertNotIn('10025',fields)
        with self.assertRaisesRegex(engine.UnresolvedBattle,'permanent_hooks_pending:10025'):
            engine.previous.compile_start(self.row,tables=self.tables,combat_context=self.context,game_mode=3,season_mec=10,first_player=0,seed='software-only')

    def test_terminal_and_postbattle_fields_do_not_enter_start(self):
        before=self.compile();self.row['outcome']={'recorded_hp_delta':9999,'winner_snapshot_slot':'p2'}
        self.context['players'][0]['after_talent_counters']={'27':999}
        self.assertEqual(before,self.compile())

    def test_invalid_values_missing_maps_and_automatic_initiative_bounds_reject(self):
        for value in [True,None,'1',2**31,-(2**31)-1]:
            row=deepcopy(self.row);row['players'][0]['candidate_start']['permanentBuffTempDatas']['10025']=value
            with self.assertRaisesRegex(engine.UnresolvedBattle,'invalid_signed_value'):self.compile(row)
        for value in [-(2**31),2**31-1]:
            row=deepcopy(self.row);row['players'][0]['candidate_start']['permanentBuffTempDatas']['10025']=value
            with self.assertRaisesRegex(ValueError,'bounded explicit integers'):
                engine.compile_start(row,tables=self.tables,combat_context=self.context,
                    game_mode=3,season_mec=10,first_player=None,seed='software-only')
        for missing in [True,False]:
            row=deepcopy(self.row)
            if missing:del row['players'][1]['candidate_start']['permanentBuffTempDatas']
            else:row['players'][1]['candidate_start']['permanentBuffTempDatas']=None
            with self.assertRaisesRegex(engine.UnresolvedBattle,'explicit_permanent_map_required'):self.compile(row)

    def test_unknown_state_and_separate_leaf_migration_reject(self):
        row=deepcopy(self.row);row['players'][0]['candidate_start']['permanentBuffTempDatas']['10016']=1
        with self.assertRaisesRegex(engine.UnresolvedBattle,'permanent_hooks_pending:10016'):self.compile(row)
        ctx=deepcopy(self.context);ctx['cloud_sword_record']={}
        with self.assertRaisesRegex(engine.UnresolvedBattle,'cloud_leaf_combination_pending'):self.compile(context=ctx)

    def test_unselected_exact_delegation(self):
        row,ctx=start_fixture();new=self.compile(row,ctx)
        old=engine.previous.compile_start(row,tables=self.tables,combat_context=ctx,game_mode=3,season_mec=10,first_player=0,seed='software-only')
        self.assertEqual(new,old);self.assertIs(engine.catalogue,engine.previous.catalogue)
        self.assertIs(engine.derive_start_initiative,engine.previous.derive_start_initiative)

if __name__=='__main__':unittest.main()
