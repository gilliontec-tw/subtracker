# SubTrack — v1 Requirements

> 目標：1 個月內完成功能完善、UI 重設計、修復安全問題、部署上線、留下完整文件。

---

## v1 Requirements

### 訂閱管理 (Subscription Management)

- [ ] **SUBSCR-01**: Bulk Renew 時不清空 Phase 2B 欄位（payment_account、auto_renew、trial_end_date、next_billing_date）
- [ ] **SUBSCR-02**: 使用者可依部門、分類、狀態篩選訂閱清單（在現有前端 JS 篩選基礎上補強）

### 通知系統 (Notifications)

- [ ] **NOTIF-01**: 通知設定頁修復——空 email 不儲存、停用時不寫空字串到 DB
- [ ] **NOTIF-02**: Email 發送失敗時，admin 介面顯示明確錯誤提示（邀請信、通知信均適用）

### 報表與數據 (Reports)

- [ ] **REPORT-01**: 多幣別報表圖表修復——每個幣別各有自己的圓餅圖，不只顯示第一個
- [ ] **REPORT-02**: 年費試算 helper 整合——消除 `annual_cost()` 在兩處重複定義的問題，提取為共用函式
- [ ] **REPORT-03**: 部門費用分析——顯示每個部門的年費總額，標示費用最高的部門

### 使用者與權限 (Users & Permissions)

- [ ] **USER-01**: Admin 可直接重置任意使用者密碼（不需刪除帳號重建）

### 安全與系統 (Security & System)

- [ ] **SEC-01**: 啟動時若 SECRET_KEY 未設定或使用預設值，立即拋出錯誤並中止啟動
- [ ] **SEC-02**: 加入 structured logging——request log、error log，錯誤不再靜默吞掉
- [ ] **DEBT-01**: 修復技術債務
  - passlib/bcrypt 衝突（移除 passlib，直接 pin bcrypt）
  - `session.py` 頂部過時的 schema comment 刪除或替換為指向 `models.py` 的指引
  - `annual_cost()` 重複定義（REPORT-02 一起處理）
  - `NOTIFICATION_OPTIONS` 重複定義（提取為共用常數）
  - `Jinja2Templates` 在四個 router 各自實例化（提取為共用實例）
  - `datetime.now()` 改為 `datetime.utcnow()` 或 `datetime.now(timezone.utc)`

### UI 視覺設計 (UI Redesign)

- [ ] **UI-01**: 全面視覺重新設計——所有頁面套用統一的極簡風格（以專案根目錄 mockup 為靈感，不必 pixel-perfect）
  - 涵蓋：首頁清單、Dashboard、Create/Edit 表單、Admin 面板、報表、通知設定、登入、帳號設定

### 部署與文件 (Deployment & Documentation)

- [ ] **DEPLOY-01**: Linux 安裝與啟動腳本——自動化安裝 Python 依賴、ODBC driver、gunicorn service、nginx 設定、systemd timer（取代 Windows Task Scheduler）
- [ ] **DEPLOY-02**: `.env` 配置說明文件——所有環境變數的用途、格式範例、必填 vs 選填
- [ ] **DEPLOY-03**: 常見操作 SOP——重啟服務、查看 log、新增使用者、手動觸發通知的步驟
- [ ] **DEPLOY-04**: 資料庫備份與還原說明——SQL Server 定期備份設定方法與還原步驟

---

## v2 Requirements（本次暫緩）

- 忘記密碼自助流程（目前 admin 重置即可）
- Audit log 分頁與篩選（目前功能夠用）
- Health check endpoint（/health 路由，給監控工具用）
- CSV 匯出
- 通知錯過補發機制（目前若排程 miss 就永遠錯過）
- 密碼複雜度驗證

---

## Out of Scope

- **Icon emoji 欄位** — 使用者確認不需要，DB column 保留但不在 UI 呈現
- **多公司 / 多租戶** — 純內部單一公司工具
- **行動 App** — 桌面瀏覽器已足夠
- **SSO / OAuth / 企業 IdP** — 邀請制足夠
- **自動抓信用卡訂閱資料** — 手動輸入即可
- **DB-level server-side 搜尋** — 前端篩選配合 UI 改善已足夠

---

## Traceability

*(由 Roadmap 填入)*

| REQ-ID | Phase |
|--------|-------|
| SUBSCR-01 | Phase 2 |
| SUBSCR-02 | Phase 3 |
| NOTIF-01 | Phase 2 |
| NOTIF-02 | Phase 2 |
| REPORT-01 | Phase 3 |
| REPORT-02 | Phase 3 |
| REPORT-03 | Phase 3 |
| USER-01 | Phase 2 |
| SEC-01 | Phase 1 |
| SEC-02 | Phase 1 |
| DEBT-01 | Phase 1 |
| UI-01 | Phase 4 |
| DEPLOY-01 | Phase 5 |
| DEPLOY-02 | Phase 5 |
| DEPLOY-03 | Phase 5 |
| DEPLOY-04 | Phase 5 |
