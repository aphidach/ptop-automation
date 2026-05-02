# Version 2.0 LINE UX Design

## Goal

ยกระดับ MVP จาก bot ที่ผู้ใช้ต้องพิมพ์คำสั่งเอง เป็น LINE experience ที่พาผู้ใช้บันทึกมิเตอร์ทีละขั้นผ่าน Rich Menu, Flex Message, Quick Reply และ Postback action

Version 2.0 ต้องลดการพิมพ์ ลดโอกาสกดผิด และทำให้เจ้าหน้าที่หน้างานรู้เสมอว่าต้องทำอะไรต่อ

## Assumptions

- มีมิเตอร์หลัก 8 เครื่อง: `M1` ถึง `M8`
- หนึ่งรอบการบันทึกคือ weekly batch
- OCR ยังต้องให้คนยืนยันก่อนบันทึกทุกครั้ง
- Backend เดิมยังเป็นแกนหลัก: LINE webhook, OCR, Google Sheets, batch, report
- Text commands เดิม เช่น `M1`, `OK`, `STATUS`, `REPORT` ควรยังใช้ได้เป็น fallback

## UX Principles

1. ผู้ใช้ไม่ควรต้องจำคำสั่ง
2. Flow หลักควรเป็น linear: `M1 -> M8`
3. ทุกค่า OCR ต้องผ่าน confirmation ก่อนบันทึก
4. หน้าจอใน LINE ต้องสั้น อ่านเร็ว และกดต่อได้ทันที
5. Error message ต้องบอก action ถัดไป ไม่ใช่แค่บอกว่า error
6. Report ต้องดูผลรวมได้ทันที และมีทางไปดูรายละเอียด

## Main Rich Menu

Rich Menu ใช้เป็น navigation หลัก และควรมี 6 ปุ่มเท่านั้น

| Menu | Purpose | Action |
| --- | --- | --- |
| บันทึกมิเตอร์ | เริ่มบันทึกค่ามิเตอร์ 8 เครื่อง | `start_collection` |
| สรุปสัปดาห์ | ดูผลผลิตและรายได้ประจำสัปดาห์ | `weekly_summary` |
| รายงานล่าสุด | ดูหรือดาวน์โหลดรายงานล่าสุด | `latest_report` |
| ประวัติ | ดูประวัติการบันทึกย้อนหลัง | `history` |
| ตั้งค่า | ตั้งค่าเครื่องมิเตอร์และการแจ้งเตือน | `settings` |
| Help | วิธีใช้งานหรือติดต่อแอดมิน | `help` |

## Mock UI Screen Mapping

### 1. Main Menu

ผู้ใช้กด Rich Menu หรือเปิดเมนูหลัก แล้วเห็นปุ่มหลักแบบ card

Primary action:

```text
บันทึกมิเตอร์
```

Secondary actions:

```text
สรุปสัปดาห์
รายงานล่าสุด
ประวัติ
ตั้งค่า
Help
```

### 2. Start Collection

เมื่อกด `บันทึกมิเตอร์` bot ส่ง Flex Message แนะนำ flow

Content:

```text
เริ่มบันทึกค่ามิเตอร์สัปดาห์นี้

คุณต้องบันทึกทั้งหมด 8 เครื่อง
ระบบจะพาไปทีละเครื่อง M1 ถึง M8
```

Actions:

```text
เริ่มบันทึก
ดูสถานะ
ยกเลิก
```

### 3. Meter Selection

ใน mock มีปุ่มเลือก `M1` ถึง `M8` ซึ่งเหมาะสำหรับ fallback หรือ manual jump

Default v2.0 behavior ควรเป็น linear:

```text
ต่อไป: M1
กรุณาถ่ายรูปเครื่อง M1
```

Manual selection ยังควรมีไว้เมื่อ:

- ผู้ใช้ต้องแก้ไขเครื่องที่ข้ามไป
- ถ่ายซ้ำเฉพาะบางเครื่อง
- Admin ต้องบันทึกนอกลำดับ

### 4. Send Meter Photo

Bot ขอรูปเครื่องปัจจุบัน

Content:

```text
กรุณาถ่ายรูปเครื่อง M1
ให้เห็นหน้าจอมิเตอร์ชัดเจน
```

Quick replies:

```text
ข้าม
เลือกเครื่องอื่น
ดูสถานะ
ยกเลิก
```

### 5. OCR Confirmation

