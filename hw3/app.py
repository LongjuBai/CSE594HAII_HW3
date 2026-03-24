#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import mimetypes
import os
import random
import secrets
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from study_config import (
    ALLOW_SAME_WORKER_BOTH_CONDITIONS,
    CONDITIONS,
    CONFIDENCE_OPTIONS,
    COURSE_TITLE,
    DB_PATH,
    EXPORT_DIR,
    HW2_DATASET,
    STATIC_DIR,
    STUDY_TITLE,
    TRIALS_PER_PARTICIPANT,
    WORKLOAD_OPTIONS,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS trials (
            trial_id TEXT PRIMARY KEY,
            split TEXT,
            task_name TEXT,
            topic TEXT,
            risk_level TEXT,
            difficulty TEXT,
            response_pattern TEXT,
            input_client_statement TEXT,
            input_counselor_response TEXT,
            input_text TEXT,
            ground_truth TEXT,
            ground_truth_binary INTEGER,
            model_output TEXT,
            model_probability REAL,
            human_rating_of_model_output TEXT,
            dataset_source TEXT,
            ai_assistance TEXT
        );

        CREATE TABLE IF NOT EXISTS participants (
            participant_id TEXT PRIMARY KEY,
            worker_id TEXT,
            assignment_id TEXT,
            hit_id TEXT,
            turk_submit_to TEXT,
            condition TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            completion_code TEXT NOT NULL,
            n_trials INTEGER NOT NULL,
            user_agent TEXT,
            ip_address TEXT,
            overall_confidence INTEGER,
            workload INTEGER,
            ai_helpfulness INTEGER,
            comments TEXT
        );

        CREATE TABLE IF NOT EXISTS participant_trials (
            participant_id TEXT NOT NULL,
            order_index INTEGER NOT NULL,
            trial_id TEXT NOT NULL,
            PRIMARY KEY (participant_id, order_index),
            FOREIGN KEY (participant_id) REFERENCES participants(participant_id),
            FOREIGN KEY (trial_id) REFERENCES trials(trial_id)
        );

        CREATE TABLE IF NOT EXISTS responses (
            participant_id TEXT NOT NULL,
            trial_id TEXT NOT NULL,
            order_index INTEGER NOT NULL,
            participant_label TEXT NOT NULL,
            confidence INTEGER NOT NULL,
            time_spent_ms INTEGER NOT NULL,
            ai_requested INTEGER NOT NULL DEFAULT 0,
            ai_request_elapsed_ms INTEGER,
            is_correct INTEGER NOT NULL,
            submitted_at TEXT NOT NULL,
            PRIMARY KEY (participant_id, trial_id),
            FOREIGN KEY (participant_id) REFERENCES participants(participant_id),
            FOREIGN KEY (trial_id) REFERENCES trials(trial_id)
        );

        CREATE INDEX IF NOT EXISTS idx_participants_worker ON participants(worker_id);
        CREATE INDEX IF NOT EXISTS idx_participants_assignment ON participants(assignment_id);
        CREATE INDEX IF NOT EXISTS idx_participant_trials_trial ON participant_trials(trial_id);
        CREATE INDEX IF NOT EXISTS idx_responses_participant ON responses(participant_id);
        """
    )
    conn.commit()


def seed_trials_if_needed(conn: sqlite3.Connection) -> int:
    trial_count = conn.execute("SELECT COUNT(*) FROM trials").fetchone()[0]
    if trial_count:
        return trial_count

    with HW2_DATASET.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = []
        for row in reader:
            rows.append(
                (
                    row["trial_id"],
                    row["split"],
                    row["task_name"],
                    row["topic"],
                    row["risk_level"],
                    row["difficulty"],
                    row["response_pattern"],
                    row["input_client_statement"],
                    row["input_counselor_response"],
                    row["input_text"],
                    row["ground_truth"],
                    int(row["ground_truth_binary"]),
                    row["model_output"],
                    float(row["model_probability"]),
                    row["human_rating_of_model_output"],
                    row["dataset_source"],
                    row.get("ai_assistance", ""),
                )
            )

    conn.executemany(
        """
        INSERT INTO trials (
            trial_id, split, task_name, topic, risk_level, difficulty, response_pattern,
            input_client_statement, input_counselor_response, input_text, ground_truth,
            ground_truth_binary, model_output, model_probability,
            human_rating_of_model_output, dataset_source, ai_assistance
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def init_database() -> int:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    try:
        ensure_schema(conn)
        return seed_trials_if_needed(conn)
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def find_existing_participant(
    conn: sqlite3.Connection,
    worker_id: str,
    assignment_id: str,
    condition: str,
) -> Optional[sqlite3.Row]:
    if assignment_id and assignment_id != "ASSIGNMENT_ID_NOT_AVAILABLE":
        row = conn.execute(
            """
            SELECT * FROM participants
            WHERE assignment_id = ? AND condition = ?
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (assignment_id, condition),
        ).fetchone()
        if row:
            return row

    if worker_id:
        return conn.execute(
            """
            SELECT * FROM participants
            WHERE worker_id = ? AND condition = ? AND status != 'completed'
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (worker_id, condition),
        ).fetchone()

    return None


def worker_has_other_condition(conn: sqlite3.Connection, worker_id: str, condition: str) -> bool:
    if not worker_id:
        return False
    row = conn.execute(
        """
        SELECT 1
        FROM participants
        WHERE worker_id = ? AND condition != ?
        LIMIT 1
        """,
        (worker_id, condition),
    ).fetchone()
    return row is not None


def select_trials_for_condition(
    conn: sqlite3.Connection,
    condition: str,
    n_trials: int,
) -> List[sqlite3.Row]:
    exposure_rows = conn.execute(
        """
        SELECT pt.trial_id, COUNT(*) AS exposure_count
        FROM participant_trials pt
        JOIN participants p ON p.participant_id = pt.participant_id
        WHERE p.condition = ?
        GROUP BY pt.trial_id
        """,
        (condition,),
    ).fetchall()
    exposure = {row["trial_id"]: row["exposure_count"] for row in exposure_rows}

    trials = conn.execute("SELECT * FROM trials").fetchall()
    rng = random.SystemRandom()
    rng.shuffle(trials)
    ordered_trials = sorted(trials, key=lambda row: exposure.get(row["trial_id"], 0))
    return ordered_trials[:n_trials]


def create_participant(
    conn: sqlite3.Connection,
    condition: str,
    worker_id: str,
    assignment_id: str,
    hit_id: str,
    turk_submit_to: str,
    user_agent: str,
    ip_address: str,
) -> sqlite3.Row:
    participant_id = secrets.token_hex(12)
    completion_code = f"COUN-{secrets.token_hex(4).upper()}"
    started_at = utc_now_iso()
    selected_trials = select_trials_for_condition(conn, condition, TRIALS_PER_PARTICIPANT)

    conn.execute(
        """
        INSERT INTO participants (
            participant_id, worker_id, assignment_id, hit_id, turk_submit_to,
            condition, status, started_at, completion_code, n_trials, user_agent, ip_address
        ) VALUES (?, ?, ?, ?, ?, ?, 'started', ?, ?, ?, ?, ?)
        """,
        (
            participant_id,
            worker_id,
            assignment_id,
            hit_id,
            turk_submit_to,
            condition,
            started_at,
            completion_code,
            len(selected_trials),
            user_agent,
            ip_address,
        ),
    )

    conn.executemany(
        """
        INSERT INTO participant_trials (participant_id, order_index, trial_id)
        VALUES (?, ?, ?)
        """,
        [
            (participant_id, index, row["trial_id"])
            for index, row in enumerate(selected_trials)
        ],
    )
    conn.commit()

    return conn.execute(
        "SELECT * FROM participants WHERE participant_id = ?",
        (participant_id,),
    ).fetchone()


def serialize_trial_for_participant(row: sqlite3.Row, condition: str) -> Dict[str, Any]:
    payload = {
        "order_index": row["order_index"],
        "trial_id": row["trial_id"],
        "input_client_statement": row["input_client_statement"],
        "input_counselor_response": row["input_counselor_response"],
    }
    if condition == "ai":
        payload.update(
            {
                "model_output": row["model_output"],
                "model_probability": row["model_probability"],
                "ai_assistance": row["ai_assistance"],
            }
        )
    return payload


def get_participant_payload(conn: sqlite3.Connection, participant_id: str) -> Dict[str, Any]:
    participant = conn.execute(
        "SELECT * FROM participants WHERE participant_id = ?",
        (participant_id,),
    ).fetchone()
    if not participant:
        raise ValueError("Participant not found.")

    trial_rows = conn.execute(
        """
        SELECT pt.order_index, t.*
        FROM participant_trials pt
        JOIN trials t ON t.trial_id = pt.trial_id
        WHERE pt.participant_id = ?
        ORDER BY pt.order_index ASC
        """,
        (participant_id,),
    ).fetchall()

    response_rows = conn.execute(
        """
        SELECT *
        FROM responses
        WHERE participant_id = ?
        ORDER BY order_index ASC
        """,
        (participant_id,),
    ).fetchall()

    return {
        "participant": row_to_dict(participant),
        "trials": [serialize_trial_for_participant(row, participant["condition"]) for row in trial_rows],
        "responses": [row_to_dict(row) for row in response_rows],
        "condition_meta": CONDITIONS[participant["condition"]],
    }


def save_trial_response(conn: sqlite3.Connection, payload: Dict[str, Any]) -> Dict[str, Any]:
    participant_id = str(payload["participant_id"])
    trial_id = str(payload["trial_id"])
    participant_label = str(payload["participant_label"]).strip().lower()
    confidence = int(payload["confidence"])
    order_index = int(payload["order_index"])
    time_spent_ms = int(payload["time_spent_ms"])
    ai_requested = 1 if payload.get("ai_requested") else 0
    ai_request_elapsed_ms = payload.get("ai_request_elapsed_ms")
    ai_request_elapsed_ms = (
        int(ai_request_elapsed_ms) if ai_request_elapsed_ms is not None else None
    )

    if participant_label not in {"appropriate", "problematic"}:
        raise ValueError("Invalid participant label.")
    if confidence not in CONFIDENCE_OPTIONS:
        raise ValueError("Invalid confidence rating.")

    trial = conn.execute(
        """
        SELECT t.ground_truth
        FROM participant_trials pt
        JOIN trials t ON t.trial_id = pt.trial_id
        WHERE pt.participant_id = ? AND pt.order_index = ? AND pt.trial_id = ?
        """,
        (participant_id, order_index, trial_id),
    ).fetchone()
    if not trial:
        raise ValueError("Trial assignment not found.")

    is_correct = 1 if participant_label == trial["ground_truth"] else 0
    conn.execute(
        """
        INSERT OR REPLACE INTO responses (
            participant_id, trial_id, order_index, participant_label, confidence,
            time_spent_ms, ai_requested, ai_request_elapsed_ms, is_correct, submitted_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            participant_id,
            trial_id,
            order_index,
            participant_label,
            confidence,
            time_spent_ms,
            ai_requested,
            ai_request_elapsed_ms,
            is_correct,
            utc_now_iso(),
        ),
    )
    conn.commit()
    return {"ok": True, "is_correct": bool(is_correct)}


def complete_study(conn: sqlite3.Connection, payload: Dict[str, Any]) -> Dict[str, Any]:
    participant_id = str(payload["participant_id"])
    participant = conn.execute(
        "SELECT * FROM participants WHERE participant_id = ?",
        (participant_id,),
    ).fetchone()
    if not participant:
        raise ValueError("Participant not found.")

    response_count = conn.execute(
        "SELECT COUNT(*) FROM responses WHERE participant_id = ?",
        (participant_id,),
    ).fetchone()[0]
    if response_count < participant["n_trials"]:
        raise ValueError("Not all trials are completed yet.")

    overall_confidence = int(payload["overall_confidence"])
    workload = int(payload["workload"])
    ai_helpfulness = payload.get("ai_helpfulness")
    ai_helpfulness = int(ai_helpfulness) if ai_helpfulness not in (None, "") else None
    comments = str(payload.get("comments", "")).strip()

    if overall_confidence not in CONFIDENCE_OPTIONS:
        raise ValueError("Invalid overall confidence.")
    if workload not in WORKLOAD_OPTIONS:
        raise ValueError("Invalid workload.")

    conn.execute(
        """
        UPDATE participants
        SET status = 'completed',
            completed_at = ?,
            overall_confidence = ?,
            workload = ?,
            ai_helpfulness = ?,
            comments = ?
        WHERE participant_id = ?
        """,
        (
            utc_now_iso(),
            overall_confidence,
            workload,
            ai_helpfulness,
            comments,
            participant_id,
        ),
    )
    conn.commit()

    submit_url = None
    if participant["turk_submit_to"] and participant["assignment_id"]:
        if participant["assignment_id"] != "ASSIGNMENT_ID_NOT_AVAILABLE":
            submit_url = participant["turk_submit_to"].rstrip("/") + "/mturk/externalSubmit"

    return {
        "ok": True,
        "completion_code": participant["completion_code"],
        "assignment_id": participant["assignment_id"],
        "submit_url": submit_url,
    }


def parse_json_body(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    content_length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(content_length).decode("utf-8")
    return json.loads(raw) if raw else {}


def send_json(handler: BaseHTTPRequestHandler, payload: Dict[str, Any], status: int = 200) -> None:
    raw = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def send_text(handler: BaseHTTPRequestHandler, content: str, status: int = 200) -> None:
    raw = content.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def serve_static(handler: BaseHTTPRequestHandler, requested_path: str) -> None:
    static_path = (STATIC_DIR / requested_path.replace("/static/", "", 1)).resolve()
    if not str(static_path).startswith(str(STATIC_DIR.resolve())) or not static_path.exists():
        handler.send_error(404, "File not found.")
        return

    mime_type, _ = mimetypes.guess_type(str(static_path))
    content = static_path.read_bytes()
    handler.send_response(200)
    handler.send_header("Content-Type", mime_type or "application/octet-stream")
    handler.send_header("Content-Length", str(len(content)))
    handler.end_headers()
    handler.wfile.write(content)


def render_home_page() -> str:
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{STUDY_TITLE}</title>
  <link rel=\"stylesheet\" href=\"/static/style.css\">
</head>
<body class=\"home-page\">
  <main class=\"home-shell\">
    <section class=\"hero-card\">
      <p class=\"eyebrow\">{COURSE_TITLE}</p>
      <h1>{STUDY_TITLE}</h1>
      <p class=\"lead\">Custom MTurk-ready study app for baseline and AI-assisted counselor-training judgments.</p>
      <div class=\"button-row\">
        <a class=\"primary-button\" href=\"/study?condition=baseline&workerId=test_baseline&assignmentId=test_assignment_baseline\">Open baseline test</a>
        <a class=\"secondary-button\" href=\"/study?condition=ai&workerId=test_ai&assignmentId=test_assignment_ai\">Open AI-assisted test</a>
      </div>
      <div class=\"mini-note\">
        <p>Trials per participant: {TRIALS_PER_PARTICIPANT}</p>
        <p>Database: {DB_PATH.name}</p>
      </div>
    </section>
  </main>
</body>
</html>
"""


def render_study_page(query: Dict[str, List[str]]) -> str:
    boot = {
        "title": STUDY_TITLE,
        "conditions": CONDITIONS,
        "query": {
            "condition": query.get("condition", ["baseline"])[0],
            "workerId": query.get("workerId", [""])[0],
            "assignmentId": query.get("assignmentId", [""])[0],
            "hitId": query.get("hitId", [""])[0],
            "turkSubmitTo": query.get("turkSubmitTo", [""])[0],
        },
        "config": {
            "trialsPerParticipant": TRIALS_PER_PARTICIPANT,
            "confidenceOptions": CONFIDENCE_OPTIONS,
            "workloadOptions": WORKLOAD_OPTIONS,
            "allowSameWorkerBothConditions": ALLOW_SAME_WORKER_BOTH_CONDITIONS,
        },
    }
    boot_json = json.dumps(boot)
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{STUDY_TITLE}</title>
  <link rel=\"stylesheet\" href=\"/static/style.css\">
</head>
<body>
  <div id=\"app\"></div>
  <script>window.__STUDY_BOOTSTRAP__ = {boot_json};</script>
  <script src=\"/static/app.js\"></script>
</body>
</html>
"""


class StudyRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            send_text(self, render_home_page())
            return
        if parsed.path == "/study":
            send_text(self, render_study_page(parse_qs(parsed.query)))
            return
        if parsed.path == "/health":
            send_json(self, {"ok": True, "time": utc_now_iso()})
            return
        if parsed.path.startswith("/static/"):
            serve_static(self, parsed.path)
            return
        self.send_error(404, "Not found.")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/start":
                self.handle_start()
                return
            if parsed.path == "/api/submit-trial":
                self.handle_submit_trial()
                return
            if parsed.path == "/api/complete":
                self.handle_complete()
                return
            self.send_error(404, "Not found.")
        except ValueError as exc:
            send_json(self, {"ok": False, "error": str(exc)}, status=400)
        except Exception as exc:
            send_json(self, {"ok": False, "error": f"Unexpected server error: {exc}"}, status=500)

    def handle_start(self) -> None:
        payload = parse_json_body(self)
        condition = str(payload.get("condition", "baseline")).strip().lower()
        worker_id = str(payload.get("worker_id", "")).strip()
        assignment_id = str(payload.get("assignment_id", "")).strip()
        hit_id = str(payload.get("hit_id", "")).strip()
        turk_submit_to = str(payload.get("turk_submit_to", "")).strip()
        user_agent = str(payload.get("user_agent", self.headers.get("User-Agent", "")))
        ip_address = str(self.client_address[0]) if self.client_address else ""

        if condition not in CONDITIONS:
            raise ValueError("Unknown condition.")
        if assignment_id == "ASSIGNMENT_ID_NOT_AVAILABLE":
            raise ValueError("This HIT is in preview mode. Accept the HIT before starting.")

        conn = get_db()
        try:
            if not ALLOW_SAME_WORKER_BOTH_CONDITIONS and worker_has_other_condition(conn, worker_id, condition):
                raise ValueError("This worker has already participated in the other condition.")

            participant = find_existing_participant(conn, worker_id, assignment_id, condition)
            if not participant:
                participant = create_participant(
                    conn=conn,
                    condition=condition,
                    worker_id=worker_id,
                    assignment_id=assignment_id,
                    hit_id=hit_id,
                    turk_submit_to=turk_submit_to,
                    user_agent=user_agent,
                    ip_address=ip_address,
                )

            payload = get_participant_payload(conn, participant["participant_id"])
            send_json(self, {"ok": True, **payload})
        finally:
            conn.close()

    def handle_submit_trial(self) -> None:
        payload = parse_json_body(self)
        conn = get_db()
        try:
            result = save_trial_response(conn, payload)
            send_json(self, result)
        finally:
            conn.close()

    def handle_complete(self) -> None:
        payload = parse_json_body(self)
        conn = get_db()
        try:
            result = complete_study(conn, payload)
            send_json(self, result)
        finally:
            conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the HW3 MTurk study app.")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Create the SQLite database and load the HW2 study dataset.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    trial_count = init_database()
    if args.init_db:
        print(f"Initialized database at {DB_PATH} with {trial_count} trials.")
        return

    server = ThreadingHTTPServer((args.host, args.port), StudyRequestHandler)
    print(f"Study app running on http://{args.host}:{args.port}")
    print(f"Loaded {trial_count} trials from {HW2_DATASET}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
