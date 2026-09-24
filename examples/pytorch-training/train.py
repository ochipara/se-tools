import torch
from torch import nn

class SubModule(nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x * 2

class Encoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.sub = SubModule()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.sub(x)
        return y

def train_step(model: Encoder, features: torch.Tensor):
    logits = model(features)
    loss = logits.sum()
    return loss

def main():
    model = Encoder()
    data = torch.randn(10, 10)
    train_step(model, data)
