#!/usr/bin/env python3
"""Evaluate model outputs on the counselor study dataset and produce error analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score


def map_error_theme(pattern: str) -> str:
    mapping = {
        "invalidation": "Empathy/validation failure",
        "judgmental_blame": "Empathy/validation failure",
        "premature_directive": "Over-directive counseling",
        "toxic_positivity": "Subtle minimization",
        "boundary_crossing": "Boundary and role violation",
        "safety_underreaction": "Safety underreaction",
        "confidentiality_breach": "Confidentiality/ethics violation",
        "coercive_control": "Coercive control",
        "validation_open_question": "Missed good empathic response",
        "reflective_collaboration": "Missed collaborative response",
        "strengths_reframe": "Missed subtle supportive response",
        "safety_check_referral": "Missed appropriate safety action",
        "safety_plan_collaboration": "Missed safety planning response",
    }
    return mapping.get(pattern, "Other")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate and analyze counselor model outputs.")
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--study", type=Path, default=root / "data" / "study_dataset_final.csv")
    parser.add_argument("--out-dir", type=Path, default=root / "outputs")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.study)
    required_cols = [
        "ground_truth_binary",
        "ground_truth",
        "model_output",
        "response_pattern",
        "topic",
        "risk_level",
        "difficulty",
    ]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    y_true = df["ground_truth_binary"].astype(int)
    y_pred = (df["model_output"] == "appropriate").astype(int)

    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)

    errors = df[y_true != y_pred].copy()
    errors["error_theme"] = errors["response_pattern"].astype(str).map(map_error_theme)

    if len(errors) == 0:
        error_dist = pd.DataFrame(columns=["error_theme", "count", "percent_of_errors"])
    else:
        error_dist = (
            errors.groupby("error_theme")
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
        )
        error_dist["percent_of_errors"] = (error_dist["count"] / len(errors) * 100).round(2)

    error_by_pattern = (
        errors.groupby("response_pattern")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    if len(errors) > 0:
        error_by_pattern["percent_of_errors"] = (error_by_pattern["count"] / len(errors) * 100).round(2)
    else:
        error_by_pattern["percent_of_errors"] = []

    error_by_risk = (
        errors.groupby("risk_level")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    if len(errors) > 0:
        error_by_risk["percent_of_errors"] = (error_by_risk["count"] / len(errors) * 100).round(2)
    else:
        error_by_risk["percent_of_errors"] = []

    error_by_difficulty = (
        errors.groupby("difficulty")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    if len(errors) > 0:
        error_by_difficulty["percent_of_errors"] = (error_by_difficulty["count"] / len(errors) * 100).round(2)
    else:
        error_by_difficulty["percent_of_errors"] = []

    error_by_topic = (
        errors.groupby("topic")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    if len(errors) > 0:
        error_by_topic["percent_of_errors"] = (error_by_topic["count"] / len(errors) * 100).round(2)
    else:
        error_by_topic["percent_of_errors"] = []

    error_examples = errors[
        [
            "trial_id",
            "topic",
            "risk_level",
            "difficulty",
            "response_pattern",
            "input_client_statement",
            "input_counselor_response",
            "ground_truth",
            "model_output",
            "model_probability",
        ]
    ].head(50)

    metrics = {
        "study_accuracy": round(float(accuracy), 4),
        "study_precision": round(float(precision), 4),
        "study_recall": round(float(recall), 4),
        "study_f1": round(float(f1), 4),
        "num_study_trials": int(len(df)),
        "num_errors": int(len(errors)),
        "error_rate": round(float(1 - accuracy), 4),
    }

    (args.out_dir / "evaluation_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    error_dist.to_csv(args.out_dir / "error_distribution.csv", index=False)
    error_by_pattern.to_csv(args.out_dir / "error_by_pattern.csv", index=False)
    error_by_risk.to_csv(args.out_dir / "error_by_risk.csv", index=False)
    error_by_difficulty.to_csv(args.out_dir / "error_by_difficulty.csv", index=False)
    error_by_topic.to_csv(args.out_dir / "error_by_topic.csv", index=False)
    error_examples.to_csv(args.out_dir / "error_examples.csv", index=False)

    summary_lines = [
        "# Evaluation Summary",
        "",
        f"- Study trials: {len(df)}",
        f"- Accuracy: {accuracy:.4f}",
        f"- Precision: {precision:.4f}",
        f"- Recall: {recall:.4f}",
        f"- F1: {f1:.4f}",
        f"- Errors: {len(errors)} ({(1 - accuracy) * 100:.2f}%)",
        "",
        "## Top Error Themes",
    ]

    if len(error_dist) == 0:
        summary_lines.append("- No model errors found on this split.")
    else:
        for _, row in error_dist.head(8).iterrows():
            summary_lines.append(
                f"- {row['error_theme']}: {int(row['count'])} ({row['percent_of_errors']:.2f}% of errors)"
            )

    (args.out_dir / "evaluation_summary.md").write_text("\n".join(summary_lines), encoding="utf-8")

    print(f"Saved evaluation outputs to: {args.out_dir}")
    print(f"Accuracy={accuracy:.4f}, F1={f1:.4f}, Errors={len(errors)}")


if __name__ == "__main__":
    main()
