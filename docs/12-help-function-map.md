# Help Function Map

## Goal

เอกสารนี้สรุปฟังก์ชันที่ระบบ LINE bot มีอยู่ตอนนี้ เพื่อใช้เป็นฐานสำหรับทำเมนู `Help` และรูปภาพ flow การใช้งานในอนาคต

Success criteria:

- รู้ว่า Rich Menu แต่ละปุ่มเรียก action อะไร
- รู้ว่าฟังก์ชันไหนพร้อมทำ Help image ก่อน
- รู้ว่าฟังก์ชันไหนเป็น flow ย่อยหรือ fallback command
- รู้ว่าส่วนไหนยังเป็น placeholder หรือ partial implementation

## Source Snapshot

อ้างอิงจากโค้ดหลัก:

- `app/line/richmenu.py`
- `app/line/parser.py`
- `app/line/messages.py`
- `app/line/webhook.py`
- `app/services/history_service.py`
- `app/services/settings_service.py`
- `app/services/report_import_service.py`

## Main Rich Menu Functions

| User-facing menu | Postback action | Current behavior | Help image priority | Notes |
| --- | --- | --- | --- | --- |
| บันทึกมิเตอร์ | `start_collection` | เริ่มหรือเปิด weekly batch ปัจจุบัน ล้าง skip state แล้วพาไปเครื่องถัดไปตามลำดับ `M1` ถึง `M8` | High | เป็น flow หลักที่สุด ควรทำภาพแรก |
| สรุปสัปดาห์ | `weekly_summary` | ส่งรายงานของ batch ที่อยู่ใน session ถ้ามี | Medium | ตอนกดจาก Rich Menu โดยไม่มี active batch อาจตอบว่า `ยังไม่มีข้อมูลรอบนี้ครับ` |
| รายงานล่าสุด | `latest_report` | หา batch ล่าสุดที่มี report image หรือ batch ล่าสุด แล้วส่งรายงานผ่าน LINE | High | ควรทำ Help image ร่วมกับสรุปสัปดาห์หรือแยกเป็นภาพสั้น |
| ประวัติ | `history` | เปิดเมนูประวัติ แล้วเลือกดูรอบปัจจุบัน สัปดาห์ก่อน รอบย้อนหลัง หรือดูตามมิเตอร์ | High | เป็นฟังก์ชัน read-only ที่ผู้ใช้ทั่วไปน่าจะใช้บ่อย |
| ตั้งค่า | `settings` | เปิดเมนูตั้งค่าแบบ role-based: operator ดูได้, admin แก้บางค่าได้ | High | ควรแยกรูป operator/admin ถ้าทำละเอียด |
| Help | `help` | ส่งข้อความช่วยเหลือแบบสั้น | High | จุดนี้ควรเปลี่ยนเป็น Quick Reply menu สำหรับเลือกรูป flow |

## Collection Functions

ฟังก์ชันกลุ่มนี้เกี่ยวกับการบันทึกค่ามิเตอร์รายสัปดาห์

