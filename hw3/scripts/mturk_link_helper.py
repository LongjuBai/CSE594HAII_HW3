#!/usr/bin/env python3
from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description='Print MTurk survey links for HW3.')
    parser.add_argument('--base-url', required=True, help='Public base URL, e.g. https://your-app.example.com')
    args = parser.parse_args()

    base = args.base_url.rstrip('/')
    baseline = (
        f"{base}/study?condition=baseline&workerId=${{workerId}}&assignmentId=${{assignmentId}}"
        f"&hitId=${{hitId}}&turkSubmitTo=${{turkSubmitTo}}"
    )
    ai = (
        f"{base}/study?condition=ai&workerId=${{workerId}}&assignmentId=${{assignmentId}}"
        f"&hitId=${{hitId}}&turkSubmitTo=${{turkSubmitTo}}"
    )

    print('Baseline condition URL:')
    print(baseline)
    print()
    print('AI-assisted condition URL:')
    print(ai)


if __name__ == '__main__':
    main()
