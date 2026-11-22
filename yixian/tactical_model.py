"""v3 rule-aware, character-independent order PROPOSAL, not the battle judge.

The numerical search consumes proposals; no neural score is a combat outcome.
An S1 warm start reuses exact ID-aligned parameters, not optimizer/RNG state.
"""
from __future__ import annotations

import torch
from torch import nn

from .order_model import BoardOrderPolicy
from .tactical_rules import FEATURE_DIM


class TacticalProposalPolicy(BoardOrderPolicy):
    def __init__(self, vocabulary_size, *, rule_features, width=256, layers=6,
                 heads=8, dropout=.1):
        super().__init__(vocabulary_size, width=width, layers=layers, heads=heads, dropout=dropout)
        features = torch.as_tensor(rule_features, dtype=torch.float32)
        if features.shape != (vocabulary_size, FEATURE_DIM) or not torch.isfinite(features).all():
            raise ValueError('Invalid rule feature matrix')
        if features[0].count_nonzero():
            raise ValueError('Padding card must have no features')
        self.register_buffer('rule_features', features.clone())
        self.rule_projection = nn.Linear(FEATURE_DIM, width, bias=False)
        # Preserve S1 outputs on initialization; learn a residual from real data.
        nn.init.zeros_(self.rule_projection.weight)

    def card_vectors(self, tokens):
        return self.cards(tokens) + self.rule_projection(self.rule_features[tokens])

    def forward(self, candidates, prefix, available):
        if candidates.ndim != 2 or candidates.shape[1] != 8 or prefix.shape != candidates.shape:
            raise ValueError('Expected eight-slot candidate and prefix tensors')
        if available.dtype != torch.bool or available.shape != candidates.shape:
            raise ValueError('Expected explicit occurrence mask')
        if not available.any(dim=1).all() or (available & candidates.eq(0)).any():
            raise ValueError('At least one non-padding legal occurrence is required')
        active = candidates.ne(0)
        context = self.steps(prefix.ne(0).sum(dim=1))[:, None] + self.types.weight[0]
        bag = self.card_vectors(candidates) + self.types.weight[1] + self.used(available.long())
        history = self.card_vectors(prefix) + self.prefix_positions.weight[None] + self.types.weight[2]
        tokens = torch.cat((context, bag, history), dim=1)
        padding = torch.cat((torch.zeros((len(candidates), 1), dtype=torch.bool, device=candidates.device),
                             ~active, prefix.eq(0)), dim=1)
        encoded = self.encoder(tokens, src_key_padding_mask=padding)
        return self.pointer(encoded[:, 1:9]).squeeze(-1).float().masked_fill(~available, -1e9)

    def warm_start(self, old_model, *, old_vocabulary, vocabulary):
        if len(vocabulary) != self.cards.num_embeddings-1 or len(set(vocabulary)) != len(vocabulary):
            raise ValueError('Invalid destination vocabulary')
        if len(old_vocabulary) != old_model.cards.num_embeddings-1 or len(set(old_vocabulary)) != len(old_vocabulary):
            raise ValueError('Invalid source vocabulary')
        source, destination = old_model.state_dict(), self.state_dict()
        with torch.no_grad():
            for name, tensor in source.items():
                if name == 'cards.weight':
                    continue
                if name not in destination or tensor.shape != destination[name].shape:
                    raise ValueError(f'Incompatible warm-start architecture: {name}')
                destination[name].copy_(tensor)
            mapping = {card: i+1 for i, card in enumerate(old_vocabulary)}
            reused = 0
            for i, card in enumerate(vocabulary, 1):
                if card in mapping:
                    self.cards.weight[i].copy_(source['cards.weight'][mapping[card]])
                    reused += 1
            self.cards.weight[0].zero_()
        return {'reused_card_embeddings': reused, 'new_card_embeddings': len(vocabulary)-reused,
                'rule_projection_initialized_zero': not bool(self.rule_projection.weight.count_nonzero()),
                'optimizer_restored': False, 'exact_resume': False,
                'new_character_or_patch_strength_verified': False}
