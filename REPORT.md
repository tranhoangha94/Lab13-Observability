# Day 13 Observability Lab — REPORT

> Ghi chép tiến độ lab. Phần 1: chạy starter app và quan sát log ban đầu.

---

## Phần 1 — Run the Starter App

**Mục tiêu:** Khởi động FastAPI agent, gửi request, quan sát log hiện tại — ghi nhận log còn cơ bản và **thiếu correlation ID**.

**Ngày thực hiện:** 2026-06-15  
**Môi trường:** Windows, Python 3.12, `uvicorn app.main:app --reload`  
**Traffic:** `python scripts/load_test.py --concurrency 5` (10 request `/chat`)

---

### 1.1 Các bước đã thực hiện

```powershell
cd d:\AI\Day13\Lab13-Observability
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
# Terminal khác:
python scripts/load_test.py --concurrency 5
```

---

### 1.2 Log trên console (Uvicorn + structlog)

Mỗi request tạo **2 dòng JSON** (`request_received` → `response_sent`), xen kẽ với access log của Uvicorn:

```text
INFO:     127.0.0.1:57591 - "POST /chat HTTP/1.1" 200 OK
{"service": "api", "payload": {"message_preview": "How should alerts be designed?"}, "event": "request_received", "level": "info", "ts": "2026-06-15T07:24:12.612874Z"}
{"service": "api", "latency_ms": 150, "tokens_in": 29, "tokens_out": 172, "cost_usd": 0.002667, "payload": {"answer_preview": "Starter answer. Teams should improve this output logic and add better quality ch..."}, "event": "response_sent", "level": "info", "ts": "2026-06-15T07:24:12.765058Z"}
```

**Log khởi động app:**

```json
{
  "service": "day13-observability-lab",
  "env": "dev",
  "payload": {"tracing_enabled": false},
  "event": "app_started",
  "level": "info",
  "ts": "2026-06-15T07:23:41.179112Z"
}
```

**Ví dụ request có PII (đã redact ở `message_preview`):**

```json
{
  "service": "api",
  "payload": {
    "message_preview": "Here is my phone [REDACTED_PHONE_VN], what should be logged?"
  },
  "event": "request_received",
  "level": "info",
  "ts": "2026-06-15T07:24:11.822311Z"
}
```

```json
{
  "service": "api",
  "payload": {
    "message_preview": "What is your refund policy? My email is [REDACTED_EMAIL]"
  },
  "event": "request_received",
  "level": "info",
  "ts": "2026-06-15T07:24:11.666126Z"
}
```

**Screenshot:** `assets/c__Users_ADMIN_AppData_Roaming_Cursor_User_workspaceStorage_9a5048cf74797bdaab2942fcdc4a5201_images_image-40eb858e-cf02-4a6d-ab39-61a9f2f0507c.png`

---

### 1.3 Log ghi ra file `data/logs.jsonl`

- Tổng số bản ghi sau load test: **43** (1 `app_started` + 40 cặp request/response + 2 `incident_enabled`)
- Định dạng: **JSON lines** (mỗi dòng 1 object)
- File log được append bởi `JsonlFileProcessor` trong `app/logging_config.py`

---

### 1.4 Phân tích — Những gì log **đã có**

| Field / Hành vi | Trạng thái | Ghi chú |
|-----------------|------------|---------|
| `ts` | Có | ISO 8601 UTC (`TimeStamper`) |
| `level` | Có | `info`, `warning` |
| `service` | Có | `api`, `control`, `day13-observability-lab` |
| `event` | Có | `app_started`, `request_received`, `response_sent`, `incident_enabled` |
| `payload` | Có | `message_preview`, `answer_preview`, metrics |
| `latency_ms`, `tokens_in/out`, `cost_usd` | Có | Chỉ ở `response_sent` |
| PII trong preview | Một phần | `summarize_text()` gọi `scrub_text()` trước khi log — email/phone/CC bị `[REDACTED_*]` |
| Uvicorn access log | Có | Dòng `INFO: 127.0.0.1:... "POST /chat" 200 OK` — **không** có correlation ID |

