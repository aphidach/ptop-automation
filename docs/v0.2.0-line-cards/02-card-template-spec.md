# Card Template Spec

เอกสารนี้เป็น source of truth สำหรับ 12 card templates ของ v0.2.0 โดยใช้ action/postback ตามชื่อในโค้ดปัจจุบันให้มากที่สุด

## Template Summary

| # | Template | Readiness | Primary action |
| --- | --- | --- | --- |
| 1 | Start Collection | `Partial` | `start_collection` |
| 2 | Meter Request | `Ready` | image message from user |
| 3 | OCR Confirmation | `Partial` | `confirm_reading` |
| 4 | Warning Recovery | `Partial` | branch-specific |
| 5 | Progress Status | `Partial` | `show_status` |
| 6 | Batch Complete | `Partial` | report generation |
| 7 | Report Summary | `Partial` | `latest_report` / `weekly_summary` |
| 8 | History Menu | `Ready` | `history_*` |
| 9 | History Detail | `Ready` | `history_batch_detail` |
| 10 | Settings | `Ready` | `settings_*` |
| 11 | Setting Confirm | `Ready` | `settings_confirm_change` |
| 12 | Report Import | `Partial` | `settings_import_report` |

## 1. Start Collection Card

| Field | Spec |
| --- | --- |
| Use case | เปิดหรือ resume weekly collection รอบปัจจุบัน |
| Trigger | Rich Menu `บันทึกมิเตอร์`, postback `start_collection` |
| Data fields | `batch_id`, `week`, `expected_meter_count`, `next_meter_id`, `confirmed_meter_count` |
| Content | title `เริ่มบันทึกมิเตอร์`, subtitle `รอบสัปดาห์นี้ M1-M8`, short guidance, next meter |
| Visual rules | hero gradient green, solar/meter icon, one primary CTA |
| Primary action | `เริ่มบันทึก` -> `start_collection` |
| Secondary actions | `ดูสถานะ` -> `show_status`, `ยกเลิก` -> `cancel_collection` |
| Fallback | text `STATUS`, `CANCEL`, `HELP` |

Implementation note: current `build_start_collection_card()` exists but should be upgraded to include progress context and the v0.2.0 visual theme.

## 2. Meter Request Card

| Field | Spec |
| --- | --- |
| Use case | ขอให้ผู้ใช้ส่งรูปของ meter ปัจจุบัน |
| Trigger | หลัง `start_collection`, `select_meter`, `retake_photo`, หรือ progress ต่อเครื่องถัดไป |
| Data fields | `meter_id`, `batch_id`, `available_meter_ids`, `skipped_meter_ids` |
| Content | title `ถ่ายรูป M2`, instruction `ให้เห็นหน้าจอมิเตอร์ชัดเจน`, selected meter badge |
| Visual rules | camera icon, highlighted current meter chip, compact meter selector |
| Primary action | user sends image message |
| Secondary actions | `ข้าม` -> `skip_meter`, `ดูสถานะ` -> `show_status`, `ยกเลิก` -> `cancel_collection`, M1-M8 -> `select_meter` |
| Fallback | user can type `M1` to `M8` to select meter |

Implementation note: current builder is a `TextMessage` with Quick Reply. It is acceptable for v0.2.0, but the visual target is a small Flex card plus Quick Reply.

## 3. OCR Confirmation Card

| Field | Spec |
| --- | --- |
| Use case | ให้ผู้ใช้ตรวจ OCR ก่อนบันทึกลง Google Sheets |
| Trigger | OCR success and confidence acceptable |
| Data fields | `meter_id`, `current_value`, `prev_value`, `produced_unit`, `amount`, `confidence_level`, `warnings` |
| Content | title `ตรวจพบค่า`, big meter id, current kWh, previous value, produced unit, amount |
| Visual rules | current value is the largest text, success-ready green theme, warning text only when needed |
| Primary action | `ยืนยัน` -> `confirm_reading` |
| Secondary actions | `แก้ไข` -> `edit_reading`, `ถ่ายใหม่` -> `retake_photo`, `ยกเลิก` -> `cancel_collection` |
| Fallback | text `OK`, or manual correction `M2 12508` |

Implementation note: current `build_confirmation_card()` exists. v0.2.0 should refine visual hierarchy and include confidence/warning state without changing confirmation safety.

## 4. Warning Recovery Card

