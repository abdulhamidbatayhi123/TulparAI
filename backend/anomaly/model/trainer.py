"""
Training loop for the anomaly-detection autoencoder.

Trains only on NORMAL data so the model learns what 'healthy behaviour'
looks like. Includes early stopping, loss logging, and model checkpointing.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from backend.anomaly.model.autoencoder import Autoencoder
import backend.anomaly.config as config


@dataclass
class TrainHistory:
    """Stores training metrics per epoch."""
    train_losses: list[float] = field(default_factory=list)
    val_losses: list[float] = field(default_factory=list)
    best_epoch: int = 0
    best_val_loss: float = float("inf")
    elapsed_seconds: float = 0.0


def train_autoencoder(
    X_train: np.ndarray,
    X_val: np.ndarray | None = None,
    epochs: int = config.EPOCHS,
    batch_size: int = config.BATCH_SIZE,
    lr: float = config.LEARNING_RATE,
    patience: int = config.PATIENCE,
    model_path: str | None = None,
) -> tuple[Autoencoder, TrainHistory]:
    """
    Train the autoencoder on normal-only data.

    Args:
        X_train: (N, input_dim) normalised feature matrix — NORMAL data only
        X_val:   (M, input_dim) validation split (optional; auto-split if None)
        epochs:  max training epochs
        batch_size: mini-batch size
        lr:      learning rate
        patience: early-stopping patience
        model_path: where to save best weights

    Returns:
        (trained_model, history)
    """
    if model_path is None:
        model_path = os.path.join(config.MODEL_DIR, "autoencoder_best.pt")

    # ── Auto-split if no validation set provided ──
    if X_val is None:
        n = len(X_train)
        split = int(n * (1 - config.VALIDATION_SPLIT))
        idx = np.random.permutation(n)
        X_train, X_val = X_train[idx[:split]], X_train[idx[split:]]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[trainer] device = {device}")

    # ── Tensors & DataLoaders ──
    train_tensor = torch.tensor(X_train, dtype=torch.float32)
    val_tensor = torch.tensor(X_val, dtype=torch.float32)

    train_loader = DataLoader(
        TensorDataset(train_tensor, train_tensor),
        batch_size=batch_size,
        shuffle=True,
    )
    val_loader = DataLoader(
        TensorDataset(val_tensor, val_tensor),
        batch_size=batch_size,
    )

    # ── Model, Loss, Optimiser ──
    input_dim = X_train.shape[1]
    model = Autoencoder(
        input_dim=input_dim,
        encoding_dim=config.ENCODING_DIM,
        hidden_dims=config.HIDDEN_DIMS,
        dropout=config.DROPOUT_RATE,
    ).to(device)

    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=5
    )

    history = TrainHistory()
    wait = 0
    t0 = time.time()

    for epoch in range(1, epochs + 1):
        # ── Train ──
        model.train()
        epoch_loss = 0.0
        for x_batch, _ in train_loader:
            x_batch = x_batch.to(device)
            x_hat = model(x_batch)
            loss = criterion(x_hat, x_batch)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item() * x_batch.size(0)
        train_loss = epoch_loss / len(train_tensor)

        # ── Validate ──
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for x_batch, _ in val_loader:
                x_batch = x_batch.to(device)
                x_hat = model(x_batch)
                loss = criterion(x_hat, x_batch)
                val_loss += loss.item() * x_batch.size(0)
        val_loss /= len(val_tensor)

        scheduler.step(val_loss)

        history.train_losses.append(train_loss)
        history.val_losses.append(val_loss)

        if epoch % 10 == 0 or epoch == 1:
            print(
                f"  Epoch {epoch:>3d}/{epochs} | "
                f"train_loss={train_loss:.6f} | val_loss={val_loss:.6f}"
            )

        # ── Early stopping ──
        if val_loss < history.best_val_loss:
            history.best_val_loss = val_loss
            history.best_epoch = epoch
            wait = 0
            torch.save(model.state_dict(), model_path)
        else:
            wait += 1
            if wait >= patience:
                print(f"  Early stopping at epoch {epoch} (best={history.best_epoch})")
                break

    history.elapsed_seconds = time.time() - t0

    # Load best weights
    model.load_state_dict(torch.load(model_path, weights_only=True))
    model.eval()

    print(
        f"[trainer] Done in {history.elapsed_seconds:.1f}s — "
        f"best val_loss={history.best_val_loss:.6f} at epoch {history.best_epoch}"
    )
    return model, history