| Function | Entry point | Current behavior | Help content |
| --- | --- | --- | --- |
| Start collection | `start_collection` | สร้าง/เปิด batch, ตั้ง state เป็น collecting, หา meter ถัดไป, ส่ง start card และข้อความให้ถ่ายรูป | ภาพ `start-collection-board-ai.png` |
| Select meter | `select_meter` + `meter_id` | เลือกเครื่องเอง เช่น `M1` ถึง `M8` แล้วรอรูป | รวมในภาพบันทึกมิเตอร์ หรือทำเป็น FAQ |
| Send meter photo | image message | ดาวน์โหลดรูปจาก LINE, ส่ง OCR, สร้าง pending confirmation | รวมในภาพบันทึกมิเตอร์ |
| Confirm reading | `confirm_reading` หรือ text `OK` | ยืนยัน pending OCR แล้วบันทึกลง Google Sheets | ภาพ `confirm-reading-board-ai.png` |
| Force confirm lower value | `force_confirm_reading` | ยอมบันทึกค่าที่ต่ำกว่าครั้งก่อนหลัง warning | FAQ หรือ troubleshooting |
| Edit reading | `edit_reading` หรือ text `M1 12508` | ให้ผู้ใช้กรอกค่าถูกต้องเอง แล้วบันทึกผ่าน manual confirm | ภาพ `confirm-reading-board-ai.png` |
| Retake photo | `retake_photo` | ล้าง pending confirmation แล้วให้ถ่ายรูปใหม่ | ภาพ `confirm-reading-board-ai.png` หรือ FAQ |
| Skip meter | `skip_meter` | mark เครื่องนั้นเป็น skipped ชั่วคราว แล้วไปเครื่องถัดไป | FAQ |
| Show status | `show_status` หรือ text `STATUS` | แสดง meter ปัจจุบัน, pending, progress, missing meters | ภาพ `troubleshooting-board-ai.png` หรือ `text-commands-board-ai.png` |
| Cancel collection | `cancel_collection` หรือ text `CANCEL` | reset collection session และ clear pending confirmation | FAQ |

## OCR and Recovery Functions

| Scenario | Current behavior | Suggested Help/FAQ |
| --- | --- | --- |
| OCR อ่านได้และ confidence ดี | ส่ง Flex confirmation card ให้กดยืนยัน แก้ไข ถ่ายใหม่ หรือยกเลิก | รวมใน `confirm-reading-board-ai.png` |
| OCR อ่านไม่ได้ | ตั้ง state เป็น `waiting_manual_value` แล้วให้พิมพ์ค่าเอง เช่น `M1 12508` | `troubleshooting-board-ai.png` |
| OCR confidence ต่ำ | ส่งข้อความเตือนให้แก้เอง ถ่ายใหม่ หรือยืนยันว่าใช่ | `troubleshooting-board-ai.png` |
| ค่าปัจจุบันต่ำกว่าครั้งก่อน | ส่ง warning พร้อมปุ่มยืนยันว่าใช่ แก้ไข หรือถ่ายใหม่ | `troubleshooting-board-ai.png` |
| เครื่องนี้ถูกบันทึกใน batch แล้ว | แจ้งว่ามีค่าเดิมอยู่แล้ว และการแทนที่จะเพิ่มในเวอร์ชันถัดไป | `troubleshooting-board-ai.png` |
| ส่งรูปผิดจังหวะ | ถ้ากำลังรอยืนยันหรือ OCR อยู่ ระบบจะให้แก้เอง/ถ่ายใหม่แทน | FAQ |

## Report Functions

| Function | Entry point | Current behavior | Help content |
| --- | --- | --- | --- |
| Generate/send report | text `GEN [รอบ]`, text `REPORT [รอบ]`, `latest_report`, `weekly_summary` | เรียก `send_report()` เพื่อสร้าง/ส่งรูป report | `latest-report-board-ai.png` |
| Auto report after complete batch | ครบทุก meter ใน batch | ส่งข้อความว่าครบ 8 เครื่อง แล้วเรียก `send_report_if_complete()` | รวมใน `start-collection-board-ai.png` |
| Report image generation | backend service | สร้างรูปจาก readings ใน batch และบันทึก URL กลับ batch | ไม่ต้องทำ Help แยกสำหรับผู้ใช้ |
| Report delivery | backend service | ส่งรูปผ่าน LINE image message โดยต้องมี HTTPS URL | ไม่ต้องทำ Help แยกสำหรับผู้ใช้ |

## History Functions

