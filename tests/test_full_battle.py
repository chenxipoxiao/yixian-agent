"""End-to-end software cases, not independent replay or real-game strength."""
import copy
import unittest
from yixian.full_battle import compile_start, simulate_batch, UnresolvedBattle
from yixian.ranked_rules import ranked_context
from yixian.terminal_damage import calculate_terminal_damage
from yixian.simulator import SimulatorError


def start_fixture():
    row={'id':'software-only','source_rules_version':'001.0008.0005','round':1,
         'source':{'raw_sha256':'software-fixture'},'players':[]}
    context={'source_raw_sha256':'software-fixture','game_mode':3,'season_mec':10,'players':[]}
    for i,slot in enumerate(('p1','p2')):
        row['players'].append({'snapshot_slot':slot,'character_id':1000003+i,
            'candidate_start':{'level':1,'extra_max_hp_modifier':0,'destiny':100,'exp':4,
                'unlocked_slots':3,'board':[0,0,0],'talents':[],'used_keyin_cards':[],
                'fate_strategies':[],'xian_mo_strategies':[],'talentTempDatas':{},
                'permanentBuffTempDatas':{'10024':6}}})
        context['players'].append({'snapshot_slot':slot,'is_mirror':False,'public_level':1,
            'hand_values_are_numeric':True,'hand_count':0})
    return row,context


def compile_fixture(row=None,context=None):
    if row is None:row,context=start_fixture()
    return compile_start(row,first_player=0,seed='software-only',game_mode=3,season_mec=10,combat_context=context)


class StartCompilerTests(unittest.TestCase):
    def setUp(self):self.row,self.context=start_fixture()

    def test_terminal_targets_cannot_change_input(self):
        before=compile_fixture(self.row,self.context)
        self.row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':9999,
            'recorded_turn_count':0,'recorded_destiny_damage':-999}
        self.context['players'][0]['after_talent_counters']={'105':999}
        self.assertEqual(before,compile_fixture(self.row,self.context))

    def test_auto_initiative_uses_start_speed_and_requires_explicit_tiebreak(self):
        args={'seed':1,'game_mode':3,'season_mec':10,'combat_context':self.context}
        with self.assertRaisesRegex(UnresolvedBattle,'Unknown initiative'):compile_start(self.row,**args)
        self.row['players'][1]['candidate_start']['permanentBuffTempDatas']['10012']=2
        c=compile_start(self.row,**args)
        self.assertEqual(c['battle']['first_player'],1)
        self.assertEqual(c['initiative_source'],'independent_start_speed_comparison')

    def test_source_and_mirror_context_are_required(self):
        for key,value in [('is_mirror',True),('is_mirror',None),('hand_count',None),
                          ('hand_count',-1),('hand_values_are_numeric',False),('public_level',2)]:
            with self.subTest(key=key,value=value):
                context=copy.deepcopy(self.context);context['players'][0][key]=value
                with self.assertRaises(UnresolvedBattle):compile_fixture(self.row,context)
        self.context['source_raw_sha256']='different'
        with self.assertRaisesRegex(UnresolvedBattle,'source mismatch'):compile_fixture(self.row,self.context)

    def test_unknown_card_or_active_effect_blocks_entire_battle(self):
        for key,value in [('board',[0,999999999,0]),('permanentBuffTempDatas',{'9999999':1}),
                          ('used_keyin_cards',[40042]),('fate_strategies',[21]),
                          ('xian_mo_strategies',[9999999])]:
            with self.subTest(key=key):
                row=copy.deepcopy(self.row);row['players'][0]['candidate_start'][key]=value
                with self.assertRaises(UnresolvedBattle):compile_fixture(row,self.context)

    def test_persistent_physique_does_not_heal_or_reapply_acquisition(self):
        s=self.row['players'][0]['candidate_start'];s['extra_max_hp_modifier']=8
        s['permanentBuffTempDatas']['10023']=10;s['talents']=[24,85]
        player=compile_fixture(self.row,self.context)['battle']['players'][0]
        self.assertEqual((player['hp'],player['max_hp'],player['physique']),(48,58,10))
        self.assertEqual(player['cards'],['601011']*3)
        self.assertEqual(player['hand_count'],0)

    def test_current_season_zen_modifier_is_one_startup_argument(self):
        s=self.row['players'][0]['candidate_start'];s['talents']=[183]
        plain=compile_fixture(self.row,self.context)['battle']['players'][0]
        s['xian_mo_strategies']=[23062]
        enhanced=compile_fixture(self.row,self.context)['battle']['players'][0]
        self.assertEqual(plain['zen_mind_forging_body_stacks'],1)
        self.assertEqual(enhanced['zen_mind_forging_body_stacks'],2)
        self.assertEqual(enhanced['physique'],plain['physique'])
        self.assertEqual(enhanced['hp'],plain['hp'])

    def test_ranked_rule_is_versioned_and_rejects_conflicting_resonance(self):
        self.assertEqual(ranked_context(version='001.0008.0005',game_mode=3,season_mec=10)['resonance_selected'],0)
        for kw in [{'version':'old'},{'game_mode':2},{'season_mec':9},{'observed_resonance':84}]:
            args={'version':'001.0008.0005','game_mode':3,'season_mec':10};args.update(kw)
            with self.assertRaises(ValueError):ranked_context(**args)


class CompleteBattleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base=compile_fixture()['battle'];cls.inputs=[]
        for name in ('normal','seat1','truncated','cat_empty','cat_full','plain_zen','extra_zen'):
            b=copy.deepcopy(base)
            if name=='seat1':b['first_player']=1
            if name=='truncated':b['max_turns']=1
            if name.startswith('cat_'):
                b['players'][0]['cards']=['614032']*3
                b['players'][0]['hand_count']=3 if name=='cat_full' else 0
                b['max_turns']=1
            if name.endswith('zen'):
                b['players'][0]['physique']=7;b['players'][0]['max_hp']=47
                b['players'][0]['zen_mind_forging_body_stacks']=2 if name=='extra_zen' else 1
                b['max_turns']=1
            cls.inputs.append((name,b))
        cls.original=copy.deepcopy(cls.inputs)
        cls.results=dict(zip((n for n,b in cls.inputs),simulate_batch([b for n,b in cls.inputs])['results']))

    def test_full_three_slot_fight_completes_without_padding(self):
        r=self.results['normal']
        self.assertTrue(r['terminated']);self.assertFalse(r['truncated'])
        self.assertEqual((r['winner'],r['turns'],r['hp_delta']),(0,27,3))
        self.assertEqual([len(p['cards']) for p in r['players']],[3,3])
        self.assertEqual(self.inputs,self.original)
        self.assertFalse(r['legacy_destiny_settlement_applied'])
        self.assertFalse(r['training_label_allowed'])

    def test_trace_and_winner_preserve_original_seats(self):
        r=self.results['seat1']
        self.assertEqual((r['winner'],r['turns'],r['hp_delta']),(1,27,-3))
        self.assertEqual([t['actor'] for t in r['trace'][:4]],[1,0,1,0])
        self.assertEqual([p['hp'] for p in r['trace'][0]['after']],[37,40])

    def test_truncation_never_generates_win_or_damage(self):
        r=self.results['truncated'];self.assertIsNone(r['winner']);self.assertIsNone(r['hp_delta'])
        self.assertTrue(r['truncated']);self.assertFalse(calculate_terminal_damage(compile_fixture(),r)['resolved'])

    def test_current_cat_uses_attack_two_and_explicit_hand_count(self):
        self.assertEqual(self.results['cat_empty']['players'][1]['hp'],34)  # 3 x 2.
        self.assertEqual(self.results['cat_full']['players'][1]['hp'],28)   # (3 + 3) x 2.

    def test_zen_modifier_uses_physique_over_cap_healing(self):
        a=self.results['plain_zen']['trace'][0]['before'][0]
        b=self.results['extra_zen']['trace'][0]['before'][0]
        self.assertEqual((a['hp'],a['max_hp']),(41,48))
        self.assertEqual((b['hp'],b['max_hp']),(42,49))

    def test_missing_hand_count_and_unknown_fields_are_rejected(self):
        for field in ('hand_count','qi'):
            b=copy.deepcopy(self.inputs[0][1]);del b['players'][0][field]
            with self.assertRaisesRegex(SimulatorError,'Explicit'):simulate_batch([b])
        b=copy.deepcopy(self.inputs[0][1]);b['recorded_winner']=0
        with self.assertRaisesRegex(SimulatorError,'Unknown battle field'):simulate_batch([b])

    def test_terminal_damage_uses_simulation_and_preserves_inputs(self):
        c=compile_fixture();r=self.results['normal'];before=copy.deepcopy((c,r))
        d=calculate_terminal_damage(c,r)
        self.assertEqual((d['hp_difference'],d['life_damage'],d['loser_destiny_after']),(3,2,98))
        self.assertEqual((c,r),before);self.assertFalse(d['full_match_transition_complete'])


