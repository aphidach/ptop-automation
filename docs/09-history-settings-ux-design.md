# History and Settings LINE UX Design

## Goal

ออกแบบเมนู `ประวัติ` และ `ตั้งค่า` ให้ใช้งานได้จริงใน LINE Bot แทนการตอบว่าอยู่ระหว่างเตรียมใช้งาน

สองเมนูนี้มีบทบาทต่างกันชัดเจน:

- `ประวัติ`: ดูข้อมูลย้อนหลังแบบ read-only สำหรับ operator และ admin
- `ตั้งค่า`: ดูและแก้ค่าระบบแบบมีสิทธิ์ สำหรับ admin เท่านั้นในส่วนที่แก้ไขข้อมูล

## Assumptions

- ระบบใช้ weekly batch เป็นรอบหลัก
- มีมิเตอร์หลัก `M1` ถึง `M8`
- ข้อมูลธุรกิจอยู่ใน Google Sheets tabs: `meters`, `readings`, `batches`, `settings`
- ผู้ใช้ทั่วไปควรดูข้อมูลได้ แต่ไม่ควรแก้ configuration
- Text commands เดิม เช่น `REPORT`, `STATUS`, `HELP` ยังต้องใช้ได้เป็น fallback
- ทุกหน้าจอใน LINE ต้องมี action ถัดไป ไม่จบด้วยข้อความตัน

## UX Principles

1. `ประวัติ` ต้องช่วยหาข้อมูลเร็ว ไม่บังคับให้ผู้ใช้จำ batch id
2. `ตั้งค่า` ต้องแยกการดูข้อมูลกับการแก้ข้อมูลอย่างชัดเจน
3. การแก้ setting ทุกครั้งต้องมี confirmation ก่อนบันทึก
4. Operator ต้องมีทางดูค่าปัจจุบันและติดต่อ admin ได้
5. Admin ต้องเห็นผลกระทบของการแก้ไขก่อนยืนยัน
6. Empty state ต้องเสนอ action ต่อ เช่น เริ่มบันทึก, ดูรายงานล่าสุด, กลับเมนูหลัก

## System 1: History

### Purpose

`ประวัติ` เป็นศูนย์ดูข้อมูลย้อนหลังของรอบบันทึกและรายงาน ไม่ควรใช้สำหรับแก้ข้อมูล

Primary jobs:

- ดูรอบปัจจุบัน
- ดูสัปดาห์ก่อน
- เลือกรอบย้อนหลัง
- ดูข้อมูลตามมิเตอร์
- ส่งรูปรายงานล่าสุด

### Entry Point

Rich Menu action:

```text
history
```

Bot should reply with a Flex or Quick Reply menu:

```text
ประวัติการบันทึกมิเตอร์

เลือกรายการที่ต้องการดูครับ
```

Actions:

```text
รอบปัจจุบัน
สัปดาห์ก่อน
เลือกรอบย้อนหลัง
ดูตามมิเตอร์
รายงานล่าสุด
กลับเมนูหลัก
```

### Current Batch View

Use when user selects `รอบปัจจุบัน`.

If there is an active/current batch:

```text
ประวัติรอบปัจจุบัน

รอบ: 2026-W19
สถานะ: collecting
บันทึกแล้ว: 5/8 เครื่อง
ยังขาด: M6, M7, M8
รวมผลิต: 2,640 kWh
ยอดเงินรวม: 11,088 บาท
```

Actions:

```text
ดูรายละเอียด
บันทึกต่อ
ส่งรายงาน
สัปดาห์ก่อน
```

If no current batch exists:

```text
ยังไม่มีประวัติการบันทึกในรอบนี้ครับ
```

Actions:

```text
เริ่มบันทึกมิเตอร์
ดูรายงานล่าสุด
Help
```

### Previous Week View

Use when user selects `สัปดาห์ก่อน`.

```text
ประวัติสัปดาห์ก่อน

รอบ: 2026-W18
บันทึกแล้ว: 8/8 เครื่อง
รวมผลิต: 4,120 kWh
ยอดเงินรวม: 17,304 บาท
```

Actions:

```text
ดูรายละเอียด
ส่งรูปรายงาน
ดูรอบก่อนหน้า
กลับประวัติ
```

