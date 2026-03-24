import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
HW2_DATASET = ROOT_DIR / "hw2" / "data" / "study_dataset_final.csv"
DB_PATH = Path(os.environ.get("STUDY_DB_PATH", str(BASE_DIR / "data" / "study.db")))
STATIC_DIR = BASE_DIR / "static"
EXPORT_DIR = BASE_DIR / "exports"

STUDY_TITLE = "Counselor Response Appropriateness Study"
COURSE_TITLE = "CSE 594 Human AI Interaction"
TRIALS_PER_PARTICIPANT = 10
ALLOW_SAME_WORKER_BOTH_CONDITIONS = False

CONDITIONS = {
    "baseline": {
        "label": "Baseline",
        "description": "Judge each counselor response without AI assistance.",
        "show_ai_panel": False,
    },
    "ai": {
        "label": "AI-Assisted",
        "description": "You may optionally reveal the AI suggestion before deciding.",
        "show_ai_panel": True,
    },
}

CONFIDENCE_OPTIONS = [1, 2, 3, 4, 5]
WORKLOAD_OPTIONS = [1, 2, 3, 4, 5]