| Function | Entry point | Current behavior | Help content |
| --- | --- | --- | --- |
| History menu | `history` | แสดงเมนูประวัติหลัก | `history-board-ai.png` |
| Current batch | `history_current` | แสดงสรุปรอบปัจจุบัน ถ้าไม่มีข้อมูลให้ empty state พร้อมปุ่มต่อ | `history-board-ai.png` |
| Previous week | `history_previous` | แสดงสรุป batch ก่อนหน้า | `history-board-ai.png` |
| Select recent week | `history_select_week` | แสดงรายการย้อนหลังประมาณ 1 เดือน สูงสุด 5 รอบ | `history-board-ai.png` |
| Batch summary | `history_batch` + `batch_id` | แสดง summary ของ batch ที่เลือก | `history-board-ai.png` |
| Batch detail | `history_batch_detail` + `batch_id` | แสดงค่า `M1` ถึง `M8` แบบ compact | `history-board-ai.png` |
| Meter history | `history_meter` + optional `meter_id` | ให้เลือก meter แล้วแสดง readings ล่าสุดของเครื่องนั้น | `history-board-ai.png` หรือ FAQ |

## Settings Functions

| Function | Entry point | Current behavior | Role | Help content |
| --- | --- | --- | --- | --- |
| Settings menu | `settings` | แสดงเมนูตามสิทธิ์ | Operator/Admin | `settings-board-ai.png` |
| View current settings | `settings_view` | แสดงจำนวนมิเตอร์, รอบบันทึก, default rate, timezone, report title | Operator/Admin | `settings-board-ai.png` |
| Meter list | `settings_meters` | แสดง active meters จาก Google Sheets | Operator/Admin | `settings-board-ai.png` |
| Meter detail | `settings_meter_detail` + `meter_id` | แสดงชื่อ, ตำแหน่ง, sort order, active, default rate | Operator/Admin | `settings-board-ai.png` |
| Edit default rate | `settings_edit_rate` | Admin กรอกค่าใหม่ แล้วต้อง confirm ก่อนบันทึก | Admin | `settings-admin-board-ai.png` |
| Edit expected meter count | `settings_edit_expected_count` | Admin กรอกจำนวนเครื่องต่อรอบ แล้วต้อง confirm ก่อนบันทึก | Admin | `settings-admin-board-ai.png` |
| Edit report title | `settings_edit_report_title` | Admin กรอกชื่อรายงานใหม่ แล้วต้อง confirm ก่อนบันทึก | Admin | `settings-admin-board-ai.png` |
| Confirm setting change | `settings_confirm_change` | บันทึก setting ลง Google Sheets และ log audit | Admin | `settings-admin-board-ai.png` |
| Cancel setting change | `settings_cancel_change` | ยกเลิก pending setting change | Admin | `settings-admin-board-ai.png` |
| Report recipients | `settings_recipients` | แสดงสถานะผู้รับรายงานและปุ่มดูรายงานล่าสุด | Admin | Later |
| Permissions | `settings_permissions` | แสดงว่า MVP ใช้ env allowlist/admin list | Admin | Later |
| Contact admin | `settings_contact_admin` | แจ้งให้ติดต่อ admin ใน LINE group หรือเพิ่ม user id ใน env | Operator/Admin | FAQ |
| Edit meter detail | `settings_edit_meter` | ยังเป็น placeholder: จะเพิ่มในเฟสถัดไป | Admin | Later |

## Report Import Functions

ฟังก์ชันนี้อยู่ใต้เมนู `ตั้งค่า` และใช้สำหรับ admin นำเข้าข้อมูลจากรูปรายงานเก่า

| Function | Entry point | Current behavior | Help content |
| --- | --- | --- | --- |
| Start old report import | `settings_import_report` | ตรวจสิทธิ์ admin แล้วขอให้ส่งรูปรายงานเก่า | `import-report-board-ai.png` |
| Upload report image | image message while import state is waiting | OCR ตารางจากรูปรายงานเก่า แล้วสร้าง preview | `import-report-board-ai.png` |
| Preview report import | automatic after OCR | แสดงวันที่ รอบ จำนวนแถว ยอดผลิต ยอดเงิน warning/error | `import-report-board-ai.png` |
| Confirm report import | `confirm_import_report` | บันทึก batch/readings 8 แถวและสร้าง report image | `import-report-board-ai.png` |
| Cancel report import | `cancel_import_report` | reset report import session | `import-report-board-ai.png` |
| Duplicate report import | automatic validation | ถ้ารอบนั้นมีข้อมูลแล้ว จะไม่ import ซ้ำ | FAQ |

