"""Export time-series metrics from logs.jsonl for the Layer-2 dashboard."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import httpx

LOG_PATH = Path("data/logs.jsonl")
OUT_PATH = Path("data/dashboard_metrics.json")
METRICS_URL = "http://127.0.0.1:8000/metrics"


def percentile(values: list[int], p: int) -> float:
    if not values:
        return 0.0
    items = sorted(values)
    idx = max(0, min(len(items) - 1, round((p / 100) * len(items) + 0.5) - 1))
    return float(items[idx])


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def bucket_key(ts: datetime) -> str:
    return ts.replace(second=0, microsecond=0).isoformat().replace("+00:00", "Z")


def load_records() -> list[dict]:
    if not LOG_PATH.exists():
        return []
    records: list[dict] = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def build_timeseries(records: list[dict]) -> list[dict]:
    responses = [r for r in records if r.get("service") == "api" and r.get("event") == "response_sent"]
    failures = [r for r in records if r.get("service") == "api" and r.get("event") == "request_failed"]

    buckets: dict[str, dict] = defaultdict(
        lambda: {
            "latencies": [],
            "errors": 0,
            "cost_usd": 0.0,
            "tokens_in": 0,
            "tokens_out": 0,
            "quality_scores": [],
        }
    )

    for rec in responses:
        if "ts" not in rec or "latency_ms" not in rec:
            continue
        key = bucket_key(parse_ts(rec["ts"]))
        bucket = buckets[key]
        bucket["latencies"].append(int(rec["latency_ms"]))
        bucket["cost_usd"] += float(rec.get("cost_usd", 0))
        bucket["tokens_in"] += int(rec.get("tokens_in", 0))
        bucket["tokens_out"] += int(rec.get("tokens_out", 0))
        # Quality proxy: heuristic from response size + latency (lab allows heuristic)
        tokens_out = int(rec.get("tokens_out", 0))
        latency_ms = int(rec["latency_ms"])
        proxy = 0.5
        if tokens_out >= 80:
            proxy += 0.2
        if latency_ms <= 3000:
            proxy += 0.1
        if tokens_out >= 120:
            proxy += 0.1
        bucket["quality_scores"].append(min(1.0, proxy))

    for rec in failures:
        if "ts" not in rec:
            continue
        buckets[bucket_key(parse_ts(rec["ts"]))]["errors"] += 1

    series: list[dict] = []
    for ts in sorted(buckets):
        b = buckets[ts]
        traffic = len(b["latencies"])
        total = traffic + b["errors"]
        series.append(
            {
                "ts": ts,
                "traffic": traffic,
                "qps": round(traffic / 60, 4),
                "latency_p50_ms": percentile(b["latencies"], 50),
                "latency_p95_ms": percentile(b["latencies"], 95),
                "latency_p99_ms": percentile(b["latencies"], 99),
                "error_count": b["errors"],
                "error_rate_pct": round((b["errors"] / total) * 100, 2) if total else 0.0,
                "cost_usd": round(b["cost_usd"], 6),
                "tokens_in": b["tokens_in"],
                "tokens_out": b["tokens_out"],
                "quality_proxy": round(sum(b["quality_scores"]) / len(b["quality_scores"]), 4)
                if b["quality_scores"]
                else 0.0,
            }
        )
    return series


def fetch_live_snapshot() -> dict:
    try:
        response = httpx.get(METRICS_URL, timeout=5.0)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        return {"error": str(exc)}


def load_slos() -> dict:
    return {
        "latency_p95_ms": 3000,
        "error_rate_pct": 2,
        "daily_cost_usd": 2.5,
        "quality_score_avg": 0.75,
    }


def main() -> None:
    records = load_records()
    if not records:
        print(f"Error: no records in {LOG_PATH}. Run the app and send requests first.")
        sys.exit(1)

    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": str(LOG_PATH),
        "slo": load_slos(),
        "live_snapshot": fetch_live_snapshot(),
        "timeseries": build_timeseries(records),
        "error_breakdown": fetch_live_snapshot().get("error_breakdown", {}),
    }
    series = payload["timeseries"]
    live = payload["live_snapshot"]
    if series and not live.get("traffic"):
        payload["live_snapshot"] = {
            **live,
            "traffic": sum(p["traffic"] for p in series),
            "latency_p95": max(p["latency_p95_ms"] for p in series),
            "total_cost_usd": round(sum(p["cost_usd"] for p in series), 4),
            "tokens_in_total": sum(p["tokens_in"] for p in series),
            "tokens_out_total": sum(p["tokens_out"] for p in series),
            "quality_avg": round(
                sum(p["quality_proxy"] for p in series) / len(series), 4
            ),
        }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Exported dashboard metrics to {OUT_PATH}")
    print(f"  Time buckets: {len(payload['timeseries'])}")
    print(f"  Live traffic: {payload['live_snapshot'].get('traffic', 'n/a')}")


if __name__ == "__main__":
    main()
