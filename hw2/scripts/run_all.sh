#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_NAME="counseling"

conda run -n "$ENV_NAME" python "$ROOT_DIR/scripts/generate_counselor_dataset.py" --n-train 3200 --n-study 240 --seed 594
conda run -n "$ENV_NAME" python "$ROOT_DIR/scripts/train_counselor_model.py" --seed 594
conda run -n "$ENV_NAME" python "$ROOT_DIR/scripts/evaluate_counselor_model.py"

echo "All done. Check $ROOT_DIR/data and $ROOT_DIR/outputs"