---

### 1.5 Phân tích — Những gì log **chưa có** (gap của starter)

| Field / Hành vi | Trạng thái | Nguyên nhân (code) |
|-----------------|------------|---------------------|
| `correlation_id` | **Thiếu** | `middleware.py`: `correlation_id = "MISSING"`, chưa bind contextvars |
| `x-request-id` header (response) | **Thiếu** | TODO trong `CorrelationIdMiddleware` chưa implement |
| `x-response-time-ms` header | **Thiếu** | TODO trong middleware |
| `user_id_hash` | **Thiếu** | TODO trong `main.py` — chưa `bind_contextvars(...)` |
| `session_id` | **Thiếu** | Cùng TODO `main.py` |
| `feature` | **Thiếu** | Cùng TODO `main.py` |
| `model` | **Thiếu** | Cùng TODO `main.py` |
| `env` trên mọi log API | **Thiếu** | Chỉ có ở `app_started` |
| PII processor toàn cục | **Chưa bật** | `scrub_event` trong `logging_config.py` vẫn comment — PII chỉ được scrub ở preview, không phải mọi field |
| Langfuse tracing | **Tắt** | `tracing_enabled: false` — chưa cấu hình key hoặc chưa gửi trace |

**Hệ quả:** Không thể nối `request_received` ↔ `response_sent` của cùng một request khi có nhiều request song song (`concurrency 5`). Không truy vết được theo user/session.

---

### 1.6 Kết quả `validate_logs.py` (baseline Phần 1)

```text
--- Lab Verification Results ---
Total log records analyzed: 43
Records with missing required fields: 40
Records with missing enrichment (context): 40
Unique correlation IDs found: 0
Potential PII leaks detected: 0

--- Grading Scorecard (Estimates) ---
- [FAILED] Missing required fields (ts, level, etc.)
- [FAILED] Correlation ID propagation (less than 2 unique IDs)
- [FAILED] Log enrichment (missing user_id_hash, etc.)
+ [PASSED] PII scrubbing

Estimated Score: 30/100
```

> **Lưu ý:** PII pass vì `summarize_text()` đã redact trước khi ghi log. Điểm enrichment và correlation ID fail đúng như thiết kế template — đây là việc cần làm ở Phần 2–4.

---

### 1.7 So sánh với schema mong đợi (`config/logging_schema.json`)

**Required:** `ts`, `level`, `service`, `event`, `correlation_id`  
**Enrichment (lab):** `user_id_hash`, `session_id`, `feature`, `model`

Log API hiện tại chỉ đáp ứng 4/5 required field; enrichment 0/4.

---

### 1.8 Kết luận Phần 1

1. App chạy ổn định; endpoint `/chat` trả `200 OK`, latency ~150ms (không incident).
2. Log đã là **structured JSON** nhưng còn **thiếu observability cốt lõi**: correlation ID, context enrichment, response headers.
3. `answer_preview` là placeholder: *"Starter answer. Teams should improve..."* — logic agent chưa phải trọng tâm lab này.
4. Điểm ước tính **30/100** — baseline trước khi implement TODO.

---

### 1.9 Việc tiếp theo (Phần 2+)

| Phần | File | Nội dung |
|------|------|----------|
| 2 | `app/middleware.py` | Correlation ID, clear/bind contextvars, response headers |
| 3 | `app/main.py` | Enrich log: `user_id_hash`, `session_id`, `feature`, `model`, `env` |
| 4 | `app/logging_config.py`, `app/pii.py` | Bật `scrub_event`, thêm pattern PII |
| 5 | — | Chạy lại `validate_logs.py`, mục tiêu pass toàn bộ |
| 6 | Langfuse | Gửi 10–20 request, xác nhận ≥ 10 traces |

---

## Phần 7 — Dashboard (6 panels)

**Mục tiêu:** Xây Layer-2 dashboard từ metrics đã export, đủ 6 panel theo `docs/dashboard-spec.md`.

**Ngày thực hiện:** 2026-06-15  
**Nguồn dữ liệu:** `data/logs.jsonl` + endpoint live `GET /metrics`

