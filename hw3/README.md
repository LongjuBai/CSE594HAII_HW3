# HW3 Study App

This folder contains a custom MTurk-ready web app for Assignment 3 built on top of the HW2 counselor-training dataset.

## What it supports
- Baseline condition without AI assistance
- AI-assisted condition with optional reveal of static AI output
- Backend data logging with SQLite
- Worker / assignment / HIT tracking
- Randomized trial assignment so workers do not all get the exact same items
- Trial-level timing and confidence logging
- Post-study workload / confidence / AI helpfulness measures
- MTurk completion code flow
- Optional MTurk auto-submit support if `turkSubmitTo` is present

## Files
- `hw3/app.py`: study server
- `hw3/study_config.py`: app settings
- `hw3/static/`: frontend assets
- `hw3/data/study.db`: SQLite database created at runtime
- `hw3/scripts/export_study_data.py`: exports collected data to CSV
- `hw3/scripts/mturk_link_helper.py`: prints condition-specific MTurk URLs
- `hw3/report/a3_1_deployment_guide.md`: step-by-step setup notes

## Local setup
1. Initialize the database:
   `conda run -n counseling python hw3/app.py --init-db`
2. Run the server:
   `conda run -n counseling python hw3/app.py --host 127.0.0.1 --port 8000`
3. Open one of these test URLs:
   - `http://127.0.0.1:8000/study?condition=baseline&workerId=test_baseline&assignmentId=test_assignment_baseline`
   - `http://127.0.0.1:8000/study?condition=ai&workerId=test_ai&assignmentId=test_assignment_ai`

## Export data
`conda run -n counseling python hw3/scripts/export_study_data.py`

## Suggested study design
- Use two separate MTurk studies: one for `baseline`, one for `ai`.
- Keep this as a between-subjects design.
- Default trial count is 10 in `hw3/study_config.py`, which is intended to stay under 10 minutes.
