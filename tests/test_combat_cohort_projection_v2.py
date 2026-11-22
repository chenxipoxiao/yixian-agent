from copy import deepcopy
import unittest
from yixian.combat_cohort_projection_v2 import project_record,start_context
from yixian.replays import game_key
from tests.test_replays import sample


class CohortProjectionTests(unittest.TestCase):
    def fixture(self):
        record=sample();d=record['data'];d.update(version='001.0008.0005',gameMode=3,seasonMec=10)
        t=d['roundStats'][0];t['p1']['publicData']['characterId']=1000003
        for slot in ('p1','p2'):
            public=t[slot]['publicData'];public['isMirror']=False
            public['lastRoundData'].update(handCards=[123,456],talentDatas={},privateTalentDatas={})
        return record,{'game_id':game_key(d['gameId']),'split':'train','raw_sha256':'a'*64,
                       'archive':'1000.tar.zst','member':'1000/1001_p0.json'}

    def test_postbattle_and_current_private_cannot_change_start_context(self):
        r,s=self.fixture();turn=r['data']['roundStats'][0]
        a=start_context(turn,s,r['data']);changed=deepcopy(turn)
        changed['winnerId']='different';changed['p1']['publicData'].update(hp=999,destiny=999,talentTempDatas={'27':999})
        changed['p1']['privateData']={'handCards':[999]*30,'xianMoData':{'tempDatas':{'13007':7}},'privateTalentDatas':{'199':{'commonParams':[9,9,9]}}}
        self.assertEqual(a,start_context(changed,s,r['data']))
        self.assertNotIn('after_talent_counters',a['players'][0]);self.assertNotIn('season_engraving_input',a['players'][0])

    def test_missing_start_is_not_filled_from_current_private_state(self):
        r,s=self.fixture();t=r['data']['roundStats'][0];p=t['p1']['publicData']
        for key in ['handCards','talentDatas','privateTalentDatas']:p['lastRoundData'].pop(key)
        p.pop('isMirror');t['p1']['privateData']={'handCards':[1,2],'talentDatas':{},'privateTalentDatas':{}}
        c=start_context(t,s,r['data'])['players'][0]
        self.assertIsNone(c['hand_count']);self.assertIsNone(c['is_mirror']);self.assertFalse(c['hand_values_are_numeric'])
        self.assertIsNone(c['start_extensions']['talentDatas']);self.assertIsNone(c['start_extensions']['privateTalentDatas'])

    def test_only_reviewed_start_parameter_keys_are_projected(self):
        r,s=self.fixture();t=r['data']['roundStats'][0];st=t['p1']['publicData']['lastRoundData']
        st['talentDatas']={'189':{'commonParams':[123]},'1':{'private':'omit'}}
        st['privateTalentDatas']={'199':{'commonParams':[0,123,456]},'2':{'private':'omit'}}
        before=deepcopy(r);c=start_context(t,s,r['data'])['players'][0]
        self.assertEqual(list(c['start_extensions']['talentDatas']),['189'])
        self.assertEqual(list(c['start_extensions']['privateTalentDatas']),['199'])
        self.assertEqual(c['hand_count'],2);self.assertNotIn('handCards',c);self.assertEqual(r,before)

    def test_empty_and_missing_parameters_remain_distinct(self):
        r,s=self.fixture();t=r['data']['roundStats'][0];t.pop('battleParams',None)
        self.assertIsNone(start_context(t,s,r['data'])['battle_params'])
        t['battleParams']=[];self.assertEqual(start_context(t,s,r['data'])['battle_params'],[])
        t['p1']['publicData']['lastRoundData']['handCards']=[True]
        self.assertFalse(start_context(t,s,r['data'])['players'][0]['hand_values_are_numeric'])

    def test_version_split_and_duplicate_round_guards(self):
        r,s=self.fixture()
        with self.assertRaises(ValueError):project_record(r,dict(s,split='test'))
        r['data']['version']='other'
        with self.assertRaisesRegex(ValueError,'version'):project_record(r,s)
        r['data']['version']='001.0008.0005';r['data']['roundStats'].append(deepcopy(r['data']['roundStats'][0]))
        with self.assertRaisesRegex(ValueError,'Duplicate round|chronological round order'):project_record(r,s)

if __name__=='__main__':unittest.main()
