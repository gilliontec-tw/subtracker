# SubTrack

## What This Is

SubTrack 是一個公司內部 SaaS 訂閱管理工具。讓 IT / 財務 / 各部門主管在同一個地方追蹤所有軟體訂閱的到期日、費用、負責部門，並在到期前自動發送 Email 通知，避免服務突然中斷或費用失控。

目標使用者：公司內部行政、IT、財務人員，不需要技術背景。

## Core Value

**到期日前就知道，不在服務中斷後才發現。** 所有訂閱、費用、通知集中一處，讓負責人不需要靠記憶或 Excel 追蹤。

## Design Philosophy

**極簡、好上手、功能齊全。** 介面以最少點擊完成常見操作，功能覆蓋訂閱管理的完整生命週期，讓非技術背景的接手人也能立刻使用。

## Requirements

### Validated

已實作並運作中的功能：

- ✓ 訂閱 CRUD（建立、讀取、更新、刪除）
- ✓ Email 通知（可設定提前天數、多個收件人）
- ✓ 邀請制使用者註冊（Admin 建立 → 邀請連結 → 使用者設密碼）
- ✓ 角色與細粒度權限（admin、can_create、can_update、can_delete）
- ✓ Admin 管理面板（使用者管理、審計日誌）
- ✓ Dashboard（費用總覽、即將到期清單）
- ✓ 基本報表（依幣別、分類的費用統計）
- ✓ Phase 2B 資料欄位（cost、currency、department、billing_cycle、payment_account、auto_renew、trial_end_date、next_billing_date、status）

### Active

本次里程碑要完成的目標：

- [ ] 完成 Phase 2B 尾聲（icon_emoji 全流程貫通、bulk renew 補齊 2B 欄位）
- [ ] 通知設定頁面完整化（email 驗證、空值保護）
- [ ] 報表多幣別圖表修復
- [ ] 全面 UI 視覺重新設計（以現有 mockup 為準，極簡風格）
- [ ] 安全強化（SECRET_KEY 啟動驗證、structured logging、email send 失敗提示）
- [ ] Bug 修復（passlib/bcrypt 衝突、stale schema comment、duplicated helpers）
- [ ] 部署到公司 Linux VM（Python app on Linux，SQL Server 留在現有 Windows Power Automate VM）
- [ ] 完整部署與維運文件（讓接手人無需技術背景也能操作）

### Out of Scope

- 多公司 / 多租戶架構 — 純內部單一公司工具
- 行動 App — 內網工具，桌面瀏覽器已足夠
- SSO / OAuth — 內部邀請制足夠，無需對接企業 IdP
- 自動從 credit card 抓訂閱資料 — 手動輸入即可

## Context

- **現況**：目前只跑在開發者自己的電腦，尚未對公司同事提供服務
- **部署目標**：Linux VM（公司內部）+ SQL Server on 現有 Windows Power Automate VM（內網連線）
- **時間壓力**：開發者一個月後離職，需在離職前完成部署並留下文件
- **接手人**：尚未確定，文件需假設接手人為非技術背景
- **未提交的在製品**：Phase 2B 部分已完成但未提交；有一份全新視覺 mockup（`SaaS Tracker Redesign v3 _standalone_.html`）；untracked 檔案包括 notifications route、config_option entities、static CSS、多個 templates

## Constraints

- **Tech Stack**: Python + FastAPI + Jinja2（伺服器端渲染，無前端建構步驟）— 不換框架
- **Database**: SQL Server（公司標準，留在 Windows VM）— 不換資料庫
- **Timeline**: 1 個月（不可延）
- **Ops**: Linux VM 環境尚未存在，需要從頭設定；通知排程改用 systemd timer 取代 Windows Task Scheduler
- **Maintenance**: 接手人技術程度未知，部署與維運必須文件化到「照抄就能動」

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SQL Server 留在 Windows VM | 公司現有授權與基礎設施，避免資料遷移風險 | — Pending |
| Python app 部署到 Linux VM | 避免額外 Windows Server 授權；Linux 更適合 uvicorn/gunicorn 長期運行 | — Pending |
| 維持 server-side rendering（Jinja2） | 不引入前端建構流程，降低接手維護複雜度 | — Pending |
| 全面套用新視覺設計 | 現有 mockup 已完成，一次到位比分頁重構更省力 | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-06 after initialization*