หลัง OCR สำเร็จ bot แสดง Flex confirmation

Content:

```text
ตรวจพบค่า

เครื่อง M1
ค่าที่อ่านได้: 12,508 kWh
ค่าครั้งก่อน: 12,000 kWh
ผลิตเพิ่ม: 508 kWh
รายได้: 2,134 บาท

ยืนยันค่าหรือไม่?
```

Actions:

```text
ยืนยัน
แก้ไข
ถ่ายใหม่
ยกเลิก
```

Rule:

```text
ห้ามบันทึกลง Google Sheets จนกว่าผู้ใช้กด ยืนยัน หรือส่งค่าแก้ไข
```

### 6. Confirmed Progress

หลังยืนยันสำเร็จ bot แสดง progress และเครื่องถัดไป

Content:

```text
บันทึกค่า M1 เรียบร้อย

ความคืบหน้า: 1/8 เครื่อง
เหลืออีก 7 เครื่อง
ต่อไป: M2
```

Actions:

```text
ถ่าย M2
ดูสถานะ
รายงานล่าสุด
```

### 7. Continue Collection

หลังบันทึกแต่ละเครื่อง bot ควรเสนอเครื่องถัดไปเป็น primary action เสมอ

Example:

```text
บันทึกค่า M2 เรียบร้อย

ความคืบหน้า: 2/8 เครื่อง
ต่อไป: M3
```

### 8. Complete Batch

เมื่อครบ 8 เครื่อง bot แจ้งว่ากำลังสร้างรายงาน

Content:

```text
บันทึกครบ 8 เครื่องแล้ว

กำลังสร้างรายงาน
กรุณารอสักครู่
```

Backend action:

```text
generate_report
```

### 9. Report Summary

หลังสร้าง report สำเร็จ bot ส่ง Flex summary และรูป report

Content:

```text
รายงานสัปดาห์ที่ 19

รวมผลิต: 4,200 kWh
รายได้รวม: 17,640 บาท
เทียบสัปดาห์ก่อน: +8%
```

Actions:

```text
ดูรายละเอียด
แชร์รายงาน
รายงานล่าสุด
```

## Collection State Machine

| State | Meaning | Expected User Action | Next State |
| --- | --- | --- | --- |
| `idle` | ยังไม่เริ่มรอบ | กดบันทึกมิเตอร์ | `collecting` |
| `collecting` | มี batch ปัจจุบันแล้ว | เลือกหรือเริ่มเครื่องถัดไป | `waiting_image` |
| `waiting_image` | รอรูปของ meter ปัจจุบัน | ส่งรูป | `processing_ocr` |
| `processing_ocr` | Backend กำลัง OCR | รอผล | `waiting_confirmation` หรือ `waiting_manual_value` |
| `waiting_confirmation` | OCR สำเร็จ รอผู้ใช้ยืนยัน | ยืนยัน, แก้ไข, ถ่ายใหม่ | `collecting` |
| `waiting_manual_value` | OCR อ่านไม่ได้หรือผู้ใช้กดแก้ไข | ส่งค่าที่ถูกต้อง | `collecting` |
| `completed` | ครบ 8 เครื่อง | รอสร้างรายงาน | `reporting` |
| `reporting` | กำลังสร้างและส่ง report | รอผล | `idle` |

## Postback Actions

| Action | Required Data | Behavior |
| --- | --- | --- |
| `start_collection` | none | สร้างหรือเปิด weekly batch ปัจจุบัน |
| `select_meter` | `meter_id` | ตั้ง meter ปัจจุบัน |
| `confirm_reading` | `meter_id`, `batch_id` | บันทึก pending confirmation |
| `edit_reading` | `meter_id`, `batch_id` | ขอให้ผู้ใช้พิมพ์ค่าเอง |
| `retake_photo` | `meter_id` | ล้าง pending แล้วรอรูปใหม่ |
| `skip_meter` | `meter_id` | mark skipped ชั่วคราว และไปเครื่องถัดไป |
| `show_status` | `batch_id` optional | แสดง progress |
| `latest_report` | none | ส่ง report ล่าสุด |
| `weekly_summary` | week optional | แสดง summary สัปดาห์ปัจจุบัน |
| `cancel_collection` | `batch_id` | ยกเลิก flow ปัจจุบัน |

## Progress UI

Progress ควรแสดงทุกครั้งหลัง save สำเร็จ

Required fields:

