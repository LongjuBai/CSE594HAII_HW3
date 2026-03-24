#!/usr/bin/env python3
"""Train a classifier for counselor-response appropriateness and run study inference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline

LABEL_APPROPRIATE = "appropriate"
LABEL_PROBLEMATIC = "problematic"


def make_pipeline(seed: int) -> Pipeline:
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 1),
                    min_df=2,
                    max_df=0.98,
                    max_features=15,
                    sublinear_tf=True,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=3000,
                    solver="liblinear",
                    class_weight="balanced",
                    C=0.5,
                    random_state=seed,
                ),
            ),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and run counselor-response model.")
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--train", type=Path, default=root / "data" / "train_dataset.csv")
    parser.add_argument("--study", type=Path, default=root / "data" / "study_dataset.csv")
    parser.add_argument("--model-out", type=Path, default=root / "models" / "counselor_tfidf_logreg.joblib")
    parser.add_argument(
        "--study-out",
        type=Path,
        default=root / "data" / "study_dataset_final.csv",
        help="Study dataset with model output columns filled.",
    )
    parser.add_argument("--outputs-dir", type=Path, default=root / "outputs")
    parser.add_argument("--seed", type=int, default=594)
    args = parser.parse_args()

    args.outputs_dir.mkdir(parents=True, exist_ok=True)
    args.model_out.parent.mkdir(parents=True, exist_ok=True)

    train_df = pd.read_csv(args.train)
    study_df = pd.read_csv(args.study)

    for col in ["input_text", "ground_truth_binary"]:
        if col not in train_df.columns:
            raise ValueError(f"Missing required train column: {col}")
    for col in ["input_text", "ground_truth_binary", "ground_truth"]:
        if col not in study_df.columns:
            raise ValueError(f"Missing required study column: {col}")

    x_train = train_df["input_text"].astype(str).values
    y_train = train_df["ground_truth_binary"].astype(int).values

    model = make_pipeline(seed=args.seed)

    cv_scores = cross_val_score(model, x_train, y_train, cv=5, scoring="f1")

    model.fit(x_train, y_train)

    x_study = study_df["input_text"].astype(str).values
    y_true = study_df["ground_truth_binary"].astype(int).values

    y_pred = model.predict(x_study)
    y_prob_appropriate = model.predict_proba(x_study)[:, 1]

    pred_labels = np.where(y_pred == 1, LABEL_APPROPRIATE, LABEL_PROBLEMATIC)

    # Fill assignment-required columns.
    study_out = study_df.copy()
    study_out["model_output"] = pred_labels
    study_out["model_probability"] = np.round(y_prob_appropriate, 4)
    study_out["ai_assistance"] = [
        f"AI suggests '{label}' (P(appropriate)={prob:.2f})."
        for label, prob in zip(pred_labels, y_prob_appropriate)
    ]

    # Keep a blank column in case human-rating based evaluation is used later.
    if "human_rating_of_model_output" not in study_out.columns:
        study_out["human_rating_of_model_output"] = ""

    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    cm = confusion_matrix(y_true, y_pred)

    metrics = {
        "study_accuracy": round(float(accuracy), 4),
        "study_precision": round(float(precision), 4),
        "study_recall": round(float(recall), 4),
        "study_f1": round(float(f1), 4),
        "study_n": int(len(study_df)),
        "cv_f1_mean": round(float(np.mean(cv_scores)), 4),
        "cv_f1_std": round(float(np.std(cv_scores)), 4),
        "confusion_matrix": {
            "tn": int(cm[0, 0]),
            "fp": int(cm[0, 1]),
            "fn": int(cm[1, 0]),
            "tp": int(cm[1, 1]),
        },
    }

    args.study_out.parent.mkdir(parents=True, exist_ok=True)
    study_out.to_csv(args.study_out, index=False)
    joblib.dump(model, args.model_out)

    metrics_path = args.outputs_dir / "model_metrics.json"
    with metrics_path.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    report_text = classification_report(
        y_true,
        y_pred,
        target_names=[LABEL_PROBLEMATIC, LABEL_APPROPRIATE],
        digits=4,
        zero_division=0,
    )
    (args.outputs_dir / "classification_report.txt").write_text(report_text, encoding="utf-8")

    cm_df = pd.DataFrame(
        cm,
        index=["true_problematic", "true_appropriate"],
        columns=["pred_problematic", "pred_appropriate"],
    )
    cm_df.to_csv(args.outputs_dir / "confusion_matrix.csv")

    preview_cols = [
        "trial_id",
        "topic",
        "risk_level",
        "input_client_statement",
        "input_counselor_response",
        "ground_truth",
        "model_output",
        "model_probability",
        "ai_assistance",
    ]
    study_out[preview_cols].head(8).to_csv(args.outputs_dir / "sample_model_outputs.csv", index=False)

    print(f"Saved model: {args.model_out}")
    print(f"Saved study predictions: {args.study_out}")
    print(f"Saved metrics: {metrics_path}")
    print(f"Study accuracy: {accuracy:.4f}, F1: {f1:.4f}")


if __name__ == "__main__":
    main()
