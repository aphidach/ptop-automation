# Runtime Card Shell Plan: Scope 1-3

เอกสารนี้เป็นแผนสำหรับเก็บ 3 ช่องว่างแรกที่ยังไม่ done จากชุด `docs/v0.2.0-line-cards`

ขอบเขตนี้เน้นทำให้ card runtime เริ่มมีแกนกลางเดียวกันก่อน ยังไม่ใช่การ migrate ครบทั้ง 12 card templates และยังไม่เปลี่ยน public API หรือ postback names

## Scope

| No. | Gap | Target outcome |
| --- | --- | --- |
| 1 | Runtime LINE bot behavior ยังไม่ได้ใช้ card design จาก docs อย่างครบถ้วน | Start, Status, Batch Complete และ warning branches เริ่มเป็น Flex แล้ว แต่ยังต้องขยายไปยัง report, history, settings และ import |
| 2 | Shared `Card Shell` ยังใช้ไม่ทั่วทุก card | มี `_card_shell()` แล้วสำหรับ Start/Status แต่ยังต้อง unify Meter Request, OCR Confirmation, Batch Complete และกลุ่ม TextMessage เดิม |
| 3 | Standard LINE Flex JSON/component builders ยังไม่ครบทุกประเภท | builder บางตัวใช้ component helpers แล้ว แต่ยังต้อง migrate ทุก card ให้ตาม pattern เดียวกัน |

## Non-goals

- ยังไม่ทำให้ครบทั้ง 12 card templates ในรอบเดียว
- ยังไม่เพิ่ม postback ใหม่ถ้า action เดิมรองรับได้
- ยังไม่ทำ share/report-forwarding
- ยังไม่เปลี่ยน OCR, Google Sheets, batch หรือ parser behavior หลัก
- ยังไม่ commit `graphify-out` หรือ generated audit output เป็น deliverable

## Target Files

| File | Reason |
| --- | --- |
| `app/line/messages.py` | จุดหลักสำหรับ shared card shell และ Flex builders |
| `app/line/webhook.py` | เชื่อมข้อมูล runtime เข้า card builder โดยไม่เปลี่ยน flow |
| `tests/test_line_messages.py` | ตรวจ payload/card copy/action ที่ builder สร้าง |
| `tests/test_line_webhook_postback.py` | ตรวจ postback route ยังคืน response ที่ถูกต้อง |

## Current Runtime Audit

ตรวจจาก `02-card-template-spec.md` เทียบกับ builders ปัจจุบันใน `app/line/messages.py`

| # | Template | Runtime builder now | Card status | Uses shared shell | Remaining work |
| --- | --- | --- | --- | --- | --- |
| 1 | Start Collection | `build_start_collection_card()` -> `FlexMessage` | `Done core` | yes, `_card_shell()` | real LINE screenshot QA, hosted hero asset decision, polish against mock |
| 2 | Meter Request | `build_meter_request_message()` -> `FlexMessage` + Quick Reply | `Partial` | no | migrate into shell, use compact hero/title pattern, avoid hard-coded M1-M8 where deployment count differs |
| 3 | OCR Confirmation | `build_confirmation_card()` -> `FlexMessage` | `Partial` | no | migrate into shell, align metric rows/buttons with Start/Status, keep confidence warning state |
| 4 | Warning Recovery | `build_unreadable_prompt()`, `build_ocr_review_message()`, `build_lower_value_warning()`, `build_duplicate_warning_card()` -> `FlexMessage` | `Partial` | warning-specific shell only | decide whether warning shell should wrap `_card_shell()`, keep duplicate replacement as `Future` |
| 5 | Progress Status | `build_status_card()` -> `FlexMessage` | `Done core` | yes, `_card_shell()` | screenshot QA, complete-state copy/report readiness decision |
| 6 | Batch Complete | `build_batch_complete_card()` -> `FlexMessage` | `Partial` | no | migrate into shell, add report-ready state when report image is available |
| 7 | Report Summary | no dedicated card builder yet | `Not done` | no | create report summary Flex card around latest/weekly report data and image URL |
| 8 | History Menu | `build_history_menu_message()` -> `TextMessage` | `Not done as card` | no | convert menu options into card/list rows while keeping Quick Reply fallback |
| 9 | History Detail | `build_history_summary_message()`, `build_history_detail_message()`, `build_history_meter_message()` -> `TextMessage` | `Not done as card` | no | create compact batch/meter detail cards; keep text fallback for long tables |
| 10 | Settings | `build_settings_menu_message()`, `build_settings_view_message()`, meter/recipient/permission builders -> `TextMessage` | `Not done as card` | no | create role-aware settings cards; preserve admin gating |
| 11 | Setting Confirm | `build_settings_confirm_change_message()` -> `TextMessage` | `Not done as card` | no | create confirm card with old/new values and admin badge |
| 12 | Report Import | prompt/preview/success/duplicate builders -> `TextMessage` | `Not done as card` | no | create import prompt, preview, success and duplicate cards with valid-only confirm CTA |