### Batch Detail View

Show a compact meter table. Keep the LINE text short; use report image for full detail.

```text
รายละเอียดรอบ 2026-W19

M1: 12,508 kWh (+508)
M2: 9,820 kWh (+410)
M3: ยังไม่มีข้อมูล
M4: ยังไม่มีข้อมูล
```

Actions:

```text
ส่งรูปรายงาน
ดูตามมิเตอร์
บันทึกต่อ
กลับประวัติ
```

### Meter History View

Use when user selects `ดูตามมิเตอร์`.

First ask for meter:

```text
ต้องการดูประวัติมิเตอร์เครื่องไหนครับ
```

Quick replies:

```text
M1
M2
M3
M4
M5
M6
M7
M8
กลับประวัติ
```

Then show latest readings:

```text
ประวัติ M1

2026-W19: 12,508 kWh (+508)
2026-W18: 12,000 kWh (+420)
2026-W17: 11,580 kWh (+395)
```

Actions:

```text
ส่งรายงานล่าสุด
เลือกเครื่องอื่น
กลับประวัติ
```

### History Postback Actions

| Action | Required Data | Behavior |
| --- | --- | --- |
| `history` | none | Open history main menu |
| `history_current` | none | Show current weekly batch summary |
| `history_previous` | none | Show previous weekly batch summary |
| `history_batch` | `batch_id` | Show summary for selected batch |
| `history_batch_detail` | `batch_id` | Show meter-level detail for selected batch |
| `history_meter` | `meter_id` | Show latest readings for one meter |
| `history_select_week` | none | Ask user to choose or type week reference |
| `latest_report` | `batch_id` optional | Send latest available report image |
| `start_collection` | none | Continue to collection flow |
| `help` | none | Show help |

### History Empty States

| Scenario | Message | Primary Action |
| --- | --- | --- |
| No current batch | ยังไม่มีประวัติการบันทึกในรอบนี้ครับ | `start_collection` |
| Batch exists but no readings | รอบนี้ยังไม่มีค่ามิเตอร์ครับ | `start_collection` |
| No report image yet | ยังไม่มีรูปรายงานสำหรับรอบนี้ครับ | `generate_report` or `start_collection` |
| Meter has no history | ยังไม่มีประวัติของ M1 ครับ | `start_collection` |
| Google Sheets unavailable | ยังดึงประวัติไม่ได้ครับ กรุณาลองใหม่อีกครั้ง | `history` |

### History Data Rules

- Current batch should use the active session batch if available.
- If there is no active session batch, derive current batch from the current ISO week and LINE source id.
- Latest report should prefer the newest `batches.report_image_url`.
- Meter history should sort readings by `created_at` descending.
- Amount and produced unit should come from saved readings, not be recalculated in the chat layer.

## System 2: Settings

### Purpose

`ตั้งค่า` เป็นเมนูดูและจัดการ configuration ของระบบ ต้องมี permission boundary ชัดเจน

Operator can:

- ดูการตั้งค่าปัจจุบัน
- ดูรายชื่อมิเตอร์
- ติดต่อผู้ดูแล

Admin can:

- แก้ข้อมูลมิเตอร์
- แก้อัตราค่าไฟ
- แก้ชื่อรายงาน
- แก้จำนวนเครื่องต่อรอบ
- จัดการผู้รับรายงาน
- จัดการสิทธิ์ผู้ใช้งาน

### Entry Point

Rich Menu action:

```text
settings
```

Bot must check user role before showing edit actions.

### Operator View

For non-admin users:

```text
ตั้งค่าระบบ

คุณสามารถดูการตั้งค่าปัจจุบันได้
การแก้ไขต้องใช้สิทธิ์ผู้ดูแลระบบ
```

Actions:

```text
ดูการตั้งค่าปัจจุบัน
ดูรายชื่อมิเตอร์
ติดต่อผู้ดูแล
Help
```

### Admin View

For admin users:

```text
ตั้งค่าระบบ

เลือกสิ่งที่ต้องการจัดการครับ
```

Actions:

```text
มิเตอร์ M1-M8
อัตราค่าไฟ
จำนวนเครื่องต่อรอบ
ชื่อรายงาน
ผู้รับรายงาน
สิทธิ์ผู้ใช้งาน
```

