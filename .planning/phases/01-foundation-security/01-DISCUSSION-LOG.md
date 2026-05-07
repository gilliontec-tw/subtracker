# Phase 1: Foundation & Security - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-07
**Phase:** 1-Foundation & Security
**Areas discussed:** Logging 函式庫選擇, Log 輸出目的地, annual_cost() scope

---

## Logging 函式庫選擇

| Option | Description | Selected |
|--------|-------------|----------|
| stdlib logging | 內建、零新依賴、與現有 notifications.py log 設定風格一致。配 JSON formatter 可輸出 structured JSON。 | ✓ |
| structlog | 真正的 structured logging，JSON 輸出之外支援 context binding。加一個新依賴；API 與 stdlib 不同需學習成本。 | |
| loguru | 最簡單的 API，一行 import 即用。但輸出不是 JSON 格式（除非另設），另加一個不常見的小依賴。 | |

**User's choice:** stdlib logging
**Notes:** 無附加說明。

---

## Log 格式

| Option | Description | Selected |
|--------|-------------|----------|
| JSON 格式 | `{"timestamp": "…", "level": "INFO", "method": "GET", "path": "/", "status": 200}`。方便未來用 grep/jq 查詢，也方便接監控工具。 | ✓ |
| 純文字格式 | `2026-05-07 08:00:01 INFO GET / 200` — 較小簡單，但難以程式化分析。 | |

**User's choice:** JSON 格式

---

## Request Logging 範圍

| Option | Description | Selected |
|--------|-------------|----------|
| 所有 request + 錯誤 | 每個 HTTP request 記錄一行（method、path、status、耗時），unhandled exception 記錄完整 traceback。最容易發現問題。 | ✓ |
| 僅錯誤 | 404、500 才記錄，正常 request 不打 log。Log 量少但問題追蹤會更少線索。 | |

**User's choice:** 所有 request + 錯誤

---

## Logging 初始化位置

| Option | Description | Selected |
|--------|-------------|----------|
| app.py lifespan 事件 | 在 FastAPI app 啟動時配置 logging，與 SECRET_KEY 檢查放在同一位置。一目瞭然。 | ✓ |
| 獨立的 logging_config.py | 建一個 `src/interfaces/web/logging_config.py`，在 app.py import 時即自動設置。可復用但多一個檔案。 | |

**User's choice:** app.py lifespan 事件

---

## Log 輸出目的地（Web Layer）

| Option | Description | Selected |
|--------|-------------|----------|
| stdout 專用 | systemd journald 自動收集、自動 rotation。接手人用 `journalctl -u subtrack` 即可查詢。部署簡單、零額外設定。 | ✓ |
| stdout + log 檔並存 | stdout 一份給 systemd，同時寫 log/web.log。查詢方式多但需要設定 rotation。 | |
| log 檔專用 | 寫 logs/web.log，與 notifications.log 風格一致。但在 systemd 環境中需要另行設定 rotation，Phase 5 尖點增加工作。 | |

**User's choice:** stdout 專用

---

## notifications.py Log 變更

| Option | Description | Selected |
|--------|-------------|----------|
| 保持現狀（檔案） | notifications.log 是 cron/Task Scheduler 工作，離線執行。檔案對調試這類工作比較直覺。Phase 5 再決定是否改。 | ✓ |
| 一起改為 stdout | systemd timer 執行的腳本 stdout 也會到 journald，一致性更強。但 Phase 5 才會設定 systemd timer，現在改有點早。 | |

**User's choice:** 保持現狀（檔案）

---

## annual_cost() 整合 Phase

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 1 一起做 | 現在就提取共用 helper，Phase 3 的 REPORT-02 只需 import 它。連貫性較少、不容易忘。 | ✓ |
| defer 到 Phase 3 | 現在等待，Phase 3 做 REPORT-02 時一起提取。但如果 Phase 3 倒序就可能忘掉。 | |

**User's choice:** Phase 1 一起做
**Notes:** ROADMAP.md 與 REQUIREMENTS.md 有衝突（ROADMAP 說 Phase 1，REQUIREMENTS 說與 REPORT-02 一起）。用戶選擇遵循 ROADMAP.md。

---

## annual_cost() 提取層

| Option | Description | Selected |
|--------|-------------|----------|
| domain entity 方法 | `Subscription.annual_cost()` — 到期費用是 domain 行為，放層對的。 | ✓ |
| 獨立 utility 函式 | `src/interfaces/web/utils.py` 或 `src/application/utils.py`，兩個 route 都 import。簡單但 billing 邏輯存在 interface layer。 | |

**User's choice:** domain entity 方法

---

## Claude's Discretion

- **SEC-01 check trigger**: app.py lifespan event（使用者確認了 logging init 的位置，SEC-01 check 自然跟在一起）
- **DEBT-01 其他 5 項**: 做法明確（remove passlib、delete comment、extract NOTIFICATION_OPTIONS to constants.py、consolidate Jinja2Templates in dependencies.py、datetime.now() → datetime.now(timezone.utc)）— 使用者未有異議

## Deferred Ideas

- Cookie `secure` flag — Phase 5（需要 nginx + HTTPS 先就位）
- `UserRole` / `BillingCycle` enum — LOW 嚴重性，不在 DEBT-01 範圍
- Log rotation for notifications.log — Phase 5 部署工作
- Health check endpoint — v2 requirement
