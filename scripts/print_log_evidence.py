"""Print curated log lines for screenshot evidence (correlation ID + PII redaction)."""

from __future__ import annotations

import json
from pathlib import Path

LOG_PATH = Path("data/logs.jsonl")


def main() -> None:
    if not LOG_PATH.exists():
        print(f"Missing {LOG_PATH}. Run load_test first.")
        return

    records = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    correlation_sample = next(
        (
            r
            for r in records
            if r.get("event") == "request_received"
            and r.get("correlation_id")
            and r.get("correlation_id") != "MISSING"
            and r.get("user_id_hash")
        ),
        None,
    )
    pii_sample = next(
        (
            r
            for r in records
            if r.get("event") == "request_received"
            and "REDACTED" in json.dumps(r)
        ),
        None,
    )

    print("=" * 60)
    print("EVIDENCE 1 — Correlation ID + log enrichment")
    print("=" * 60)
    if correlation_sample:
        print(json.dumps(correlation_sample, indent=2, ensure_ascii=False))
    else:
        print("No suitable log found. Send /chat requests first.")

    print()
    print("=" * 60)
    print("EVIDENCE 2 — PII redaction in message_preview")
    print("=" * 60)
    if pii_sample:
        print(json.dumps(pii_sample, indent=2, ensure_ascii=False))
    else:
        print("No REDACTED_* log found. Use sample_queries with email/phone.")


if __name__ == "__main__":
    main()