### Current Settings View

```text
การตั้งค่าปัจจุบัน

จำนวนมิเตอร์: 8 เครื่อง
รอบบันทึก: รายสัปดาห์
อัตราเริ่มต้น: 4.2 บาท/kWh
Timezone: Asia/Bangkok
ชื่อรายงาน: Solar Weekly Report
```

Operator actions:

```text
ดูรายชื่อมิเตอร์
ติดต่อผู้ดูแล
กลับเมนูหลัก
```

Admin actions:

```text
แก้อัตราค่าไฟ
แก้ชื่อรายงาน
แก้จำนวนเครื่อง
กลับตั้งค่า
```

### Meter Settings Flow

Admin chooses `มิเตอร์ M1-M8`.

```text
ตั้งค่ามิเตอร์

เลือกเครื่องที่ต้องการดูหรือแก้ไข
```

Quick replies:

```text
M1
M2
M3
M4
M5
M6
M7
M8
กลับตั้งค่า
```

Meter detail:

```text
มิเตอร์ M1

ชื่อ: Solar 1
ตำแหน่ง: อาคาร A
ลำดับรายงาน: 1
สถานะ: active
อัตรา: 4.2 บาท/kWh
```

Admin actions:

```text
แก้ชื่อ
แก้ตำแหน่ง
แก้อัตรา
เปิด/ปิดใช้งาน
กลับมิเตอร์
```

### Rate Settings Flow

When admin chooses `อัตราค่าไฟ`:

```text
อัตราค่าไฟปัจจุบัน

ค่าเริ่มต้น: 4.2 บาท/kWh

ต้องการแก้เป็นเท่าไหร่ครับ
พิมพ์ตัวเลข เช่น 4.5
```

After admin enters value:

```text
ยืนยันการแก้อัตราค่าไฟ

ค่าเดิม: 4.2 บาท/kWh
ค่าใหม่: 4.5 บาท/kWh

ค่านี้จะใช้กับการบันทึกครั้งถัดไป
```

Actions:

```text
ยืนยัน
ยกเลิก
```

### Report Settings Flow

```text
ตั้งค่ารายงาน

ชื่อรายงานปัจจุบัน:
Solar Weekly Report
```

Actions:

```text
แก้ชื่อรายงาน
ดูรายงานล่าสุด
กลับตั้งค่า
```

When editing title, require confirmation:

```text
ยืนยันชื่อรายงานใหม่

ชื่อเดิม: Solar Weekly Report
ชื่อใหม่: ข้อมูลการผลิตไฟฟ้า Solar Cells
```

Actions:

```text
ยืนยัน
ยกเลิก
```

### Report Recipients Flow

This controls where generated reports should be pushed.

```text
ผู้รับรายงาน

ส่งอัตโนมัติ: เปิด
ปลายทางหลัก: LINE group ปัจจุบัน
ผู้รับเพิ่มเติม: 2 รายการ
```

Admin actions:

```text
เปิด/ปิดส่งอัตโนมัติ
เพิ่มผู้รับ
ลบผู้รับ
ทดสอบส่งรายงาน
```

### User Permission Flow

```text
สิทธิ์ผู้ใช้งาน

Admin: 2 คน
Operator: 8 คน
Allowlist: เปิด
```

Admin actions:

```text
เพิ่ม Admin
เพิ่ม Operator
ลบผู้ใช้
ดูรายการทั้งหมด
```

For safety, permission changes should require confirmation and should log to `audit_log`.

### Settings Postback Actions

| Action | Required Data | Behavior |
| --- | --- | --- |
| `settings` | none | Open settings menu after role check |
| `settings_view` | none | Show current settings |
| `settings_meters` | none | Show meter list |
| `settings_meter_detail` | `meter_id` | Show one meter configuration |
| `settings_edit_meter` | `meter_id`, `field` | Ask admin for new meter value |
| `settings_edit_rate` | none or `meter_id` | Ask admin for new rate |
| `settings_edit_report_title` | none | Ask admin for report title |
| `settings_recipients` | none | Show report recipient settings |
| `settings_permissions` | none | Show user permission settings |
| `settings_confirm_change` | `change_id` | Apply pending setting change |
| `settings_cancel_change` | `change_id` | Cancel pending setting change |
| `help` | none | Show help |

