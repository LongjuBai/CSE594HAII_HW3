#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from hw3.study_config import DB_PATH


def main() -> None:
    parser = argparse.ArgumentParser(description='Clear participant/session data while keeping trial items intact.')
    parser.add_argument('--db', type=Path, default=DB_PATH)
    parser.add_argument('--yes', action='store_true', help='Skip the safety prompt.')
    args = parser.parse_args()

    if not args.yes:
        answer = input('This will delete all participant runs but keep the trial pool. Continue? [y/N] ')
        if answer.strip().lower() != 'y':
            print('Cancelled.')
            return

    conn = sqlite3.connect(args.db)
    conn.execute('DELETE FROM responses')
    conn.execute('DELETE FROM participant_trials')
    conn.execute('DELETE FROM participants')
    conn.commit()
    conn.close()
    print(f'Cleared participant data in {args.db}')


if __name__ == '__main__':
    main()
