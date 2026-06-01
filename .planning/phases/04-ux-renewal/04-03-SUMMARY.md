---
phase: "04"
plan: "03"
subsystem: frontend
tags: [ux, form, delete, billing_cycle, subscription]
dependency_graph:
  requires: []
  provides: [delete-in-edit-form, billing-cycle-required]
  affects: [SubscriptionForm, SubscriptionEditPage]
tech_stack:
  added: []
  patterns: [useMutation-inside-form, controlled-select-with-watch]
key_files:
  created: []
  modified:
    - frontend/src/components/subscriptions/SubscriptionForm.tsx
    - frontend/src/pages/SubscriptionEditPage.tsx
decisions:
  - Moved delete mutation inside SubscriptionForm so edit mode is self-contained — no prop-drilling of callbacks
  - Used `value={billingCycle ?? ''}` on Select (controlled) instead of `defaultValue` so null billing_cycle always shows placeholder
  - toFormValues return type changed to Partial<FormValues> so null billing_cycle passes through without fake fallback
metrics:
  duration: "~15 min"
  completed: "2026-06-01"
  tasks_completed: 2
  files_changed: 2
---

# Phase 04 Plan 03: billing_cycle required + delete danger zone

Removed the silent `?? 'monthly'` fallback from `toFormValues`, wired the billing_cycle Select as a controlled component (`value={watch('billing_cycle')}`), and added a 「刪除訂閱」 danger zone with confirmation dialog in edit mode only.

## Tasks Completed

| # | Task | Files |
|---|------|-------|
| 1 | Fix toFormValues — no auto-fill billing_cycle | SubscriptionForm.tsx |
| 2 | Add delete danger button (edit mode only) | SubscriptionForm.tsx, SubscriptionEditPage.tsx |

## What Was Built

**Task 1 — billing_cycle required (D-15)**

- `toFormValues` return type changed from `FormValues` to `Partial<FormValues>`
- `billing_cycle` mapping changed from `sub.billing_cycle ?? 'monthly'` to `sub.billing_cycle as FormValues['billing_cycle']` — null passes through
- `Props.defaultValues` type widened to `Partial<FormValues>` to accept null billing_cycle
- billing_cycle `<Select>` changed from `defaultValue` to `value={billingCycle ?? ''}` (controlled) — shows "請選擇" placeholder when unset
- Zod schema unchanged: `billing_cycle` remains a required enum; submitting without selecting shows 「請選擇計費週期」

**Task 2 — Delete danger zone (D-09)**

- Added optional `subscriptionId?: number` and `serviceName?: string` props to SubscriptionForm
- `isEditMode = subscriptionId !== undefined && serviceName !== undefined` — both must be present
- `useMutation(deleteSubscription)` inside SubscriptionForm:
  - `onSuccess`: invalidates subscriptions cache, shows toast 「{serviceName}」已刪除, navigates to /subscriptions
  - `onError`: shows destructive toast 「刪除失敗」
- Danger zone section appears below save/cancel buttons (edit mode only):
  - border-t border-destructive/30, h3 「危險操作」, description 「刪除後無法復原。」
  - `type="button"` variant="destructive" to avoid form submission
- Confirmation dialog mirrors DeleteConfirmDialog.tsx structure:
  - Title: 確認刪除
  - Description: 確定要刪除「{serviceName}」嗎？此操作無法復原。
  - Footer: 取消 (outline) + 確認刪除 (destructive)
- `SubscriptionEditPage.tsx` updated to pass `subscriptionId={subId}` and `serviceName={subscription.service_name}`
- `SubscriptionNewPage.tsx` unchanged — does not pass these props, no delete UI appears

## Verification Results

- `npx tsc --noEmit`: PASSED (no output = no errors)
- `npm run lint`: PASSED (0 errors, 0 warnings after removing spurious eslint-disable directive)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — delete action is already protected by existing auth guards (require_can_delete) on the backend.

## Self-Check: PASSED

- frontend/src/components/subscriptions/SubscriptionForm.tsx — modified, exists
- frontend/src/pages/SubscriptionEditPage.tsx — modified, exists
- SubscriptionNewPage.tsx — untouched, no delete props
- tsc clean, lint clean