### Settings Permission Rules

| Role | View Settings | Edit Settings | Manage Users | Send Test Report |
| --- | --- | --- | --- | --- |
| Operator | yes | no | no | no |
| Admin | yes | yes | yes | yes |
| Owner | yes | yes | yes | yes |

Recommended MVP role source:

- Use environment variable allowlists first.
- Later move roles to a `settings` or `users` worksheet.

Example environment variables:

```text
ADMIN_LINE_USER_IDS=Uxxxx,Uyyyy
ALLOWED_LINE_USER_IDS=Uxxxx,Uyyyy
ALLOWED_LINE_SOURCE_IDS=Cxxxx,Uxxxx
```

### Settings Write Rules

- Never update Google Sheets immediately after a user enters a value.
- Create a pending setting change first.
- Show old value, new value, and impact.
- Apply only after admin confirms.
- Log every confirmed change to `audit_log`.
- If the admin cancels, discard the pending change.

### Settings Empty and Error States

| Scenario | Message | Primary Action |
| --- | --- | --- |
| User is not admin | การแก้ไขต้องใช้สิทธิ์ผู้ดูแลระบบครับ | `settings_view` |
| Invalid number | กรุณาพิมพ์ตัวเลข เช่น 4.5 | retry same step |
| Unknown meter | ไม่พบมิเตอร์นี้ครับ | `settings_meters` |
| Sheets write failed | บันทึกการตั้งค่าไม่สำเร็จ กรุณาลองใหม่ | `settings` |
| Pending change expired | หมดเวลายืนยันการแก้ไขแล้วครับ | restart edit flow |

## Data Model Additions

The existing `settings` tab can support simple key-value settings.

Recommended keys:

| key | example | notes |
| --- | --- | --- |
| `expected_meter_count` | `8` | Number of meters in one batch |
| `default_rate` | `4.2` | Default THB/kWh |
| `timezone` | `Asia/Bangkok` | Used for week/date |
| `report_title` | `Solar Weekly Report` | Report image title |
| `auto_send_report` | `true` | Push report when complete |
| `report_recipient_ids` | `Cxxxx,Uyyyy` | Comma-separated LINE ids for MVP |

Optional future tab:

```text
users
```

Suggested columns:

| column | example |
| --- | --- |
| line_user_id | Uxxxx |
| display_name | Somchai |
| role | admin |
| active | TRUE |
| created_at | 2026-05-04T09:00:00+07:00 |

## Implementation Phases

### Phase A: Replace Placeholder Replies

- Implement `history` main menu
- Implement `settings` main menu
- Keep both menus read-only except existing report actions

Done when:

- Pressing `ประวัติ` shows usable actions
- Pressing `ตั้งค่า` shows current settings or admin menu

### Phase B: History Read Views

- Add current batch summary
- Add previous batch summary
- Add batch detail view
- Add meter history view

Done when:

- User can inspect recent readings without typing `REPORT`

### Phase C: Settings Read Views

- Add current settings view
- Add meter settings detail view
- Add role-based menu branching

Done when:

- Operator can view settings but cannot see edit actions
- Admin can see edit actions

### Phase D: Settings Write Flow

- Add pending setting change session state
- Add confirmation and cancellation
- Write confirmed changes to Google Sheets
- Log changes to `audit_log`

Done when:

- Admin can update a setting safely from LINE

### Phase E: Hardening

- Persist session state outside memory
- Add role/allowlist storage
- Add audit detail for all settings changes
- Add tests for all postback actions and permission branches

Done when:

- Settings changes are safe enough for production use

## Acceptance Criteria

History is ready when:

- `ประวัติ` no longer returns a placeholder message
- User can view current batch, previous batch, and meter history
- Empty states always offer a useful next action
- User can request latest report from the history menu

Settings is ready when:

- `ตั้งค่า` no longer returns a placeholder message
- Operator can view settings but cannot edit them
- Admin can edit settings only after confirmation
- Every confirmed change is logged to `audit_log`
- Invalid input and failed writes are recoverable without restarting the chat