---

### 7.1 Các bước thực hiện

```powershell
# 1. Tạo traffic (nếu chưa có log mới)
python scripts/load_test.py --concurrency 5

# 2. Export metrics từ logs → JSON cho dashboard
python scripts/export_dashboard_metrics.py

# 3. Mở dashboard qua uvicorn (KHÔNG mở file HTML trực tiếp — browser chặn fetch)
start http://127.0.0.1:8000/dashboard/
```

Script export đọc `response_sent` / `request_failed` trong `data/logs.jsonl`, gom theo **phút**, đồng thời gọi `http://127.0.0.1:8000/metrics` để lấy snapshot live.

---

### 7.2 Sáu panel bắt buộc

| # | Panel | Metric | Nguồn | Đơn vị |
|---|-------|--------|-------|--------|
| 1 | Latency | P50 / P95 / P99 | `latency_*_ms` per bucket | ms |
| 2 | Traffic | Request count | `traffic` per minute | req/min |
| 3 | Error rate | % + breakdown | `error_rate_pct`, `error_breakdown` | % |
| 4 | Cost | Chi phí theo thời gian | `cost_usd` per bucket | USD |
| 5 | Tokens | Input / output | `tokens_in`, `tokens_out` | tokens |
| 6 | Quality proxy | Heuristic score | `quality_proxy` (log) + `quality_avg` (live) | 0–1 |

**Quality bar (spec):**
- Time range mặc định: **1 giờ** (buckets trong `timeseries`)
- Auto-refresh: **30 giây** (`dashboard/index.html`)
- Đường SLO: latency P95 ≤ **3000 ms**, error ≤ **2%**, quality ≥ **0.75** (từ `config/slo.yaml`)
- Tối đa **6 panel** trên layer chính

---

### 7.3 Snapshot metrics (sau export)

**Live `/metrics` (in-memory):**

```json
{
  "traffic": 10,
  "latency_p50": 150.0,
  "latency_p95": 152.0,
  "latency_p99": 152.0,
  "total_cost_usd": 0.0221,
  "tokens_in_total": 340,
  "tokens_out_total": 1404,
  "error_breakdown": {},
  "quality_avg": 0.88
}
```

**Time-series từ logs (`data/dashboard_metrics.json`):**
- 3 time buckets (theo phút UTC)
- P95 latency ~150 ms — **dưới SLO 3000 ms**
- Error rate 0% — **dưới SLO 2%**
- Quality proxy ~0.8–0.9 — **trên SLO 0.75**

---

### 7.4 File deliverable

| File | Mô tả |
|------|--------|
| `scripts/export_dashboard_metrics.py` | Export logs → `data/dashboard_metrics.json` |
| `dashboard/index.html` | Dashboard 6 panel (Chart.js) |
| `data/dashboard_metrics.json` | Dữ liệu đã export |
| `config/slo.yaml` | Ngưỡng SLO tham chiếu |

---

### 7.5 Mapping panel → chart

```text
dashboard/index.html
├── Panel 1: latencyChart     → P50, P95, P99 + SLO line
├── Panel 2: trafficChart     → bar requests/min
├── Panel 3: errorChart       → error % + SLO 2%
├── Panel 4: costChart        → USD/min
├── Panel 5: tokensChart      → tokens in vs out
└── Panel 6: qualityChart     → heuristic proxy + SLO 0.75
```

Header stats bar: traffic, P95, total cost, tokens, quality avg, error count (từ live snapshot).

---

### 7.6 Kết luận Phần 7

1. Dashboard đủ **6 panel** theo spec, có đường SLO và đơn vị rõ ràng.
2. Dữ liệu lấy từ **log đã instrument** (Phần 2–4) + **metrics in-memory** (`app/metrics.py`).
3. Có thể dùng screenshot `dashboard/index.html` làm evidence `[DASHBOARD_6_PANELS_SCREENSHOT]` trong blueprint.
4. Để dashboard luôn mới: chạy load test → `export_dashboard_metrics.py` → refresh trang (hoặc đợi 30s).

---