## Text Fallback Commands

คำสั่งเหล่านี้ยังควรอยู่ใน Help เพราะช่วยให้ผู้ใช้แก้สถานการณ์เฉพาะหน้าได้

| Command | Behavior | Should show in Help |
| --- | --- | --- |
| `M1` ถึง `M8` | เลือกมิเตอร์และรอรูป | Yes |
| `M1 12508` | กรอกค่าเองหรือแก้ค่า OCR | Yes |
| `OK` | ยืนยันค่า pending ล่าสุด | Yes |
| `STATUS` | ดูสถานะ batch/current meter | Yes |
| `GEN [รอบ]` | สร้าง/ส่งรูปรายงานของ batch ที่ระบุหรือ current batch | Admin/dev only |
| `REPORT [รอบ]` | ส่งรูปรายงานของ batch ที่ระบุหรือ current batch | Yes |
| `HELP` | แสดงคำสั่งสั้น | Yes |
| `CANCEL` | ยกเลิก pending confirmation | Yes |

## Recommended Help Menu

เมื่อผู้ใช้กด `Help` ควรเปลี่ยนจากข้อความสั้นเป็น Quick Reply menu แบบนี้

```text
ต้องการดูวิธีใช้งานส่วนไหนครับ?
```

Quick replies:

```text
บันทึกมิเตอร์
ยืนยัน/แก้ OCR
ดูสถานะ
รายงานล่าสุด
ประวัติ
ตั้งค่า
นำเข้ารายงานเก่า
คำสั่งพิมพ์เอง
ติดต่อแอดมิน
```

จำนวนปุ่มยังไม่เกิน limit ของ LINE quick reply และครอบคลุมฟังก์ชันหลักในระบบปัจจุบัน

## Recommended Help Images

เริ่มจากภาพหลักที่จำเป็นก่อน

| Asset | Covers | Priority |
| --- | --- | --- |
| `docs/help-flows/start-collection-board-ai.png` | เริ่มบันทึก, ถ่าย M1-M8, ครบแล้วส่งรายงาน | P0 |
| `docs/help-flows/confirm-reading-board-ai.png` | ตรวจ OCR, ยืนยัน, แก้ไข, ถ่ายใหม่ | P0 |
| `docs/help-flows/latest-report-board-ai.png` | ดูรายงานล่าสุดและสรุปสัปดาห์ | P0 |
| `docs/help-flows/history-board-ai.png` | ดูรอบปัจจุบัน, สัปดาห์ก่อน, ย้อนหลัง, ตามมิเตอร์ | P1 |
| `docs/help-flows/settings-board-ai.png` | ดู settings, รายชื่อมิเตอร์, ติดต่อ admin | P1 |
| `docs/help-flows/settings-admin-board-ai.png` | แก้ rate, จำนวนเครื่อง, ชื่อรายงาน พร้อม confirmation | P2 |
| `docs/help-flows/import-report-board-ai.png` | นำเข้ารายงานเก่าจากรูป | P2 |
| `docs/help-flows/troubleshooting-board-ai.png` | OCR ไม่ชัด, ค่าต่ำกว่าเดิม, duplicate, ส่งรูปผิดจังหวะ | P2 |
| `docs/help-flows/text-commands-board-ai.png` | คำสั่ง fallback ทั้งหมด | P2 |

## First Image Scripts

### `start-collection-board-ai.png`

