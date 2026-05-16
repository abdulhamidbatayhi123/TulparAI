"""
Autoencoder neural network for anomaly detection.

The encoder compresses a 28-dim feature vector down to an 8-dim latent code.
The decoder reconstructs it. High reconstruction error ⇒ anomaly.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class Autoencoder(nn.Module):
    """
    Symmetric deep autoencoder for athlete-behaviour anomaly detection.

    Architecture
    ────────────
    Encoder:  input_dim → 64 → 32 → encoding_dim
    Decoder:  encoding_dim → 32 → 64 → input_dim

    All hidden layers use LeakyReLU + BatchNorm + Dropout.
    Output uses Sigmoid (if data is min-max scaled) or Identity.
    """

    def __init__(
        self,
        input_dim: int = 28,
        encoding_dim: int = 8,
        hidden_dims: list[int] | None = None,
        dropout: float = 0.2,
    ):
        super().__init__()
        if hidden_dims is None:
            hidden_dims = [64, 32]

        self.input_dim = input_dim
        self.encoding_dim = encoding_dim

        # ── Build Encoder ──
        encoder_layers = []
        prev_dim = input_dim
        for h_dim in hidden_dims:
            encoder_layers += [
                nn.Linear(prev_dim, h_dim),
                nn.BatchNorm1d(h_dim),
                nn.LeakyReLU(0.2),
                nn.Dropout(dropout),
            ]
            prev_dim = h_dim
        encoder_layers.append(nn.Linear(prev_dim, encoding_dim))
        self.encoder = nn.Sequential(*encoder_layers)

        # ── Build Decoder (mirror) ──
        decoder_layers = []
        prev_dim = encoding_dim
        for h_dim in reversed(hidden_dims):
            decoder_layers += [
                nn.Linear(prev_dim, h_dim),
                nn.BatchNorm1d(h_dim),
                nn.LeakyReLU(0.2),
                nn.Dropout(dropout),
            ]
            prev_dim = h_dim
        decoder_layers.append(nn.Linear(prev_dim, input_dim))
        self.decoder = nn.Sequential(*decoder_layers)

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        return self.encoder(x)

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        return self.decoder(z)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        z = self.encode(x)
        x_hat = self.decode(z)
        return x_hat

    def reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
        """Per-sample MSE reconstruction error."""
        x_hat = self.forward(x)
        return torch.mean((x - x_hat) ** 2, dim=1)
