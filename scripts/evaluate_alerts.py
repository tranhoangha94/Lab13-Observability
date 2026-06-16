"""Evaluate alert rules against live /metrics and optional dashboard export."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import httpx
import yaml

RULES_PATH = Path("config/alert_rules.yaml")
METRICS_URL = "http://127.0.0.1:8000/metrics"
HEALTH_URL = "http://127.0.0.1:8000/health"


def load_rules() -> list[dict[str, Any]]:
    if not RULES_PATH.exists():
        print(f"Error: {RULES_PATH} not found")
        sys.exit(1)
    data = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))
    return data.get("alerts", [])


def fetch_metrics() -> dict[str, Any]:
    response = httpx.get(METRICS_URL, timeout=5.0)
    response.raise_for_status()
    return response.json()


def fetch_incidents() -> dict[str, bool]:
    response = httpx.get(HEALTH_URL, timeout=5.0)
    response.raise_for_status()
    return response.json().get("incidents", {})


def compute_signals(metrics: dict[str, Any]) -> dict[str, float]:
    traffic = int(metrics.get("traffic", 0))
    errors = sum(metrics.get("error_breakdown", {}).values())
    error_rate = (errors / traffic * 100.0) if traffic else 0.0
    return {
        "latency_p95_ms": float(metrics.get("latency_p95", 0)),
        "error_rate_pct": round(error_rate, 2),
        "session_cost_usd": float(metrics.get("total_cost_usd", 0)),
    }


def evaluate_rule(rule: dict[str, Any], signals: dict[str, float]) -> tuple[bool, str]:
    metric = rule["metric"]
    threshold = float(rule["threshold"])
    value = signals.get(metric, 0.0)
    compare = rule.get("compare", "gt")

    if compare == "gt":
        firing = value > threshold
    elif compare == "gte":
        firing = value >= threshold
    elif compare == "lt":
        firing = value < threshold
    else:
        firing = False

    detail = f"{metric}={value} (threshold {compare} {threshold})"
    return firing, detail


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate configured alert rules")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    try:
        metrics = fetch_metrics()
        incidents = fetch_incidents()
    except Exception as exc:
        print(f"Error: cannot reach API at {METRICS_URL} — start uvicorn first. ({exc})")
        sys.exit(1)

    signals = compute_signals(metrics)
    rules = load_rules()

    print("--- Alert Evaluation ---")
    print(f"Traffic: {metrics.get('traffic', 0)} | Incidents: {incidents}")
    if args.verbose:
        print(f"Signals: {json.dumps(signals, indent=2)}")

    firing_count = 0
    for rule in rules:
        firing, detail = evaluate_rule(rule, signals)
        status = "FIRING" if firing else "OK"
        if firing:
            firing_count += 1
        print(f"[{status}] {rule['name']} ({rule['severity']}) — {detail}")
        print(f"         condition: {rule['condition']}")
        print(f"         runbook: {rule['runbook']}")
        if rule.get("lab_scenario"):
            enabled = incidents.get(rule["lab_scenario"], False)
            print(f"         lab_scenario: {rule['lab_scenario']} ({'enabled' if enabled else 'disabled'})")

    print(f"\nSummary: {firing_count}/{len(rules)} alert(s) firing")
    if firing_count:
        print("Action: follow runbook links in docs/alerts.md")
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
