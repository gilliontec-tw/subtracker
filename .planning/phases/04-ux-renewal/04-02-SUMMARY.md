---
phase: "04"
plan: "02"
subsystem: frontend
tags: [subscriptions, batch-renew, ux, checkboxes, wallet]
dependency_graph:
  requires: [04-01]
  provides: [batch-renew-ui, wallet-payment-shortcut]
  affects: [SubscriptionTable, BatchRenewDialog, subscriptions-api]
tech_stack:
  added: []
  patterns: [useMutation, useQueryClient, TanStack Query invalidation]
key_files:
  created:
    - frontend/src/components/subscriptions/BatchRenewDialog.tsx
  modified:
    - frontend/src/api/subscriptions.ts
    - frontend/src/components/subscriptions/SubscriptionTable.tsx
decisions:
  - Eligibility computed client-side (preview before POST) then only eligible IDs sent to backend
  - Trash icon removed from row actions; replaced by Wallet icon for payment creation shortcut
  - canCreate drives both wallet icon visibility and hasActions (not canDelete)
  - addCycle uses JS Date arithmetic, no external library dependency
metrics:
  duration: ~15min
  completed: "2026-06-01"
  tasks_completed: 3
  files_changed: 3
---

# Phase 04 Plan 02: Subscription Table UX Redesign + Batch Renewal Summary

**One-liner:** Checkbox-per-row selection with batch-renewal dialog (showing old→new dates, skipping ineligible), wallet icon for payment creation, trash icon removed from table rows.

## What Was Built

### Task 1 — batchRenewSubscriptions API function
Added `batchRenewSubscriptions(ids: number[])` to `frontend/src/api/subscriptions.ts`. Also exported `BatchRenewSkipped` and `BatchRenewResult` types. Uses existing `ApiResponse<T>` wrapper pattern.

### Task 2 — BatchRenewDialog component
New file `frontend/src/components/subscriptions/BatchRenewDialog.tsx`:
- Accepts `subscriptions[]` (already filtered to selected rows by parent)
- Computes eligibility client-side: ineligible if `status !== 'active'` or `billing_cycle == null`
- Shows each subscription's eligibility status and projected `expiry_date → newExpiry` using `addCycle()`
- Summary line: "將續訂 X 筆，略過 Y 筆"
- On confirm, POSTs only eligible IDs; invalidates `['subscriptions']` cache; calls `onSuccess` to clear selection

### Task 3 — SubscriptionTable redesign
Modified `frontend/src/components/subscriptions/SubscriptionTable.tsx`:
- Added leading checkbox column (header select-all with indeterminate state, per-row checkbox)
- Added `selectedIds: Set<number>` state, `paymentSubId`, `batchOpen` state
- "續訂 (N)" button appears above table when at least one row selected
- Replaced trash icon (`canDelete`) with wallet icon (`canCreate`) in actions column
- `hasActions` now driven by `canUpdate || canCreate` (not canDelete)
- `colSpan` updated to 9 (with actions) or 8 (without) for the empty state row
- Added `PaymentRecordFormDialog` and `BatchRenewDialog` at bottom of JSX
- Removed `DeleteConfirmDialog` import (no longer used in rows)

## Success Criteria Verification

- D-01: wallet icon opens PaymentRecordFormDialog per row — implemented via `setPaymentSubId(sub.id)`
- D-05: trash icon removed from subscription table rows — DeleteConfirmDialog removed from rows
- D-06: action column keeps pencil + wallet — both rendered when canUpdate/canCreate
- D-07: checkbox per row + header select-all with indeterminate — implemented
- D-08: 续订 button appears above table when >=1 selected — `{selectedIds.size > 0 && ...}`
- D-10/D-11: BatchRenewDialog shows old→new dates, flags ineligible — implemented
- D-13: after success, selectedIds cleared — `onSuccess={() => setSelectedIds(new Set())}`
- D-14: only eligible (active + billing_cycle) IDs sent to POST — `eligibleIds` computed before mutate

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. All features are fully wired.

## Threat Flags

None. No new network endpoints, auth paths, or schema changes introduced on the frontend.

## Self-Check: PASSED

Files created/modified:
- FOUND: frontend/src/api/subscriptions.ts (batchRenewSubscriptions added)
- FOUND: frontend/src/components/subscriptions/BatchRenewDialog.tsx (new)
- FOUND: frontend/src/components/subscriptions/SubscriptionTable.tsx (redesigned)
