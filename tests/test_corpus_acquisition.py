from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from yixian.corpus_acquisition import (archive_names, checked_metadata, prior_game_groups,
    AcquisitionBudget, acquisition_lock, daily_usage)
from yixian.order_data import SCOPE, SPLIT_SALT, VERSION, game_split


class CorpusAcquisitionTests(unittest.TestCase):
    def test_expansion_range_excludes_original_shards(self):
        original = set(archive_names(34498000, 8))
        expanded = set(archive_names(34490000, 12))
        self.assertFalse(original & expanded)
        for start,count in [(34499000,1),(34490001,1),(34490000,13)]:
            with self.assertRaises(ValueError): archive_names(start,count)

    def test_metadata_cannot_repeat_or_substitute_a_requested_shard(self):
        names = archive_names(34490000,2)
        infos = [{'path':name,'size':10,'lfs':{'oid':'a'*64}} for name in names]
        self.assertEqual(checked_metadata(infos[::-1],names),infos)
        with self.assertRaises(ValueError): checked_metadata([infos[0],infos[0]],names)
        with self.assertRaises(ValueError): checked_metadata(infos,names,cap=19)

    def test_excludes_all_prior_splits_and_checks_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            groups = [f'game-{n}' for n in range(100)]
            hashes = {}
            for split in ('train','validation','test'):
                path = root/f'{split}.jsonl'
                # No board/outcome field is needed to obtain the exclusion set.
                path.write_text(''.join(json.dumps({'game_id':group,'split':split})+'\n'
                    for group in groups if game_split(group)==split),encoding='utf-8')
                hashes[split] = hashlib.sha256(path.read_bytes()).hexdigest()
            (root/'manifest.json').write_text(json.dumps({'scope':SCOPE,'rules_version':VERSION,
                'split_salt':SPLIT_SALT,'split_sha256':hashes}),encoding='utf-8')
            excluded, provenance = prior_game_groups(root)
            self.assertEqual(excluded,set(groups))
            self.assertEqual(provenance['fields_used_from_prior_records'],['game_id','split'])
            (root/'test.jsonl').write_text('{}',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'checksum'): prior_game_groups(root)

    def test_parallel_reservations_never_exceed_batch_cap(self):
        with tempfile.TemporaryDirectory() as directory:
            budget = AcquisitionBudget(Path(directory),day_used=0,batch_limit=20,
                                       daily_limit=100,output_directory='fixture')
            def reserve(index):
                try: budget.reserve(f'{index}.tar.zst',10); return True
                except ValueError: return False
            with ThreadPoolExecutor(max_workers=4) as pool:
                accepted = list(pool.map(reserve,range(4)))
            self.assertEqual(sum(accepted),2)
            self.assertEqual(json.loads(budget.path.read_text())['reserved_bytes'],20)

    def test_daily_limit_and_failed_attempt_reservations_persist(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            budget=AcquisitionBudget(root/'ledgers',day_used=95,batch_limit=20,
                                     daily_limit=100,output_directory='fixture')
            budget.reserve('one.tar.zst',5)
            with self.assertRaises(ValueError): budget.reserve('one.tar.zst',5)
            self.assertEqual(daily_usage(root/'cache',root/'ledgers',budget.state['local_day']),5)

    def test_lock_refuses_overlapping_acquisition(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            with acquisition_lock(path):
                with self.assertRaises(FileExistsError):
                    with acquisition_lock(path): pass
            self.assertFalse((path/'.acquisition.lock').exists())


if __name__ == '__main__':
    unittest.main()