```text
หัวข้อ: วิธีเริ่มบันทึกค่ามิเตอร์

1. กดเมนู “บันทึกมิเตอร์”
2. ระบบเปิดรอบบันทึกประจำสัปดาห์
3. ระบบบอกเครื่องถัดไป เช่น M1
4. ถ่ายรูปมิเตอร์ให้ชัดเจน
5. ตรวจค่า OCR แล้วกดยืนยัน
6. ทำต่อจนครบ M1 ถึง M8
7. เมื่อครบ ระบบสร้างและส่งรูปรายงานให้อัตโนมัติ
```

### `confirm-reading-board-ai.png`

```text
หัวข้อ: วิธียืนยันหรือแก้ค่า OCR

1. หลังส่งรูป ระบบอ่านค่ามิเตอร์ด้วย OCR
2. ตรวจเครื่องและค่าที่ระบบอ่านได้
3. ถ้าถูกต้อง กด “ยืนยัน”
4. ถ้าผิด กด “แก้ไข” แล้วพิมพ์ค่า เช่น M1 12508
5. ถ้ารูปไม่ชัด กด “ถ่ายใหม่”
6. ระบบบันทึกเฉพาะค่าที่ผ่านการยืนยันแล้วเท่านั้น
```

### `latest-report-board-ai.png`

```text
หัวข้อ: วิธีดูรายงานล่าสุด

1. กดเมนู “รายงานล่าสุด”
2. ระบบค้นหารอบล่าสุดที่มีรายงาน
3. ระบบส่งรูปรายงานกลับใน LINE
4. ถ้าไม่มีรายงาน ระบบจะแนะนำให้เริ่มบันทึกมิเตอร์ก่อน
```

### `history-board-ai.png`

```text
หัวข้อ: วิธีดูประวัติ

1. กดเมนู “ประวัติ”
2. เลือก “รอบปัจจุบัน”, “สัปดาห์ก่อน”, “เลือกรอบย้อนหลัง” หรือ “ดูตามมิเตอร์”
3. ระบบแสดงสรุปจำนวนเครื่อง ยอดผลิต และยอดเงิน
4. เลือก “ดูรายละเอียด” เพื่อดูค่า M1 ถึง M8
5. เลือก “ส่งรายงาน” ถ้าต้องการรูปรายงานของรอบนั้น
```

### `settings-board-ai.png`

```text
หัวข้อ: วิธีดูการตั้งค่า

1. กดเมนู “ตั้งค่า”
2. ผู้ใช้ทั่วไปดูการตั้งค่าปัจจุบันและรายชื่อมิเตอร์ได้
3. การแก้ไขต้องใช้สิทธิ์ admin
4. ถ้าต้องการแก้ข้อมูล ให้ติดต่อผู้ดูแลระบบ
```

## Implementation Notes

- `Help` มี Quick Reply submenu แล้ว และส่งรูปได้เมื่อ configure HTTPS URLs ครบ
- mapping รูป Help อยู่ใน `app/line/messages.py` แยกจาก business logic หลัก
- URL รูปต้องเป็น HTTPS ที่ LINE เข้าถึงได้
- ถ้าใช้ GitHub public raw URL ให้ใช้เฉพาะเริ่มต้นหรือไฟล์ที่ไม่เปลี่ยนบ่อย
- มี preview image แยกจาก original image แล้วในรูปแบบ `*-board-ai-preview.jpg`
- ฟังก์ชันที่ยังเป็น partial/placeholder ไม่ควรทำภาพ Help แบบสัญญาเกินจริง

## Suggested Next Step

1. Host `docs/help-flows/*-board-ai.png` และ `docs/help-flows/*-board-ai-preview.jpg` บน HTTPS
2. ตั้งค่า `HELP_FLOW_IMAGE_BASE_URL`
3. ตั้งค่า `HELP_FLOW_IMAGE_PREVIEW_BASE_URL`
4. ทดสอบกด `Help` ใน LINE แล้วเลือกแต่ละหัวข้อ