Summary:

- `02-card-template-spec.md` has all 12 template types documented.
- Runtime has Flex cards for 6 template families: Start, Meter Request, OCR Confirmation, Warning Recovery, Progress Status and Batch Complete.
- Runtime has shared shell coverage for only 2 template families: Start Collection and Progress Status.
- 6 template families still rely on TextMessage presentation: Report Summary, History Menu, History Detail, Settings, Setting Confirm and Report Import.
- Therefore the card system is **not complete across all 12 types yet**.

## Phase 1: Runtime Behavior Boundary

Goal:

- lock behavior ปัจจุบันก่อนปรับ card presentation
- แยกให้ชัดว่าอะไรเป็น visual-only และอะไรเป็น state/action จริง

Tasks:

- list existing builders in `app/line/messages.py`
- list postback names ที่ Start และ Status ใช้อยู่ เช่น `start_collection`, `show_status`, `select_meter`, `cancel`
- confirm fallback text commands ยังต้องอยู่ เช่น `STATUS`, `HELP`, `CANCEL`
- add focused tests ก่อนแก้ layout ถ้ามี branch ที่ยังไม่มี coverage

Done when:

- Start และ Status flow มี test coverage สำหรับ action สำคัญ
- ไม่มี requirement ใดบังคับให้เปลี่ยน parser หรือ public postback name

Current status:

- mostly done for Start, Status, confirmation postbacks and warning branches
- still needed for report summary, history, settings and report import card migrations

## Phase 2: Shared Card Shell API

Goal:

- สร้าง API กลางที่ทำให้ card หน้าตาไปทางเดียวกัน
- ลดการ hard-code สี, spacing, badge และ button style กระจายหลายจุด

Proposed helper shape:

```python
build_card_shell(
    title: str,
    subtitle: str | None = None,
    step_badge: str | None = None,
    status_badge: str | None = None,
    hero_image_url: str | None = None,
    body_contents: list[dict] | None = None,
    primary_action: CardAction | None = None,
    secondary_actions: list[CardAction] | None = None,
)
```

Supporting helpers:

- `_primary_button(label, postback_data)`
- `_secondary_button(label, postback_data)`
- `_status_badge(text, tone="success")`
- `_metric_row(label, value, tone="default")`
- `_section_title(text)`
- `_compact_meter_grid(meter_ids, completed_ids, total_count)`

Rules:

- shell hides empty values instead of rendering placeholders like `-`
- primary action has one green filled button
- secondary actions render as outline/light buttons, maximum 2 visible
- text copy stays short enough for LINE mobile cards

Done when:

- Start and Status builders can call the same shell helper
- color and button styling are not duplicated between those two builders
- tests can assert semantic payload content without depending on exact internal helper names

Current status:

- `_card_shell()` exists and is used by Start Collection and Progress Status
- `_warning_recovery_card()` exists as a separate warning-specific shell
- remaining work is to decide whether Batch Complete, Meter Request and OCR Confirmation should call `_card_shell()` directly or use thin wrappers around it

## Phase 3: Standard Flex Builder Pattern

Goal:

- make every upgraded builder follow one predictable structure
- prepare the repo for later migration of Meter Request, OCR Confirmation and Warning Recovery

Builder pattern:

1. collect runtime data
2. normalize display data
3. select card state
4. call shared shell/helper components
5. return LINE SDK message object with current alt text pattern

Start Collection builder:

- shows `step_badge`
- shows short title and subtitle
- supports optional `hero_image_url`
- uses configured `expected_meter_count`
- does not show `เครื่องถัดไป -`
- primary action remains `start_collection`
- secondary action remains `show_status`

Status builder:

