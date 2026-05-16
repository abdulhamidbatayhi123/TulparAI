"""
train.py — End-to-end training script for the TulparAI anomaly detector.

Steps:
  1. Generate synthetic normal training data
  2. Build feature matrix & fit scaler
  3. Train autoencoder
  4. Compute anomaly threshold from training reconstruction errors
  5. Save model + scaler + threshold
  6. Evaluate on test set (with injected anomalies)

Run with:
    cd backend
    python -m backend.anomaly.train
"""

import os
import sys
import json
import numpy as np
import torch

import backend.anomaly.config as config
from backend.anomaly.data.synthetic import generate_dataset
from backend.anomaly.features.pipeline import build_feature_matrix, FeatureScaler
from backend.anomaly.model.trainer import train_autoencoder
from backend.anomaly.model.detector import AnomalyDetector
from backend.anomaly.model.autoencoder import Autoencoder


def main():
    print("=" * 60)
    print("  TulparAI Anomaly Detection — Training Pipeline")
    print("=" * 60)

    # ── 1. Generate Data ──
    print("\n[1/6] Generating synthetic training data (normal only)...")
    profiles, train_logs, train_labels = generate_dataset(days=90, anomaly_ratio=0.0, seed=42)
    print(f"  → {len(profiles)} athletes × 90 days = {len(train_logs)} normal logs")

    print("\n[2/6] Generating test data (with ~15% anomalies)...")
    _, test_logs, test_labels = generate_dataset(days=30, anomaly_ratio=0.15, seed=99)
    n_anomalies = sum(1 for l in test_labels if l["is_anomaly"])
    print(f"  → {len(test_logs)} test logs ({n_anomalies} anomalies, {len(test_logs) - n_anomalies} normal)")

    # Save profiles
    profiles_path = os.path.join(config.DATA_DIR, "sample_profiles.json")
    with open(profiles_path, "w", encoding="utf-8") as f:
        json.dump([p.model_dump(mode="json") for p in profiles], f, indent=2, ensure_ascii=False)
    print(f"  → Profiles saved to {profiles_path}")

    # ── 3. Feature Engineering ──
    print("\n[3/6] Building feature matrices...")
    X_train = build_feature_matrix(profiles, train_logs)
    X_test = build_feature_matrix(profiles, test_logs)
    print(f"  → Train shape: {X_train.shape}, Test shape: {X_test.shape}")

    # Scale features
    scaler = FeatureScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # ── 4. Train Autoencoder ──
    print("\n[4/6] Training autoencoder...")
    model, history = train_autoencoder(
        X_train_scaled,
        epochs=config.EPOCHS,
        batch_size=config.BATCH_SIZE,
        lr=config.LEARNING_RATE,
        patience=config.PATIENCE,
    )

    # ── 5. Compute Threshold ──
    print("\n[5/6] Computing anomaly threshold...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    with torch.no_grad():
        x_tensor = torch.tensor(X_train_scaled, dtype=torch.float32).to(device)
        train_errors = model.reconstruction_error(x_tensor).cpu().numpy()

    threshold = float(np.percentile(train_errors, config.ANOMALY_THRESHOLD_PERCENTILE))
    print(f"  → Threshold (p{config.ANOMALY_THRESHOLD_PERCENTILE}): {threshold:.6f}")
    print(f"  → Mean train error: {train_errors.mean():.6f}")
    print(f"  → Max train error:  {train_errors.max():.6f}")

    # ── 6. Save Everything ──
    print("\n[6/6] Saving model, scaler, and threshold...")
    detector = AnomalyDetector(model=model, scaler=scaler, threshold=threshold, device=device)
    detector.save(config.MODEL_DIR)
    print(f"  → Saved to {config.MODEL_DIR}/")

    # ── Evaluate ──
    print("\n" + "=" * 60)
    print("  Evaluation on Test Set")
    print("=" * 60)

    # Reload to test persistence
    detector = AnomalyDetector.load(config.MODEL_DIR)

    profile_map = {p.athlete_id: p for p in profiles}
    true_positives = 0
    false_positives = 0
    true_negatives = 0
    false_negatives = 0

    anomaly_type_counts = {}

    for log, label in zip(test_logs, test_labels):
        profile = profile_map[log.athlete_id]
        result = detector.check(profile, log)

        actual = label["is_anomaly"]
        predicted = result.is_anomaly

        if actual and predicted:
            true_positives += 1
        elif not actual and predicted:
            false_positives += 1
        elif not actual and not predicted:
            true_negatives += 1
        else:
            false_negatives += 1

        if result.is_anomaly:
            t = result.anomaly_type or "unknown"
            anomaly_type_counts[t] = anomaly_type_counts.get(t, 0) + 1

    total = len(test_logs)
    accuracy = (true_positives + true_negatives) / total * 100
    precision = true_positives / max(1, true_positives + false_positives) * 100
    recall = true_positives / max(1, true_positives + false_negatives) * 100
    f1 = 2 * precision * recall / max(1, precision + recall)

    print(f"\n  Accuracy:  {accuracy:.1f}%")
    print(f"  Precision: {precision:.1f}%")
    print(f"  Recall:    {recall:.1f}%")
    print(f"  F1-Score:  {f1:.1f}")
    print(f"\n  TP={true_positives}  FP={false_positives}  TN={true_negatives}  FN={false_negatives}")

    if anomaly_type_counts:
        print("\n  Detected anomaly types:")
        for t, c in sorted(anomaly_type_counts.items(), key=lambda x: -x[1]):
            print(f"    {t:25s} → {c}")

    # Save training report
    report = {
        "epochs_trained": len(history.train_losses),
        "best_epoch": history.best_epoch,
        "best_val_loss": round(history.best_val_loss, 6),
        "threshold": round(threshold, 6),
        "elapsed_seconds": round(history.elapsed_seconds, 1),
        "evaluation": {
            "total_test": total,
            "accuracy": round(accuracy, 1),
            "precision": round(precision, 1),
            "recall": round(recall, 1),
            "f1": round(f1, 1),
            "tp": true_positives,
            "fp": false_positives,
            "tn": true_negatives,
            "fn": false_negatives,
        },
        "anomaly_types": anomaly_type_counts,
    }
    report_path = os.path.join(config.MODEL_DIR, "training_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Report saved to {report_path}")

    print("\n✅ Training complete!")


if __name__ == "__main__":
    main()