## Phần 8 — Alerting

**Mục tiêu:** Cấu hình alert rules, viết runbook, inject incident và xác nhận alert **FIRING**.

**Ngày thực hiện:** 2026-06-15

---

### 8.1 Alert rules (`config/alert_rules.yaml`)

| Alert | Severity | Điều kiện | Scenario test |
|-------|----------|-----------|---------------|
| `high_latency_p95` | P2 | `latency_p95_ms > 2000` (5m) | `rag_slow` |
| `high_error_rate` | P1 | `error_rate_pct > 5` (5m) | `tool_fail` |
| `cost_budget_spike` | P2 | `session_cost_usd > $0.04` (2× baseline $0.02) | `cost_spike` |

Mỗi rule có `metric`, `threshold`, `compare`, `runbook` link tới `docs/alerts.md`.

> Ngưỡng latency **2000 ms** dùng cho lab (P95 ~2650 ms khi `rag_slow`). Production có thể nâng lên 5000 ms / 30m.

---

### 8.2 Runbook (`docs/alerts.md`)

Đã có 3 runbook: latency, error rate, cost spike — kèm **first checks**, **mitigation**, và mục **Lab verification** với lệnh test.

---

### 8.3 Script đánh giá: `scripts/evaluate_alerts.py`

Đọc `config/alert_rules.yaml`, gọi `GET /metrics` + `GET /health`, in trạng thái **OK** / **FIRING**.

```powershell
python scripts/evaluate_alerts.py
python scripts/evaluate_alerts.py --verbose
```

Exit code `0` = không alert; `2` = có alert firing.

---

### 8.4 Kết quả test

**Baseline (không incident):**

```text
Summary: 0/3 alert(s) firing
```

**Test `rag_slow`:**

```text
[FIRING] high_latency_p95 (P2) — latency_p95_ms=2651.0 (threshold gt 2000.0)
Summary: 1/3 alert(s) firing
```

**Test `tool_fail`:**

```text
[FIRING] high_error_rate (P1) — error_rate_pct=100.0 (threshold gt 5.0)
Summary: 2/3 alert(s) firing  (latency alert vẫn firing từ traffic trước)
```

**Test `cost_spike`:**

```text
[FIRING] cost_budget_spike (P2) — session_cost_usd=0.0995 (threshold gt 0.04)
Summary: 3/3 alert(s) firing
```

**Root cause khi `rag_slow` (incident response mẫu):**
- **Symptom:** P95 latency > 2s, dashboard panel 1 vượt SLO line
- **Proof:** `GET /health` → `incidents.rag_slow: true`; log `incident_enabled`; trace RAG span chậm ~2.5s
- **Fix:** `python scripts/inject_incident.py --scenario rag_slow --disable`
- **Preventive:** Alert `high_latency_p95` + runbook `docs/alerts.md#1-high-latency-p95`

---

### 8.5 Quy trình test đầy đủ

```powershell
python scripts/evaluate_alerts.py

python scripts/inject_incident.py --scenario rag_slow
python scripts/load_test.py --concurrency 5
python scripts/evaluate_alerts.py --verbose

python scripts/inject_incident.py --scenario rag_slow --disable
python scripts/inject_incident.py --scenario tool_fail
python scripts/load_test.py
python scripts/evaluate_alerts.py --verbose

python scripts/inject_incident.py --scenario tool_fail --disable
python scripts/inject_incident.py --scenario cost_spike
python scripts/load_test.py --concurrency 5
python scripts/evaluate_alerts.py --verbose

python scripts/inject_incident.py --scenario cost_spike --disable
```

---

### 8.6 Kết luận Phần 8

1. **3 alert rules** đã cấu hình với metric/threshold có thể evaluate tự động.
2. **Runbook** đủ 3 scenario + hướng dẫn lab test.
3. **Cả 3 alert** đã verify **FIRING** với incident injection tương ứng.
4. Evidence: screenshot output `evaluate_alerts.py` → `[ALERT_RULES_SCREENSHOT]` trong blueprint.

---

*Cập nhật: Phần 1–8 hoàn thành.*


