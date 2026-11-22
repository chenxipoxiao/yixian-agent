import unittest
from yixian.fate_catalog import build_catalog, classify, render_description, render_markdown


def localization(values):
    return {'mSource':{'mTerms':[{'Term':key,'Languages':[value]} for key,value in values.items()]}}


class FateCatalogTests(unittest.TestCase):
    def test_description_only_substitutes_known_literals(self):
        text=render_description('加{otherParams[0]}气，第{effectRound}轮获得【431】。{otherParams[9]} {danger()} 【KEYWORD_灵气】',
                                {'otherParams':[2],'effectRound':10},card_names={431:'龟之力'})
        self.assertIn('加2气，第10轮获得【龟之力】',text)
        self.assertIn('{otherParams[9]} {danger()}',text)
        self.assertIn('【灵气】',text)

    def test_false_battle_flag_does_not_hide_damage_or_death_effect(self):
        entry=classify('下次命元耗尽时，保留1点命元不被淘汰',battle_flag=False)
        self.assertTrue(entry['combat_relevant'])
        self.assertIn('death_prevention',entry['phases'])
        self.assertFalse(entry['classification_verified'])
        self.assertTrue(classify('生命上限+5',battle_flag=False)['combat_relevant'])
        self.assertIn('battle_end',classify('每当战斗失败时换牌机会+1')['phases'])
        self.assertIn('battle_start',classify('开始战斗时若换牌机会为0，下轮多加1次换牌机会')['phases'])
        self.assertTrue(classify('为【澄心剑胚】选效果：攻+3')['combat_relevant'])

    def test_namespace_partial_coverage_and_availability_stay_distinct(self):
        regular=[{'id':1001,'name':'普通','isBattleTalent':True}]
        seasonal=[{'id':1001,'isBattleEffect':True,'isAvailable':False,'otherParams':[2], '_unknown_fields':{'8':'data'}},
                  {'id':1002,'isBattleEffect':True,'isAvailable':True}]
        support={'regular':{1001},'partial_season':{1001:['battle_start']},'legacy_candidate_season':{1002}}
        result=build_catalog(regular,seasonal,localization({'XianMoStrategyName_1001':'开局','XianMoStrategyDesc_1001':'战斗开始加{otherParams[0]}气'}),runtime_support=support)
        ordinary, partial, legacy=result['entries']
        self.assertTrue(ordinary['execution']['complete_effect'])
        self.assertFalse(partial['execution']['complete_effect'])
        self.assertEqual(partial['execution']['components'],['battle_start'])
        self.assertFalse(partial['available'])
        self.assertTrue(partial['has_unparsed_expression_fields'])
        self.assertEqual(legacy['execution']['status'],'legacy_candidate')
        self.assertEqual(result['summary']['season']['combat_available_records'],1)

    def test_unimplemented_flagged_effect_and_mode_variants_not_claimed_supported(self):
        result=build_catalog([{'id':7,'name':'保命','talentId':7,'isBattleTalent':False,'diffDescInGameModes':[17]}],[],
            localization({'TalentDesc_7':'下次命元耗尽时，保留1点命元不被淘汰'}),runtime_support={})
        entry=result['entries'][0]
        self.assertEqual(entry['execution']['status'],'not_implemented')
        self.assertEqual(entry['eligibility']['diffDescInGameModes'],[17])
        self.assertIn('保命',render_markdown(result))

    def test_partial_registry_wins_over_broad_execution_whitelist(self):
        result=build_catalog([{'id':7,'name':'保命','isBattleTalent':False}],[],
            localization({'TalentDesc_7':'下次命元耗尽时，保留1点命元不被淘汰'}),
            runtime_support={'regular':{7},'partial_regular':{7:['death_prevention']}})
        self.assertFalse(result['entries'][0]['execution']['complete_effect'])
        self.assertEqual(result['summary']['regular']['complete_declared_effects'],0)
        self.assertIsNone(result['summary']['regular']['combat_available_records'])

    def test_duplicate_ids_rejected_but_cross_namespace_same_id_is_valid(self):
        with self.assertRaises(ValueError):
            build_catalog([{'id':1},{'id':1}],[],localization({}),runtime_support={})
        result=build_catalog([{'id':1}],[{'id':1}],localization({}),runtime_support={})
        self.assertEqual(len(result['entries']),2)

    def test_preparation_components_are_not_labeled_ongoing_combat(self):
        support = {'partial_regular': {24: ['conditional_extra_draw'], 85: ['acquisition_card_grant']}}
        result = build_catalog([{'id': 24, 'name': '龙脉传承'}, {'id': 85, 'name': '云剑唤雨'}], [],
                               localization({}), runtime_support=support)
        for entry in result['entries']:
            self.assertEqual(entry['phases'], support['partial_regular'][entry['id']])
            self.assertFalse(entry['execution']['complete_effect'])
            self.assertFalse(entry['execution']['current_server_rules_verified'])
        rendered = render_markdown(result)
        self.assertIn('首轮/突破额外抽牌', rendered)
        self.assertIn('取得时获得牌', rendered)
        self.assertNotIn('持续战斗机制', rendered)