```text
บันทึกแล้วกี่เครื่อง
เหลือกี่เครื่อง
เครื่องถัดไปคืออะไร
รายการที่ยังขาด
```

Status categories:

| Status | Meaning |
| --- | --- |
| บันทึกแล้ว | มี confirmed reading แล้ว |
| รอการบันทึก | ยังไม่มี reading ใน batch |
| ค่าผิดปกติ | reading มี warning เช่น ค่าน้อยกว่ารอบก่อน |
| ยังไม่เริ่ม | ยังไม่มี batch หรือยังไม่เลือก meter |

## Error and Recovery UX

### OCR Unreadable

Message:

```text
อ่านเลขจากรูปนี้ไม่ชัด
กรุณาพิมพ์ค่า M1 เอง เช่น M1 12508
```

Actions:

```text
ถ่ายใหม่
กรอกเอง
ยกเลิก
```

### Value Lower Than Previous

Message:

```text
ค่าที่อ่านได้ต่ำกว่าครั้งก่อน

ครั้งก่อน: 12,000 kWh
ครั้งนี้: 11,900 kWh

กรุณาตรวจสอบก่อนบันทึก
```

Actions:

```text
ยืนยันว่าใช่
แก้ไข
ถ่ายใหม่
```

### Duplicate Meter

Message:

```text
รอบนี้มีค่า M1 แล้ว

ค่าเดิม: 12,508 kWh
ค่าใหม่: 12,520 kWh

ต้องการแทนที่หรือไม่?
```

Actions:

```text
แทนที่
ไม่แทนที่
ถ่ายใหม่
```

### Image Sent At Wrong Time

Message:

```text
ตอนนี้ระบบกำลังรอรูปของ M3
ถ้ารูปนี้เป็น M3 กดดำเนินการต่อ
ถ้าไม่ใช่ กรุณาเลือกเครื่องที่ถูกต้อง
```

Actions:

```text
ใช้เป็น M3
เลือกเครื่องอื่น
ยกเลิก
```

## Fallback Text Commands

เพื่อไม่ให้ v2.0 ทำให้ field operation ติดขัด คำสั่งเดิมควรยังใช้ได้

| Command | Behavior |
| --- | --- |
| `M1` | เลือก meter |
| `M1 12508` | กรอกหรือแก้ค่าเอง |
| `OK` | ยืนยัน pending confirmation ล่าสุด |
| `STATUS` | ดู progress |
| `REPORT` | ส่งรายงานล่าสุดหรือ report ของ batch ปัจจุบัน |
| `HELP` | ดูวิธีใช้งาน |
| `CANCEL` | ยกเลิก pending confirmation |

## V2.0 Implementation Phases

### Phase 2.0A: LINE UI Foundation

- Add Flex message builders
- Add Quick Reply builders
- Add Postback action parser
- Add Rich Menu payload/spec
- Keep text command fallback

Done when:

- Backend can reply with v2.0 start, status, confirmation, and report Flex payloads in tests

### Phase 2.0B: Guided Collection Flow

- Add explicit collection state to session
- Track current meter in batch
- Default next meter should follow `M1 -> M8`
- Show progress after every confirmed reading

Done when:

- User can start from menu and complete `M1 -> M8` without typing meter ids

### Phase 2.0C: Confirmation and Recovery

- Convert OCR confirmation to Flex
- Add actions for confirm, edit, retake
- Add warning flow for suspicious values
- Add duplicate replacement flow

Done when:

- No OCR value is saved without explicit confirmation
- User can recover from unreadable OCR without restarting the whole batch

### Phase 2.0D: Report Experience

- Add report summary Flex
- Send report image after summary
- Add latest report and weekly summary actions

Done when:

- After 8 confirmed readings, user receives a summary and report image in LINE

### Phase 2.0E: Production Readiness

- Persist session state outside memory
- Add source/user allowlist
- Add audit log for postback actions
- Add retry/report regeneration path

Done when:

- Backend restart does not lose active collection state
- Admin can diagnose failed OCR/report flows

## Acceptance Criteria

Version 2.0 is complete when:

- User can start collection from Rich Menu
- User can finish a weekly batch without typing `M1` to `M8`
- Bot always shows the current meter and progress
- OCR values are never saved without confirmation
- User can edit or retake when OCR is wrong
- Completing 8 meters automatically triggers report generation
- Report summary and report image are sent back to LINE
- Existing text commands still work as fallback

