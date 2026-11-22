import unittest
try:
    import torch
    from yixian.order_model import BoardOrderPolicy, reconstruction_loss
    from yixian.tactical_model import TacticalProposalPolicy
except ImportError:
    torch = None
from yixian.tactical_rules import TacticalCatalogue


@unittest.skipIf(torch is None, 'PyTorch is available on the training server')
class TacticalModelTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(2); torch.manual_seed(7)
        self.cat = TacticalCatalogue([{'id': i, 'attack': i*2} for i in range(1, 5)],
                                    rules_version='fixture', source_sha256='fixture')
        self.kw = dict(width=32, layers=1, heads=4, dropout=0.)
        self.model = TacticalProposalPolicy(5, rule_features=self.cat.matrix([1, 2, 3, 4]), **self.kw)
        self.bag = torch.tensor([[1, 2, 1, 3, 0, 0, 0, 0]])
        self.prefix = torch.zeros_like(self.bag); self.mask = self.bag.ne(0)

    def test_warm_start_exact_initial_scores_then_rule_branch_learns(self):
        old = BoardOrderPolicy(5, **self.kw).eval(); self.model.eval()
        result = self.model.warm_start(old, old_vocabulary=[1, 2, 3, 4], vocabulary=[1, 2, 3, 4])
        torch.testing.assert_close(old(self.bag, self.prefix, self.mask), self.model(self.bag, self.prefix, self.mask))
        self.assertFalse(result['exact_resume'])
        target = self.bag.eq(2)
        opt = torch.optim.AdamW(self.model.parameters(), lr=.001)
        opt.zero_grad(); reconstruction_loss(self.model(self.bag, self.prefix, self.mask), target).mean().backward()
        self.assertGreater(self.model.rule_projection.weight.grad.abs().sum().item(), 0)
        opt.step()
        baseline = self.model(self.bag, self.prefix, self.mask)
        with torch.no_grad(): self.model.rule_features[2, 4] += 2
        self.assertFalse(torch.allclose(baseline, self.model(self.bag, self.prefix, self.mask)))

    def test_warm_start_remaps_ids_instead_of_assuming_positions(self):
        old = BoardOrderPolicy(5, **self.kw)
        self.model.warm_start(old, old_vocabulary=[4, 3, 2, 1], vocabulary=[1, 2, 3, 4])
        torch.testing.assert_close(self.model.cards.weight[1], old.cards.weight[4])

    def test_permutation_equivariance_and_legal_seeded_proposals(self):
        from yixian.tactical_checkpoint import generate_proposals
        self.model.eval(); order = torch.tensor([2, 0, 3, 1, 7, 6, 5, 4])
        torch.testing.assert_close(self.model(self.bag[:, order], self.prefix, self.mask[:, order]),
                                  self.model(self.bag, self.prefix, self.mask)[:, order], atol=1e-5, rtol=1e-5)
        a = generate_proposals(self.model, [1, 2, 3, 4], [1, 2, 1], count=20, seed=7)
        self.assertEqual(a, generate_proposals(self.model, [1, 2, 3, 4], [1, 2, 1], count=20, seed=7))
        for board in a: self.assertCountEqual(board, [1, 2, 1])
        with self.assertRaises(ValueError): generate_proposals(self.model, [1, 2, 3, 4], [99])

    def test_checkpoint_requires_explicit_patch_and_replaces_old_feature_buffer(self):
        import hashlib
        from pathlib import Path
        import tempfile
        from yixian.research import contract_digest
        from yixian.tactical_rules import digest
        from yixian.tactical_checkpoint import load_tactical_checkpoint, SCOPE
        contract = {'schema_version': 3, 'scope': SCOPE, 'test_data_opened': False,
                    'battle_labels_used': False, 'source_sha256': {},
                    'vocabulary_digest': digest([1, 2, 3, 4]), 'model': self.kw,
                    'card_rule_fingerprint': self.cat.fingerprint}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'model.pt'
            torch.save({'contract': contract, 'contract_digest': contract_digest(contract),
                        'model': self.model.state_dict(), 'vocabulary': [1, 2, 3, 4]}, path)
            checksum = hashlib.sha256(path.read_bytes()).hexdigest()
            loaded, meta = load_tactical_checkpoint(path, root=folder, expected_sha256=checksum, catalogue=self.cat)
            self.assertFalse(meta['rule_patch_applied'])
            patched = TacticalCatalogue([{'id': i, 'attack': 99} for i in range(1, 5)], rules_version='new', source_sha256='new')
            with self.assertRaises(ValueError):
                load_tactical_checkpoint(path, root=folder, expected_sha256=checksum, catalogue=patched)
            loaded, meta = load_tactical_checkpoint(path, root=folder, expected_sha256=checksum,
                                                   catalogue=patched, allow_rule_patch=True)
            self.assertTrue(meta['rule_patch_applied'])
            torch.testing.assert_close(loaded.rule_features, torch.tensor(patched.matrix([1, 2, 3, 4])))
