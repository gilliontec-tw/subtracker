# SubTrack — Roadmap

**5 phases** | **16 requirements** | 1-month delivery target

---

## Phase 1: Foundation & Security
**Goal**: 消除啟動風險、修復技術債，讓後續所有 phase 都在穩固的 codebase 上進行。
**Requirements**: SEC-01, SEC-02, DEBT-01
**Suggested model**: sonnet（SEC 項目需要理解安全語義；DEBT 重構需要跨檔案一致性）
**Plans:** 2 plans
**Success criteria**:
1. 啟動時若 `SECRET_KEY` 未設定或等於預設值，程式拒絕啟動並顯示明確錯誤訊息
2. 每個 HTTP request 都有 log 紀錄；unhandled exception 不再靜默消失，會寫入 error log
3. `passlib` 依賴已移除，`bcrypt` 直接 pin；`session.py` 頂部的過時 schema comment 已刪除
4. `annual_cost()`、`NOTIFICATION_OPTIONS`、`Jinja2Templates` 各自只定義一處，其他地方 import
5. 所有時間戳記改用 `datetime.now(timezone.utc)`，timezone-naive 問題消除
6. `pytest` 全數通過，無 regression

Plans:
- [x] 01-01-PLAN.md — SEC-01 + SEC-02: SECRET_KEY validation, JSON logging middleware, fix silent except blocks in admin.py
- [x] 01-02-PLAN.md — DEBT-01: remove passlib, delete stale session.py comment, extract annual_cost() to domain entity, create constants.py, consolidate Jinja2Templates, fix datetime timezone

---

## Phase 2: Feature Fixes
**Goal**: 修復現有功能中已知的 bug 和不完整之處，讓每個功能都可靠地工作。
**Requirements**: SUBSCR-01, NOTIF-01, NOTIF-02, USER-01
**Suggested model**: sonnet（跨 use case / route / template 的完整修復）
**Success criteria**:
1. Bulk Renew 操作後，`payment_account`、`auto_renew`、`trial_end_date`、`next_billing_date` 值保持不變
2. 通知設定頁：停用時不將空字串寫入 DB；空 email 欄位無法儲存，顯示驗證錯誤
3. Email 發送失敗時，admin 頁面顯示明確的錯誤提示，不再靜默失敗
4. Admin 可從使用者管理頁直接重置任意使用者的密碼，無需刪除帳號
5. `pytest` 全數通過，新功能有對應的 unit test

---

## Phase 3: Reports & Subscription Filtering
**Goal**: 強化報表的完整性並新增部門費用分析，同時讓訂閱清單支援有效篩選。
**Requirements**: REPORT-01, REPORT-02, REPORT-03, SUBSCR-02
**Suggested model**: sonnet（新功能開發 + Chart.js 整合）
**Success criteria**:
1. 報表頁：有多幣別訂閱時，每個幣別各自顯示一個圓餅圖（不只第一個）
2. 報表頁：顯示部門費用分析區塊，列出每個部門的年費總額，標示費用最高的部門
3. `annual_cost()` 只在一處定義，dashboard 和報表頁都 import 同一個函式
4. 訂閱清單可依「部門」、「分類」、「狀態」篩選，UI 狀態反映目前條件
5. `pytest` 全數通過

---

## Phase 4: UI Redesign
**Goal**: 套用統一的極簡視覺風格到所有頁面，提升可讀性與使用者上手速度。
**Requirements**: UI-01
**Suggested model**: sonnet（大規模 template 重構，需要視覺一致性判斷）
**UI Reference**: `SaaS Tracker Redesign v3 _standalone_.html`（靈感參考，非 pixel-perfect）
**Success criteria**:
1. 所有頁面（清單、Dashboard、表單、Admin、報表、通知設定、登入、帳號）使用統一 CSS 風格
2. 主要操作（新增訂閱、編輯、篩選）在桌面瀏覽器上 3 步驟以內完成
3. 首頁清單在 20+ 筆資料時仍保持可讀，到期日、費用、狀態一目了然
4. 純 CSS + vanilla JS，無前端 build step，不引入新 npm 依賴
5. Chrome / Edge 最新版正常顯示，無版型破版

---

## Phase 5: Deployment & Documentation
**Goal**: 讓 SubTrack 成功跑在公司 Linux VM 上，並留下讓非技術人員也能獨立維護的完整文件。
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04
**Suggested model**: sonnet（bash scripting + 技術文件需要準確細節）
**Target**: Ubuntu/Debian Linux VM；SQL Server 在同網段 Windows VM（Power Automate 機器）
**Success criteria**:
1. 執行 `deploy/install.sh` 後，服務以 gunicorn + systemd 方式運行，nginx 反向代理 port 80
2. systemd timer 每天 08:00 自動執行通知腳本（取代 Windows Task Scheduler）
3. `install.sh` 包含 Microsoft ODBC Driver for Linux 安裝步驟，可連接同網段 SQL Server
4. `.env.example` 有每個變數的中文說明、格式範例、必填 / 選填標記
5. `docs/operations.md` 涵蓋：重啟服務、查看 log、新增使用者、手動觸發通知的完整 SOP
6. `docs/database.md` 涵蓋：SQL Server 備份指令、還原步驟、緊急聯絡資訊位置

---

## Requirement Traceability

| REQ-ID | Phase | Description |
|--------|-------|-------------|
| SEC-01 | Phase 1 | SECRET_KEY 啟動驗證 |
| SEC-02 | Phase 1 | Structured logging |
| DEBT-01 | Phase 1 | 技術債修復（6 項） |
| SUBSCR-01 | Phase 2 | Bulk Renew bug 修復 |
| NOTIF-01 | Phase 2 | 通知設定頁修復 |
| NOTIF-02 | Phase 2 | Email 發送失敗提示 |
| USER-01 | Phase 2 | Admin 重置密碼 |
| REPORT-01 | Phase 3 | 多幣別圖表修復 |
| REPORT-02 | Phase 3 | 年費 helper 整合 |
| REPORT-03 | Phase 3 | 部門費用分析 |
| SUBSCR-02 | Phase 3 | 訂閱篩選強化 |
| UI-01 | Phase 4 | 全面 UI 視覺重設計 |
| DEPLOY-01 | Phase 5 | Linux 安裝腳本 |
| DEPLOY-02 | Phase 5 | .env 說明文件 |
| DEPLOY-03 | Phase 5 | 常見操作 SOP |
| DEPLOY-04 | Phase 5 | DB 備份還原說明 |