| Field | Spec |
| --- | --- |
| Use case | ช่วยผู้ใช้แก้สถานการณ์ OCR อ่านไม่ได้, confidence ต่ำ, ค่าต่ำกว่ารอบก่อน, duplicate reading หรือส่งรูปผิดจังหวะ |
| Trigger | OCR parse fail, confidence gate fail, validation warning, duplicate check, image sent while state is not waiting image |
| Data fields | `meter_id`, `warning_type`, `current_value`, `prev_value`, `existing_value`, `suggested_text_input`, `batch_id` |
| Content | title `ตรวจสอบก่อนบันทึก`, yellow warning panel, one-line reason, next-step copy |
| Visual rules | yellow is warning only, do not use green primary until action is safe |
| Primary action | depends on branch: `ยืนยันว่าใช่` -> `force_confirm_reading`, `แก้ไข` -> `edit_reading`, `ถ่ายใหม่` -> `retake_photo` |
| Secondary actions | `ดูสถานะ` -> `show_status`, `ยกเลิก` -> `cancel_collection` |
| Fallback | manual correction such as `M2 12508` |

Readiness detail:

- OCR unreadable and lower-value warning are `Partial`
- duplicate replace UX is `Future` until replacement behavior is fully supported

## 5. Progress Status Card

| Field | Spec |
| --- | --- |
| Use case | แสดงสถานะ batch หลังบันทึกสำเร็จหรือเมื่อผู้ใช้ขอดูสถานะ |
| Trigger | postback `show_status`, text `STATUS`, after successful confirmation |
| Data fields | `batch_id`, `week`, `current_meter_id`, `confirmed_meter_count`, `expected_meter_count`, `missing_meter_ids`, `pending_meter_id`, `next_meter_id` |
| Content | title `สถานะรอบบันทึก`, progress `5/8 เครื่อง`, meter grid M1-M8, next action |
| Visual rules | use progress bar, status dots/checks, compact missing meter summary |
| Primary action | `บันทึกต่อ` -> `start_collection` or `select_meter` for next meter |
| Secondary actions | `รายงานล่าสุด` -> `latest_report`, `Help` -> `help` |
| Fallback | text `STATUS` |

Implementation note: current status reply is text-based. v0.2.0 should introduce Flex rendering while keeping the same data source.

## 6. Batch Complete Card

| Field | Spec |
| --- | --- |
| Use case | แจ้งว่าบันทึกครบทุกเครื่องและกำลังสร้างรายงาน |
| Trigger | after confirmation makes `confirmed_meter_count == expected_meter_count` |
| Data fields | `batch_id`, `week`, `expected_meter_count`, `report_status` |
| Content | title `บันทึกครบแล้ว`, success check, text `ครบ 8/8 เครื่อง กำลังสร้างรายงาน` |
| Visual rules | green success state, minimal text, no extra options that distract from report generation |
| Primary action | automatic report generation; optional `ดูรายงานล่าสุด` -> `latest_report` after report is ready |
| Secondary actions | `ประวัติ` -> `history_batch`, `ดูสถานะ` -> `show_status` |
| Fallback | text `REPORT` |

Implementation note: current flow sends simple text and report image. Card should sit before or with report delivery.

## 7. Report Summary Card

| Field | Spec |
| --- | --- |
| Use case | สรุปรายงานล่าสุดหรือสรุปสัปดาห์ก่อน/ปัจจุบัน |
| Trigger | Rich Menu `รายงานล่าสุด`, `สรุปสัปดาห์`, auto report after complete batch, text `REPORT` |
| Data fields | `batch_id`, `week`, `total_produced_unit`, `total_amount`, `confirmed_meter_count`, `expected_meter_count`, `report_image_url`, `comparison_percent` |
| Content | title `รายงานสัปดาห์ W19`, total kWh, total amount, mini chart or report thumbnail |
| Visual rules | blue accent for chart/data, green CTA for latest report, keep totals large |
| Primary action | `ดูรายงานล่าสุด` -> `latest_report` |
| Secondary actions | `ดูรายละเอียด` -> `history_batch_detail`, `ประวัติ` -> `history`, `แชร์รายงาน` -> `Future` |
| Fallback | text `REPORT [รอบ]` |

Readiness detail: report generation exists, but `แชร์รายงาน` is `Future` unless implemented as a supported LINE action.

## 8. History Menu Card

| Field | Spec |
| --- | --- |
| Use case | จุดเริ่มต้นสำหรับดูข้อมูลย้อนหลัง |
| Trigger | Rich Menu `ประวัติ`, postback `history` |
| Data fields | optional `current_batch_id`, `latest_batch_id` |
| Content | title `ประวัติ`, options `รอบปัจจุบัน`, `สัปดาห์ก่อน`, `เลือกรอบย้อนหลัง`, `ดูตามมิเตอร์` |
| Visual rules | data blue accent, simple list rows with icons |
| Primary action | user selects one history route |
| Secondary actions | `รายงานล่าสุด` -> `latest_report`, `กลับเมนูหลัก` -> `help` or no-op navigation |
| Fallback | text `REPORT` for latest report |

