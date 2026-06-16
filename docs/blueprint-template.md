# Day 13 Observability Lab Report

> **Instruction**: Fill in all sections below. This report is designed to be parsed by an automated grading assistant. Ensure all tags (e.g., `[GROUP_NAME]`) are preserved.

## 1. Team Metadata
- [GROUP_NAME]: 
- [REPO_URL]: 
- [MEMBERS]:
  - Member A: [Name] | Role: Logging & PII
  - Member B: [Name] | Role: Tracing & Enrichment
  - Member C: [Name] | Role: SLO & Alerts
  - Member D: [Name] | Role: Load Test & Dashboard
  - Member E: [Name] | Role: Demo & Report

---

## 2. Group Performance (Auto-Verified)
- [VALIDATE_LOGS_FINAL_SCORE]: 100/100
- [TOTAL_TRACES_COUNT]: 10+
- [PII_LEAKS_FOUND]: 0

---

## 3. Technical Evidence (Group)

### 3.1 Logging & Tracing
- [EVIDENCE_CORRELATION_ID_SCREENSHOT]: screenshot/sc-logs-correlation-id.png
- [EVIDENCE_PII_REDACTION_SCREENSHOT]: screenshot/sc-logs-pii-redaction.png
- [EVIDENCE_TRACE_WATERFALL_SCREENSHOT]: screenshot/sc-langfuse-waterfall.png
- [TRACE_WATERFALL_EXPLANATION]: Span `run` wraps the agent pipeline. With `rag_slow` enabled, latency jumps ~2.5s (RAG sleep), visible in trace duration and matching log `latency_ms` plus alert `high_latency_p95`.

### 3.2 Dashboard & SLOs
- [DASHBOARD_6_PANELS_SCREENSHOT]: screenshot/sc-dashboard-6-panels.png
- [SLO_TABLE]:
| SLI | Target | Window | Current Value |
|---|---:|---|---:|
| Latency P95 | < 3000ms | 28d | ~2651ms (incident) / ~152ms (normal) |
| Error Rate | < 2% | 28d | 0% (normal) |
| Cost Budget | < $2.5/day | 1d | ~$0.10 (session, lab) |

### 3.3 Alerts & Runbook
- [ALERT_RULES_SCREENSHOT]: screenshot/sc1.png
- [SAMPLE_RUNBOOK_LINK]: docs/alerts.md#1-high-latency-p95

---

## 4. Incident Response (Group)
- [SCENARIO_NAME]: rag_slow
- [SYMPTOMS_OBSERVED]: P95 latency > 2000ms; dashboard panel 1 spikes; users see ~2.6s+ response time
- [ROOT_CAUSE_PROVED_BY]: GET /health shows incidents.rag_slow=true; log event incident_enabled; Langfuse trace shows slow RAG path
- [FIX_ACTION]: python scripts/inject_incident.py --scenario rag_slow --disable
- [PREVENTIVE_MEASURE]: Alert high_latency_p95 + runbook docs/alerts.md#1-high-latency-p95

---

## 5. Individual Contributions & Evidence

### [MEMBER_A_NAME]
- [TASKS_COMPLETED]: 
- [EVIDENCE_LINK]: (Link to specific commit or PR)

### [MEMBER_B_NAME]
- [TASKS_COMPLETED]: 
- [EVIDENCE_LINK]: 

### [MEMBER_C_NAME]
- [TASKS_COMPLETED]: 
- [EVIDENCE_LINK]: 

### [MEMBER_D_NAME]
- [TASKS_COMPLETED]: 
- [EVIDENCE_LINK]: 

### [MEMBER_E_NAME]
- [TASKS_COMPLETED]: 
- [EVIDENCE_LINK]: 

---

## 6. Bonus Items (Optional)
- [BONUS_COST_OPTIMIZATION]: (Description + Evidence)
- [BONUS_AUDIT_LOGS]: (Description + Evidence)
- [BONUS_CUSTOM_METRIC]: (Description + Evidence)
