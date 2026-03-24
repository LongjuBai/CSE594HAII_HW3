#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from hw3.study_config import DB_PATH, EXPORT_DIR


def write_csv(path: Path, rows, fieldnames) -> None:
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def mean(values):
    return round(sum(values) / len(values), 4) if values else None


def main() -> None:
    parser = argparse.ArgumentParser(description='Export HW3 study data from SQLite.')
    parser.add_argument('--db', type=Path, default=DB_PATH)
    parser.add_argument('--out-dir', type=Path, default=EXPORT_DIR)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    participants = [dict(row) for row in conn.execute('SELECT * FROM participants ORDER BY started_at').fetchall()]
    responses = [dict(row) for row in conn.execute('SELECT * FROM responses ORDER BY submitted_at').fetchall()]
    joined = [
        dict(row)
        for row in conn.execute(
            '''
            SELECT
                p.participant_id,
                p.worker_id,
                p.assignment_id,
                p.hit_id,
                p.condition,
                p.started_at,
                p.completed_at,
                p.completion_code,
                p.overall_confidence,
                p.workload,
                p.ai_helpfulness,
                r.order_index,
                r.trial_id,
                r.participant_label,
                r.confidence AS trial_confidence,
                r.time_spent_ms,
                r.ai_requested,
                r.ai_request_elapsed_ms,
                r.is_correct,
                t.topic,
                t.risk_level,
                t.difficulty,
                t.input_client_statement,
                t.input_counselor_response,
                t.ground_truth,
                t.model_output,
                t.model_probability,
                t.ai_assistance
            FROM responses r
            JOIN participants p ON p.participant_id = r.participant_id
            JOIN trials t ON t.trial_id = r.trial_id
            ORDER BY p.started_at, r.order_index
            '''
        ).fetchall()
    ]

    by_condition = {}
    for condition in ['baseline', 'ai']:
        condition_rows = [row for row in joined if row['condition'] == condition]
        by_condition[condition] = {
            'participants': sum(1 for row in participants if row['condition'] == condition),
            'responses': len(condition_rows),
            'accuracy': mean([row['is_correct'] for row in condition_rows]),
            'avg_time_spent_ms': mean([row['time_spent_ms'] for row in condition_rows]),
            'avg_trial_confidence': mean([row['trial_confidence'] for row in condition_rows]),
            'ai_reveal_rate': mean([row['ai_requested'] for row in condition_rows]) if condition == 'ai' else None,
        }

    summary = {
        'participants_total': len(participants),
        'participants_completed': sum(1 for row in participants if row['status'] == 'completed'),
        'responses_total': len(responses),
        'by_condition': by_condition,
    }

    if participants:
        write_csv(args.out_dir / 'participants.csv', participants, participants[0].keys())
    if responses:
        write_csv(args.out_dir / 'responses.csv', responses, responses[0].keys())
    if joined:
        write_csv(args.out_dir / 'joined_trials.csv', joined, joined[0].keys())

    (args.out_dir / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')

    print(f'Exported study data to {args.out_dir}')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