- shows `status_badge` like `2/6 เครื่อง`
- uses meter grid helper with configured total count
- shows `บันทึกต่อ` only when there is a real next meter
- complete state should prefer `รายงานล่าสุด` or no primary CTA, depending on report readiness

Done when:

- Start and Status cards are visually related in Flex payload structure
- tests prove expected count works for non-8-meter deployments
- tests prove complete status does not show a misleading next-recording CTA
- webhook postbacks still route to the same behavior as before

Current status:

- done for Start and Status core behavior
- partially done for Batch Complete and warning cards
- not done for Report Summary, History, Settings, Setting Confirm and Report Import

## Phase 4: Collection Card Cleanup

Goal:

- finish the collection set before expanding to all 12 card types

Tasks:

- refactor Meter Request into `_card_shell()` or a shell-compatible wrapper
- refactor OCR Confirmation into `_card_shell()` with metric rows and shared button hierarchy
- refactor Batch Complete into `_card_shell()` and keep report generation automatic
- keep Warning Recovery visually aligned, but do not expose replacement as active behavior
- keep all current postback names stable

Done when:

- Start, Meter Request, OCR Confirmation, Warning Recovery, Status and Batch Complete share one visual language
- no collection card uses placeholder rows such as `-`
- all collection card tests still pass

## Phase 5: Report and History Cards

Goal:

- cover template types 7-9 without making dense LINE cards unreadable

Tasks:

- add Report Summary card for latest/weekly report metadata
- keep report image delivery behavior unchanged
- convert History Menu into a card/list style response
- add compact History Detail card for batch summary
- keep long meter-by-meter details available as text fallback when Flex would be too dense

Done when:

- `latest_report`, `weekly_summary`, `history`, `history_batch`, `history_batch_detail` and `history_meter` all have card or documented card-plus-text fallback behavior
- report/history actions remain compatible with current parser and webhook routing

## Phase 6: Settings and Report Import Cards

Goal:

- cover template types 10-12 with safe admin/operator behavior

Tasks:

- convert Settings menu/view/meters into role-aware cards
- convert Setting Confirm into a confirmation card with old/new values and clear cancel action
- convert Report Import prompt, preview, success and duplicate branches into one visual family
- show `confirm_import_report` only when import preview is valid and not duplicate
- preserve non-admin restrictions exactly as current runtime behavior

Done when:

- non-admin users never see edit/confirm actions
- report import duplicate and error states do not show a green confirm CTA
- settings and import tests cover both admin and non-admin branches

## Test Plan

Focused first:

```bash
rtk uv run pytest tests/test_line_messages.py tests/test_line_webhook_postback.py
```

Then full suite:

```bash
rtk uv run pytest
```

Required assertions:

- Start card contains configured range/count such as `M1-M6` and `0/6 เครื่อง`
- Start card does not contain stale `M1-M8` when expected count is 6
- Status card contains `บันทึกแล้ว 2/6 เครื่อง`
- Status card does not contain `บันทึกแล้ว 2/8 เครื่อง` when total count is 6
- complete Status card does not show `บันทึกต่อ` when no next meter exists
- duplicate warning does not append `kWh` to placeholder text such as `มีข้อมูลเดิม`
- Report Summary card routes to `latest_report`, history detail and history menu without exposing `share_report`
- History cards route to current, previous, batch detail and meter history
- Settings cards hide admin-only actions for non-admin users
- Report Import preview shows confirm action only for valid non-duplicate import
- postback names remain stable

## Acceptance Criteria

- scope 1 is done when runtime Start and Status responses use v0.2.0 card presentation without changing behavior
- scope 2 is done when a shared card shell/helper layer exists and Start/Status both use it
- scope 3 is done when upgraded builders follow the same data-normalize-shell-return pattern
- all 12 template types have either a Flex card builder or a consciously documented card-plus-text fallback
- each remaining TextMessage builder has an explicit migration decision: convert, keep as fallback, or defer
- all focused tests pass
- full test suite passes or any unrelated failure is documented with exact reason

## Recommended Next Order

1. Refactor Meter Request, OCR Confirmation and Batch Complete to use the shared shell language
2. Add Report Summary card, because it is the largest missing user-facing card type
3. Convert History Menu and one History Detail path before expanding every history branch
4. Convert Settings menu/view and Setting Confirm with admin/non-admin tests
5. Convert Report Import prompt/preview/success/duplicate states
6. Capture real LINE screenshots and compare against `05-visual-alignment-plan.md`
