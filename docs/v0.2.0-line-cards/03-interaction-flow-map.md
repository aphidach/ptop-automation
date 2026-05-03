# Interaction Flow Map

เอกสารนี้ map ทางเดินหลักจาก Rich Menu ไปยัง card templates และ fallback commands สำหรับ v0.2.0

## Main Rich Menu

Rich Menu ยังใช้ 6 ปุ่มหลักเหมือนเดิม และแยกสิทธิ์ใน flow หลังจากกดปุ่ม ไม่แยกเมนูหลักตาม role

| Menu | Postback | First card | Notes |
| --- | --- | --- | --- |
| บันทึกมิเตอร์ | `start_collection` | Start Collection -> Meter Request | flow หลักของ operator |
| สรุปสัปดาห์ | `weekly_summary` | Report Summary | ใช้ current session batch ถ้ามี |
| รายงานล่าสุด | `latest_report` | Report Summary | ส่ง report image เมื่อมี URL |
| ประวัติ | `history` | History Menu | read-only สำหรับทุก role |
| ตั้งค่า | `settings` | Settings | role-based content |
| Help | `help` | Help Flow menu | ส่ง image help ตาม topic |

## Collection Happy Path

```text
Rich Menu: บันทึกมิเตอร์
-> Start Collection Card
-> Meter Request Card: M1
-> user sends image
-> OCR Confirmation Card
-> user confirms
-> Progress Status Card
-> Meter Request Card: M2
-> repeat until M8
-> Batch Complete Card
-> Report Summary Card + report image
```

Rules:

- default sequence is `M1 -> M8`
- every OCR value must be confirmed before writing to Google Sheets
- after each confirmed reading, show progress and next meter
- text fallback must remain available at every step

## OCR and Recovery Branches

| Scenario | Card | Primary recovery |
| --- | --- | --- |
| OCR reads valid value | OCR Confirmation | `confirm_reading` |
| OCR confidence low | Warning Recovery | manual correction or `retake_photo` |
| OCR unreadable | Warning Recovery | type `M2 12508` or retake |
| value lower than previous | Warning Recovery | `force_confirm_reading`, edit, or retake |
| duplicate reading | Warning Recovery | show existing data; replacement remains `Future` unless implemented |
| image sent at wrong time | Warning Recovery or Meter Request | confirm intended meter or choose correct meter |

## State Transition Map

| State | User-visible card | Expected user action | Next state |
| --- | --- | --- | --- |
| `idle` | Start Collection | tap start | `collecting` |
| `collecting` | Meter Request | send image or select meter | `waiting_image` / `processing_ocr` |
| `waiting_image` | Meter Request | send meter photo | `processing_ocr` |
| `processing_ocr` | processing text or status | wait | `waiting_confirmation` or `waiting_manual_value` |
| `waiting_confirmation` | OCR Confirmation or Warning Recovery | confirm, edit, retake, cancel | `collecting` |
| `waiting_manual_value` | Warning Recovery | type corrected value | `collecting` |
| `completed` | Batch Complete | wait for report | `reporting` |
| `reporting` | Report Summary | view report/history | `idle` or `reported` |

## Report Flow

```text
Rich Menu: รายงานล่าสุด
-> Report Summary Card
-> report image if available
-> actions: ดูรายละเอียด, ประวัติ, Help
```

```text
Rich Menu: สรุปสัปดาห์
-> Report Summary Card for current/session batch
-> if no active data, show empty state with Start Collection
```

`แชร์รายงาน` is a visual design option only and must be marked `Future` until a supported send/share behavior is implemented.

## History Flow

```text
Rich Menu: ประวัติ
-> History Menu Card
-> รอบปัจจุบัน / สัปดาห์ก่อน / เลือกรอบย้อนหลัง / ดูตามมิเตอร์
-> History Detail Card
-> optional Report Summary or report image
```

Empty states must offer at least one useful next action:

- no current batch -> `start_collection`
- no report image -> `latest_report` if available, otherwise `start_collection`
- no meter history -> choose another meter or start collection

## Settings Flow

### Operator

```text
Rich Menu: ตั้งค่า
-> Settings Card with read-only actions
-> ดูค่าปัจจุบัน / ดูรายชื่อมิเตอร์ / ติดต่อผู้ดูแล / Help
```

Operator must not see edit actions in primary card content.

### Admin

```text
Rich Menu: ตั้งค่า
-> Settings Card with admin badge
-> edit rate / edit expected count / edit report title / import old report
-> Setting Confirm Card
-> settings updated and audit logged
```

Admin write rules:

- never write immediately after text input
- always show old value, new value, and impact
- only `settings_confirm_change` writes to Google Sheets
- `settings_cancel_change` discards pending change

## Report Import Flow

```text
Settings Card
-> นำเข้ารายงานเก่า
-> Report Import Card: upload prompt
-> admin sends report image
-> OCR preview in Report Import Card
-> confirm import or cancel
-> success routes to History Detail and Report Summary
```

If duplicate data exists, do not import again. Route to existing history/report.

## Help Flow Integration

Help remains the place for longer visual explanation. Cards should stay short.

| Help topic | Image |
| --- | --- |
| `start_collection` | `docs/help-flows/original/start-collection-board-ai.png` |
| `confirm_reading` | `docs/help-flows/original/confirm-reading-board-ai.png` |
| `latest_report` | `docs/help-flows/original/latest-report-board-ai.png` |
| `history` | `docs/help-flows/original/history-board-ai.png` |
| `settings` | `docs/help-flows/original/settings-board-ai.png` |
| `settings_admin` | `docs/help-flows/original/settings-admin-board-ai.png` |
| `import_report` | `docs/help-flows/original/import-report-board-ai.png` |
| `troubleshooting` | `docs/help-flows/original/troubleshooting-board-ai.png` |
| `text_commands` | `docs/help-flows/original/text-commands-board-ai.png` |

## Fallback Text Commands

| Text | Behavior | Card equivalent |
| --- | --- | --- |
| `M1` to `M8` | select meter | Meter Request |
| `M1 12508` | manual correction | OCR Confirmation / Warning Recovery |
| `OK` | confirm pending OCR | OCR Confirmation |
| `STATUS` | show progress | Progress Status |
| `REPORT [รอบ]` | send report | Report Summary |
| `HELP` | open help | Help Flow menu |
| `CANCEL` | cancel pending operation | current flow cancel |

Fallback commands must stay documented because field use may be faster with text in some cases.
