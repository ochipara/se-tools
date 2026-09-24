from dataclasses import dataclass
import torch
from torch import nn

@dataclass
class Batch:
    features: torch.Tensor
    labels: torch.Tensor

class Encoder(nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x

def train_step(
    model: Encoder,
    batch: Batch,
    optimizer: torch.optim.Optimizer,
) -> torch.Tensor:
    x = batch.features
    logits = model(x)
    loss = logits.sum()

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    return loss