Implementation note: current history menu exists as `TextMessage` with Quick Reply. It can be upgraded visually without changing routing.

## 9. History Detail Card

| Field | Spec |
| --- | --- |
| Use case | แสดงรายละเอียด batch หรือประวัติรายมิเตอร์แบบ compact |
| Trigger | `history_current`, `history_previous`, `history_batch`, `history_batch_detail`, `history_meter` |
| Data fields | `batch_id`, `week`, `status`, `readings`, `missing_meter_ids`, `total_produced_unit`, `total_amount`, `meter_id` |
| Content | title `รายละเอียดรอบ W19`, compact M1-M8 rows, total kWh and amount |
| Visual rules | table rows must stay short; use missing state chip instead of long text |
| Primary action | `ส่งรายงาน` -> `latest_report` with `batch_id` |
| Secondary actions | `กลับประวัติ` -> `history`, `ดูตามมิเตอร์` -> `history_meter`, `บันทึกต่อ` -> `start_collection` |
| Fallback | text `REPORT 2026-W19` if batch id is known |

Implementation note: current text summary/detail exists. v0.2.0 can keep text for long tables if Flex becomes too dense.

## 10. Settings Card

| Field | Spec |
| --- | --- |
| Use case | ให้ operator/admin ดูหรือจัดการ settings ตามสิทธิ์ |
| Trigger | Rich Menu `ตั้งค่า`, postback `settings` |
| Data fields | `is_admin`, `settings_values`, `meter_count`, `default_rate`, `timezone`, `report_title` |
| Content | title `ตั้งค่าระบบ`, role badge, menu rows for settings sections |
| Visual rules | gear and lock icon, neutral gray for read-only rows, green admin badge |
| Primary action | `ดูค่าปัจจุบัน` -> `settings_view` |
| Secondary actions | `มิเตอร์ M1-M8` -> `settings_meters`, `อัตราค่าไฟ` -> `settings_edit_rate`, `จำนวนเครื่อง` -> `settings_edit_expected_count`, `ชื่อรายงาน` -> `settings_edit_report_title`, `นำเข้ารายงานเก่า` -> `settings_import_report` |
| Fallback | `Help` -> `help_flow` topic `settings` |

Implementation note: role-based menu exists. Visual card should avoid showing edit actions to non-admin users.

## 11. Setting Confirm Card

| Field | Spec |
| --- | --- |
| Use case | ให้ admin ตรวจค่าเดิม/ค่าใหม่ก่อนบันทึก setting |
| Trigger | admin enters new value after `settings_edit_rate`, `settings_edit_expected_count`, or `settings_edit_report_title` |
| Data fields | `change_id`, `setting_key`, `label`, `old_value`, `new_value`, `impact` |
| Content | title `ยืนยันการแก้ไข`, compare `4.2 -> 4.5 บาท/kWh`, impact note |
| Visual rules | comparison block centered, admin lock badge, primary green confirm |
| Primary action | `ยืนยัน` -> `settings_confirm_change` with `change_id` |
| Secondary action | `ยกเลิก` -> `settings_cancel_change` |
| Fallback | if pending expires, restart from `settings` |

Implementation note: current pending setting confirmation exists and is a good candidate to convert to Flex first.

## 12. Report Import Card

| Field | Spec |
| --- | --- |
| Use case | ให้ admin นำเข้าข้อมูลจากรูปรายงานเก่า |
| Trigger | `settings_import_report`, image message while report import state is waiting, OCR preview result |
| Data fields | `pending_import_id`, `date`, `week`, `rows_count`, `expected_rows`, `total_produced_unit`, `total_amount`, `warnings`, `errors`, `duplicate` |
| Content | prompt upload, OCR preview `อ่านได้ 8/8`, totals, warning/error rows |
| Visual rules | upload/photo icon, blue for OCR/data preview, yellow for warnings, green only when confirmable |
| Primary action | `ยืนยันนำเข้า` -> `confirm_import_report` when valid |
| Secondary actions | `ยกเลิก` -> `cancel_import_report`, `กลับตั้งค่า` -> `settings`, `ดูรายละเอียด` -> `history_batch_detail` after success |
| Fallback | if OCR fails, ask for a new image; if duplicate, route to history/report instead of import |

Implementation note: current import prompt, preview, success, duplicate branches exist. v0.2.0 should unify them into one visual family.
