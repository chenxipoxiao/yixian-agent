"""Permutation-equivariant pointer policy for the board reconstruction task."""
from __future__ import annotations

import torch
from torch import nn


class BoardOrderPolicy(nn.Module):
    def __init__(self, vocabulary_size, *, width=256, layers=6, heads=8, dropout=.1):
        super().__init__()
        self.cards = nn.Embedding(vocabulary_size, width, padding_idx=0)
        self.types = nn.Embedding(3, width)
        self.prefix_positions = nn.Embedding(8, width)
        self.used = nn.Embedding(2, width)
        self.steps = nn.Embedding(9, width)
        block = nn.TransformerEncoderLayer(width, heads, width*4, dropout=dropout,
                                           batch_first=True, norm_first=True)
        self.encoder = nn.TransformerEncoder(block, layers, norm=nn.LayerNorm(width),
                                              enable_nested_tensor=False)
        self.pointer = nn.Sequential(nn.Linear(width, width), nn.GELU(), nn.Linear(width, 1))

    def forward(self, candidates, prefix, available):
        available = available.bool() & candidates.ne(0)
        if candidates.ndim != 2 or candidates.shape[1] != 8 or prefix.shape != candidates.shape:
            raise ValueError('Expected batched eight-slot candidates and prefix')
        if not available.any(dim=1).all():
            raise ValueError('Every observation needs a legal next card')
        context = self.steps(prefix.ne(0).sum(dim=1))[:, None] + self.types.weight[0]
        # Candidate tokens have no positional embedding. Shuffling the bag must
        # only permute the candidate scores, including identical-card copies.
        bag = self.cards(candidates) + self.types.weight[1] + self.used(available.long())
        positions = self.prefix_positions.weight[None]
        history = self.cards(prefix) + positions + self.types.weight[2]
        tokens = torch.cat([context, bag, history], dim=1)
        padding = torch.cat([torch.zeros_like(candidates[:, :1], dtype=torch.bool),
                             candidates.eq(0), prefix.eq(0)], dim=1)
        features = self.encoder(tokens, src_key_padding_mask=padding)
        scores = self.pointer(features[:, 1:9]).squeeze(-1).float()
        return scores.masked_fill(~available, -1e9)


def reconstruction_loss(logits, target_mask):
    """Marginalize all interchangeable occurrences of the desired card."""
    if logits.shape != target_mask.shape or not target_mask.any(dim=1).all():
        raise ValueError('Every row needs at least one matching target')
    if (logits[target_mask] <= -1e8).any():
        raise ValueError('A target cannot be an illegal action')
    correct = logits.masked_fill(~target_mask, -torch.inf)
    return torch.logsumexp(logits, dim=1) - torch.logsumexp(correct, dim=1)
