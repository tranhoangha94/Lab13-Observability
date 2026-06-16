# Alert Rules and Runbooks

## 1. High latency P95
- Severity: P2
- Trigger: `latency_p95_ms > 5000 for 30m`
- Impact: tail latency breaches SLO
- First checks:
  1. Open top slow traces in the last 1h
  2. Compare RAG span vs LLM span
  3. Check if incident toggle `rag_slow` is enabled
- Mitigation:
  - truncate long queries
  - fallback retrieval source
  - lower prompt size

## 2. High error rate
- Severity: P1
- Trigger: `error_rate_pct > 5 for 5m`
- Impact: users receive failed responses
- First checks:
  1. Group logs by `error_type`
  2. Inspect failed traces
  3. Determine whether failures are LLM, tool, or schema related
- Mitigation:
  - rollback latest change
  - disable failing tool
  - retry with fallback model

## 3. Cost budget spike
- Severity: P2
- Trigger: `hourly_cost_usd > 2x_baseline for 15m`
- Impact: burn rate exceeds budget
- First checks:
  1. Split traces by feature and model
  2. Compare tokens_in/tokens_out
  3. Check if `cost_spike` incident was enabled
- Mitigation:
  - shorten prompts
  - route easy requests to cheaper model
  - apply prompt cache

---

## Lab verification (Part 8)

Use these commands to configure, inject, and test alerts:

```powershell
# Baseline — expect all OK
python scripts/evaluate_alerts.py

# Test 1: latency alert (rag_slow adds ~2.5s RAG delay → P95 ~2650ms)
python scripts/inject_incident.py --scenario rag_slow
python scripts/load_test.py --concurrency 5
python scripts/evaluate_alerts.py --verbose

# Test 2: error rate alert (tool_fail breaks retrieval)
python scripts/inject_incident.py --scenario rag_slow --disable
python scripts/inject_incident.py --scenario tool_fail
python scripts/load_test.py
python scripts/evaluate_alerts.py --verbose

# Test 3: cost spike (4x output tokens)
python scripts/inject_incident.py --scenario tool_fail --disable
python scripts/inject_incident.py --scenario cost_spike
python scripts/load_test.py --concurrency 5
python scripts/evaluate_alerts.py --verbose

# Cleanup
python scripts/inject_incident.py --scenario cost_spike --disable
```

| Alert | Lab scenario | Expected signal |
|-------|--------------|-----------------|
| `high_latency_p95` | `rag_slow` | `latency_p95_ms` > 2000 |
| `high_error_rate` | `tool_fail` | `error_rate_pct` > 5% |
| `cost_budget_spike` | `cost_spike` | `session_cost_usd` > $0.04 |
