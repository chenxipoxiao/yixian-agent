from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from yixian.corpus_merge import compose,freeze_corpus,sha
from yixian.order_data import CHARACTER,SCOPE,SPLIT_SALT,VERSION,game_split,validate_splits


class CorpusMergeTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        self.minimum={'train':2,'validation':2,'test':1}
        self.registry={'corpora':[self.make_source('old',False),self.make_source('new',True)]}

    def make_source(self,name,fresh):
        directory=self.root/name
        directory.mkdir()
        groups={}
        for index in range(1000):
            group=f'fixture-{name}-{index}'
            groups.setdefault(game_split(group),group)
            if len(groups)==3:break
        rows=[]
        for split,group in groups.items():
            board=[1,2,1,3]
            rows.append({'id':hashlib.sha256(json.dumps([group,board],separators=(',',':')).encode()).hexdigest(),
                'game_id':group,'split':split,'board':board,'scope':SCOPE,
                'character_id':CHARACTER,'source_rules_version':VERSION,'season_mec':10,
                'recorded_action_trajectory':False})
        hashes={}
        for split in ('train','validation','test'):
            path=directory/f'{split}.jsonl'
            path.write_text(''.join(json.dumps(row)+'\n' for row in rows if row['split']==split),encoding='utf-8')
            hashes[split]=sha(path)
        manifest={'scope':SCOPE,'rules_version':VERSION,'split_salt':SPLIT_SALT,
            'character_id':CHARACTER,'season_mec':10,'vocabulary':[1,2,3],
            'card_config_sha256':'a'*64,'revision':'b'*40,'archives':[],
            'split_summary':validate_splits(rows),'split_sha256':hashes,
            'excluded_previously_inspected_games':[]}
        (directory/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
        return {'id':name,'directory':name,'manifest_sha256':sha(directory/'manifest.json'),
            'allowed_roles_in_next_experiment':['train','validation','test'] if fresh else ['train','validation'],
            'test_use_status':'never_model_evaluated' if fresh else 'previously_evaluated_retired_from_new_final_test'}

    def test_retired_test_is_excluded_while_original_training_roles_are_preserved(self):
        rows,manifest=compose(self.registry,self.root,self.minimum)
        retired=json.loads((self.root/'old/test.jsonl').read_text())['game_id']
        self.assertNotIn(retired,{row['game_id'] for row in rows})
        self.assertIn(retired,manifest['excluded_previously_inspected_games'])
        self.assertEqual(manifest['split_summary']['games'],{'train':2,'validation':2,'test':1})
        self.assertEqual(manifest['retired_test_game_count'],1)
        self.assertEqual(manifest['test_model_evaluations'],0)

    def test_used_test_cannot_be_reauthorized_as_fresh_by_adding_role(self):
        self.registry['corpora'][0]['allowed_roles_in_next_experiment'].append('test')
        with self.assertRaisesRegex(ValueError,'previously evaluated'):
            compose(self.registry,self.root,self.minimum)

    def test_duplicate_source_games_cannot_inflate_sample_size(self):
        self.registry['corpora'][1]={**self.registry['corpora'][0],'id':'copy'}
        with self.assertRaisesRegex(ValueError,'overlap'):
            compose(self.registry,self.root,self.minimum)

    def test_changed_partition_is_rejected(self):
        with (self.root/'new/test.jsonl').open('a') as stream:stream.write('\n')
        with self.assertRaisesRegex(ValueError,'checksum'):
            compose(self.registry,self.root,self.minimum)

    def test_changed_vocabulary_is_rejected_even_with_registered_manifest(self):
        path=self.root/'new/manifest.json'
        manifest=json.loads(path.read_text())
        manifest['vocabulary']=[1,2,3,4]
        path.write_text(json.dumps(manifest))
        self.registry['corpora'][1]['manifest_sha256']=sha(path)
        with self.assertRaisesRegex(ValueError,'vocabulary'):
            compose(self.registry,self.root,self.minimum)

    def test_acquisition_exclusions_do_not_drop_approved_parent_training_groups(self):
        group=json.loads((self.root/'old/train.jsonl').read_text())['game_id']
        path=self.root/'new/manifest.json'
        manifest=json.loads(path.read_text())
        manifest['excluded_previously_inspected_games']=[group,'diagnostic-only-game']
        path.write_text(json.dumps(manifest))
        self.registry['corpora'][1]['manifest_sha256']=sha(path)
        rows,merged=compose(self.registry,self.root,self.minimum)
        self.assertIn(group,{row['game_id'] for row in rows})
        self.assertNotIn(group,merged['excluded_previously_inspected_games'])
        self.assertIn('diagnostic-only-game',merged['excluded_previously_inspected_games'])

    def test_below_game_minimum_does_not_create_frozen_corpus(self):
        registry=self.root/'registry.json'
        registry.write_text(json.dumps(self.registry))
        output=self.root/'frozen'
        with self.assertRaisesRegex(ValueError,'Insufficient'):
            freeze_corpus(registry,output,root=self.root,minimum_games={**self.minimum,'test':2})
        self.assertFalse(output.exists())

    def test_frozen_corpus_hashes_match_and_existing_output_is_preserved(self):
        registry=self.root/'registry.json'
        registry.write_text(json.dumps(self.registry))
        output=self.root/'frozen'
        manifest=freeze_corpus(registry,output,root=self.root,minimum_games=self.minimum)
        for split,digest in manifest['split_sha256'].items():
            self.assertEqual(sha(output/f'{split}.jsonl'),digest)
        self.assertEqual(sha(output/'source-registry.json'),sha(registry))
        original=sha(output/'manifest.json')
        with self.assertRaises(FileExistsError):
            freeze_corpus(registry,output,root=self.root,minimum_games=self.minimum)
        self.assertEqual(sha(output/'manifest.json'),original)


if __name__=='__main__':unittest.main()
