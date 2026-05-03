# Implementation Plan for v0.2.0 Cards

เอกสารนี้เป็น handoff สำหรับรอบพัฒนา code หลังจาก design docs ชุดนี้ ไม่ใช่รายการที่ถูก implement แล้วในรอบเอกสาร

## Guardrails

- ไม่บันทึก OCR ลง Google Sheets โดยไม่มี confirmation
- คง text commands เดิมไว้ครบ
- ใช้ postback names เดิมก่อนเพิ่ม action ใหม่
- อย่าแสดง action ที่ยังไม่รองรับจริงเป็น primary CTA
- แก้ card presentation แบบ incremental เพื่อไม่กระทบ flow ที่ใช้งานได้อยู่แล้ว

## Phase 1: Flex Foundation

Touchpoints:

- `app/line/messages.py`
- `tests/test_line_messages.py`
- `tests/test_line_webhook_postback.py`

Tasks:

- เพิ่ม shared style constants สำหรับ color tokens และ common spacing
- เพิ่ม helper สำหรับ primary/secondary/warning buttons
- เพิ่ม helper สำหรับ status badge, metric row, meter grid และ section title
- คง return type เป็น LINE SDK message objects ตาม pattern ปัจจุบัน

Done when:

- existing message tests pass
- builders สร้าง Flex payload ได้โดยไม่เปลี่ยน behavior หลัก

## Phase 2: Collection Cards

Implement or upgrade:

- Start Collection Card
- Meter Request Card
- OCR Confirmation Card
- Warning Recovery Card
- Progress Status Card
- Batch Complete Card

Tasks:

- upgrade `build_start_collection_card()`
- convert meter request/status from text-first to card or card plus Quick Reply
- refine `build_confirmation_card()` visual hierarchy
- unify unreadable, low confidence, lower value, duplicate and retake prompts under Warning Recovery visual pattern

Done when:

- user can complete M1-M8 with card-guided flow
- postback behavior remains compatible with current parser/webhook
- every warning branch has edit, retake, or cancel recovery

## Phase 3: Report, History, and Settings Cards

Implement or upgrade:

- Report Summary Card
- History Menu Card
- History Detail Card
- Settings Card
- Setting Confirm Card
- Report Import Card

Tasks:

- add report summary Flex before or with report image
- upgrade history menu/detail presentation without losing compact text fallback
- upgrade role-based settings menu and setting confirmation
- unify report import prompt, preview, success, and duplicate messages visually

Done when:

- all Rich Menu buttons return a card or card-like guided response
- operator/admin split is visible and safe
- report import never shows confirm CTA when pending import has errors or duplicate data

## Phase 4: Parser and Webhook Gaps

Touchpoints:

- `app/line/parser.py`
- `app/line/webhook.py`
- `tests/test_line_parser.py`
- `tests/test_line_webhook_postback.py`

Tasks:

- keep existing postback names stable
- add only missing postback data fields needed by cards, such as `batch_id` or `change_id`
- mark unsupported visual actions as disabled, omitted, or `Future` in docs until implemented
- avoid adding share/report-forwarding until desired behavior is explicit

Done when:

- all card actions are parseable
- unsupported actions are not visible as active buttons

## Phase 5: Tests

Required tests:

- Rich Menu postbacks still route to the same high-level behavior
- Start Collection returns start card plus next meter request
- OCR Confirmation includes confirm, edit, retake and cancel actions
- Warning Recovery supports unreadable OCR and lower-value warning
- `STATUS` and `show_status` render progress data
- History menu routes to current, previous, recent week and meter history
- Settings menu hides edit actions for non-admin users
- Setting confirm applies only after `settings_confirm_change`
- Report Import preview shows confirm only when import is valid
- fallback text commands `M1`, `M1 12508`, `OK`, `STATUS`, `REPORT`, `HELP`, `CANCEL` still work

Verification command:

```bash
rtk pytest
```

## Phase 6: Rollout Checklist

- Run full unit test suite
- Generate and inspect sample Flex payloads for the 12 templates
- Validate Rich Menu upload locally with `rtk make richmenu-check`
- Confirm Help Flow image URLs are HTTPS in deployment environment
- Field test one complete M1-M8 batch in a LINE test group
- Test OCR unreadable, manual correction, lower-value warning and report import duplicate
- Keep text fallback docs visible in Help

## Non-goals for v0.2.0 Implementation

- Web admin dashboard
- Multi-tenant configuration
- Native LINE report sharing workflow
- Full duplicate replacement unless explicitly scoped
- Replacing Google Sheets storage
- Changing OCR provider behavior

## Acceptance Criteria

- All 12 card templates have a matching builder or documented fallback
- All 6 Rich Menu buttons lead to guided card-based responses
- Current text command fallback remains compatible
- No OCR value is saved without explicit confirmation
- Admin-only actions are not exposed to non-admin users
- Tests cover core postback routing and card actions