class TerminalDamageTests(unittest.TestCase):
    def setUp(self):
        self.c=compile_fixture();self.c['battle']['players'][0]['round_number']=18
        self.r={'terminated':True,'truncated':False,'winner':0,
            'players':[{'hp':55,'kindness_tune_stacks':0,'direct_destiny_lost':0},
                       {'hp':-5,'kindness_tune_stacks':0,'direct_destiny_lost':0}]}

    def test_kindness_precedes_cap_then_even_reduction(self):
        self.c['effect_players'][0]['season_choices']=[2011]
        self.c['effect_players'][1]['fates']=[27,45]
        self.r['players'][1]['kindness_tune_stacks']=4
        d=calculate_terminal_damage(self.c,self.r)
        self.assertEqual(d['base_damage'],27);self.assertEqual(d['life_damage'],10)
        self.assertEqual([e['effect'] for e in d['events']],['season2011','buff210','talent27_cap','talent45'])

    def test_kindness_floor_and_guard_pending_counter(self):
        self.r['players'][1]['kindness_tune_stacks']=50
        self.assertEqual(calculate_terminal_damage(self.c,self.r)['life_damage'],1)
        self.r['players'][1]['kindness_tune_stacks']=0
        self.c['effect_players'][1].update(fates=[105],talent_counters={'105':1})
        d=calculate_terminal_damage(self.c,self.r);self.assertEqual(d['life_damage'],0)
        self.assertEqual(d['pending_match_effects'],[{'kind':'consume_fate_counter','fate':105}])
        self.assertEqual(self.c['effect_players'][1]['talent_counters'],{'105':1})

    def test_single_survival_and_multiple_survival_ambiguity(self):
        loser=self.c['effect_players'][1];loser.update(fates=[65],talent_counters={'65':1},life=8)
        self.assertEqual(calculate_terminal_damage(self.c,self.r)['life_damage'],7)
        loser['fates'].append(83);loser['talent_counters']['83']=1
        self.assertFalse(calculate_terminal_damage(self.c,self.r)['resolved'])

    def test_missing_counter_is_not_empty_dictionary(self):
        self.c['effect_players'][1].update(fates=[105],talent_counters=None)
        with self.assertRaisesRegex(ValueError,'counters'):calculate_terminal_damage(self.c,self.r)

    def test_in_battle_destiny_changes_require_ledger(self):
        self.r['players'][1]['direct_destiny_lost']=1
        self.assertFalse(calculate_terminal_damage(self.c,self.r)['resolved'])

    def test_unknown_terminal_buff_is_not_zero(self):
        del self.r['players'][1]['kindness_tune_stacks']
        with self.assertRaisesRegex(ValueError,'kindness'):calculate_terminal_damage(self.c,self.r)


if __name__=='__main__':unittest.main()
