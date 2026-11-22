"""Exercise CUDA training and checkpoints with synthetic data, not a game policy.

This verifies deployment only. It does not train Long Yao or produce game labels.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import tempfile
import time

import torch
from torch import nn


class DeploymentProbe(nn.Module):
    def __init__(self):
        super().__init__()
        self.embedding = nn.Embedding(10000, 384)
        block = nn.TransformerEncoderLayer(
            d_model=384, nhead=8, dim_feedforward=1536,
            dropout=0.0, batch_first=True, norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(block, 8, enable_nested_tensor=False)
        self.policy = nn.Linear(384, 256)

    def forward(self, cards):
        return self.policy(self.encoder(self.embedding(cards)).mean(dim=1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError('Use a new report path; previous evidence is preserved')
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA is not available to PyTorch')

    torch.manual_seed(91011)
    torch.set_num_threads(4)
    device = torch.device('cuda:0')
    model = DeploymentProbe().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    scaler = torch.amp.GradScaler('cuda')
    cards = torch.randint(0, 10000, (16, 64), device=device)
    targets = torch.randint(0, 256, (16,), device=device)
    before = model.policy.weight.detach().clone()
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize()
    start = time.perf_counter()
    losses = []
    for _ in range(8):
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device_type='cuda', dtype=torch.float16):
            logits = model(cards)
            loss = nn.functional.cross_entropy(logits, targets)
        if not torch.isfinite(loss):
            raise RuntimeError('Non-finite loss')
        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        for parameter in model.parameters():
            if parameter.grad is not None and not torch.isfinite(parameter.grad).all():
                raise RuntimeError('Non-finite gradient')
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(optimizer)
        scaler.update()
        losses.append(float(loss.detach().cpu()))
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - start
    changed = not torch.equal(before, model.policy.weight.detach())
    if not changed:
        raise RuntimeError('Optimizer did not change model parameters')

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='gpu-checkpoint-', dir=args.out.parent) as temporary:
        checkpoint = Path(temporary) / 'probe.pt'
        torch.save({'model': model.state_dict(), 'optimizer': optimizer.state_dict()}, checkpoint)
        restored = torch.load(checkpoint, map_location='cpu', weights_only=True)
        checkpoint_exact = all(torch.equal(value.cpu(), restored['model'][key])
                               for key, value in model.state_dict().items())
        if not checkpoint_exact or not restored['optimizer']['state']:
            raise RuntimeError('Model or optimizer checkpoint verification failed')

    properties = torch.cuda.get_device_properties(device)
    report = {
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'synthetic_gpu_deployment_probe_not_game_training',
        'passed': True,
        'python': platform.python_version(),
        'torch': torch.__version__,
        'cuda_runtime': torch.version.cuda,
        'gpu': properties.name,
        'compute_capability': list(torch.cuda.get_device_capability(device)),
        'gpu_memory_mib': round(properties.total_memory / 2**20),
        'parameter_count': sum(parameter.numel() for parameter in model.parameters()),
        'batch_size': 16, 'sequence_length': 64, 'optimizer_steps': 8,
        'precision': 'fp16 autocast with gradient scaling',
        'elapsed_seconds_including_initialization': elapsed,
        'peak_allocated_mib': round(torch.cuda.max_memory_allocated() / 2**20, 1),
        'losses': losses,
        'parameters_changed': changed,
        'checkpoint_exact': checkpoint_exact,
        'full_match_training_started': False,
    }
    args.out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
