# Screenshot Evidence — Day 13 Lab

Đặt tên file theo convention dưới đây, rồi điền path vào `docs/blueprint-template.md`.

| File | Nội dung cần chụp | Blueprint tag |
|------|-------------------|-----------------|
| `sc-langfuse-traces.png` | Langfuse → Traces, ≥ 10 traces, filter tag `lab` | `[EVIDENCE_TRACE_WATERFALL_SCREENSHOT]` (list) |
| `sc-langfuse-waterfall.png` | Mở 1 trace → span `run` + metadata/tags | `[EVIDENCE_TRACE_WATERFALL_SCREENSHOT]` |
| `sc-logs-correlation-id.png` | `data/logs.jsonl` hoặc terminal — thấy `correlation_id`, enrichment | `[EVIDENCE_CORRELATION_ID_SCREENSHOT]` |
| `sc-logs-pii-redaction.png` | Dòng log có `[REDACTED_EMAIL]` / `[REDACTED_PHONE_VN]` | `[EVIDENCE_PII_REDACTION_SCREENSHOT]` |
| `sc-dashboard-6-panels.png` | `http://127.0.0.1:8000/dashboard/` — đủ 6 chart + stats | `[DASHBOARD_6_PANELS_SCREENSHOT]` |
| `sc-alerts.png` | Output `python scripts/evaluate_alerts.py --verbose` | `[ALERT_RULES_SCREENSHOT]` |

`sc1.png` = alerts (đã có) → có thể đổi tên thành `sc-alerts.png`.

---

## 1. Langfuse

1. Mở https://us.cloud.langfuse.com
2. Project của bạn → **Tracing** → **Traces**
3. **Screenshot list:** chọn time range **Last 1 hour**, thấy ≥ 10 rows
4. Click 1 trace (name `run`) → **Screenshot waterfall:** userId hash, sessionId, tags `lab`, `qa`/`summary`

**Gợi ý giải thích waterfall (`TRACE_WATERFALL_EXPLANATION`):**
> Span `run` bọc toàn bộ agent pipeline. Khi bật `rag_slow`, latency tăng ~2.5s do RAG sleep — có thể đối chiếu với log `latency_ms` và alert `high_latency_p95`.

---

## 2. Logs

**Cách A — VS Code:** mở `data/logs.jsonl`, tìm dòng có:
- `correlation_id`: `req-...`
- `user_id_hash`, `session_id`, `feature`, `model`
- `message_preview` với `[REDACTED_EMAIL]` hoặc `[REDACTED_PHONE_VN]`

**Cách B — terminal (dễ chụp):**

```powershell
python scripts/print_log_evidence.py
```

---

## 3. Dashboard

```powershell
uvicorn app.main:app --reload
python scripts/load_test.py --concurrency 5
python scripts/export_dashboard_metrics.py
start http://127.0.0.1:8000/dashboard/
```

Chụp full màn hình: 6 panel + hàng stats trên (Traffic, P95, Cost…).

---

## 4. Alerts

```powershell
python scripts/evaluate_alerts.py --verbose
```

Đã có: `screenshot/sc1.png`
