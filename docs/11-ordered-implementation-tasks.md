# Ordered Implementation Tasks

รายการนี้เรียงตามลำดับที่ควรทำจริงสำหรับ MVP:

```text
LINE -> Python Backend -> OpenTyphoon OCR -> Google Sheets -> Report -> LINE
```

## 1. Project Setup

Goal: เตรียมโครง backend ให้รันได้

Tasks:

- สร้าง Python virtual environment
- สร้าง `requirements.txt`
- สร้างโครง folder `app/`
- สร้าง `app/main.py`
- สร้าง `app/config.py`
- เพิ่ม `.env.example`
- เพิ่ม `.gitignore`
- เพิ่ม endpoint `GET /health`

Done when:

- รัน `uvicorn app.main:app --reload --port 8000` ได้
- เปิด `GET /health` แล้วได้ `{ "status": "ok" }`

## 2. LINE Webhook Setup

Goal: รับ event จาก LINE ได้อย่างถูกต้อง

Tasks:

- ติดตั้ง `line-bot-sdk`
- เพิ่ม environment variables:
  - `LINE_CHANNEL_ACCESS_TOKEN`
  - `LINE_CHANNEL_SECRET`
- สร้าง `app/line/webhook.py`
- สร้าง endpoint `POST /webhook/line`
- ตรวจสอบ `X-Line-Signature`
- Log event type ที่ได้รับ
- ตอบ HTTP 200 ให้ LINE เสมอเมื่อ signature ถูกต้อง

Done when:

- LINE webhook verify ผ่าน
- Backend รับ text/image event ได้

## 3. Text Command Handling

Goal: ให้ผู้ใช้บอก meter id ได้ เช่น `M1`

Tasks:

- สร้าง `app/line/parser.py`
- Parse command:
  - `M1`
  - `OK`
  - `M1 12508`
  - `STATUS`
  - `HELP`
  - `CANCEL`
- Validate meter id จาก config หรือ Google Sheet mock
- เก็บ latest meter id ต่อ LINE source/user
- Reply กลับ LINE เมื่อผู้ใช้พิมพ์ meter id

Done when:

- ผู้ใช้พิมพ์ `M1`
- Bot ตอบว่า `รับทราบ M1 ส่งรูปได้เลยครับ`

## 4. Session Storage

Goal: เก็บสถานะ conversation ระหว่างรอรูปและรอยืนยัน

Tasks:

- สร้าง `app/services/session_service.py`
- เก็บข้อมูล:
  - `line_source_id`
  - `line_user_id`
  - `latest_meter_id`
  - `pending_confirmation`
  - `batch_id`
- MVP ใช้ in-memory dict ได้ก่อน
- ออกแบบให้เปลี่ยนเป็น Redis/SQLite ได้ภายหลัง

Done when:

- พิมพ์ `M1` แล้วส่งรูปทีหลัง ระบบยังรู้ว่ารูปคือ `M1`

## 5. LINE Image Download

Goal: ดาวน์โหลดรูปจาก LINE message id ได้

Tasks:

- สร้าง `app/line/client.py`
- Implement download image by `message_id`
- Save image ลง `tmp/images/`
- ตั้งชื่อไฟล์ด้วย `message_id`
- Validate file type/size เบื้องต้น
- Reply error ถ้าดาวน์โหลดไม่ได้

Done when:

- ผู้ใช้ส่งรูปใน LINE
- Backend ดาวน์โหลดรูปลงเครื่องได้

## 6. OpenTyphoon OCR Client

Goal: อ่านข้อความจากรูปด้วย OpenTyphoon OCR

Tasks:

- ติดตั้ง `typhoon-ocr`
- เพิ่ม environment variable `TYPHOON_OCR_API_KEY`
- สร้าง `app/ocr/opentyphoon.py`
- Implement `read_image(image_path)`
- Return:
  - `raw_text`
  - `model`
  - `duration_ms`
  - `error`
- Log OCR request/response แบบไม่เก็บ secret

Done when:

- ส่ง local image เข้า OCR แล้วได้ raw text กลับมา

## 7. OCR Rate Limiter

Goal: ไม่ยิง OpenTyphoon เกิน limit 2 req/s และ 20 req/min

Tasks:

- สร้าง `app/ocr/rate_limiter.py`
- Implement queue หรือ async limiter
- จำกัด burst ไม่เกิน 2 requests/second
- จำกัด sustained traffic ไม่เกิน 20 requests/minute
- Retry เมื่อเจอ 429 ด้วย exponential backoff
- Log retry count

Done when:

- ส่งรูป 8 รูปติดกันแล้ว OCR ถูกทยอยทำงาน
- ไม่มี request burst เกิน limit

## 8. Meter Value Parser

Goal: แปลง OCR raw text เป็นเลขมิเตอร์

Tasks:

- สร้าง `app/ocr/value_parser.py`
- Extract numeric candidates เช่น:
  - `12,500`
  - `12500`
  - `012500`
- Normalize comma/space
- เลือกค่าที่น่าจะเป็นเลขมิเตอร์ที่สุด
- Return `None` ถ้าอ่านไม่ได้
- เขียน unit tests สำหรับ parser

Done when:

- Raw OCR text ถูกแปลงเป็น `int` ได้
- ถ้าอ่านไม่ได้ ระบบบอกให้ user พิมพ์เอง

## 9. Confirmation Flow

Goal: ให้คนยืนยันก่อนบันทึกทุกครั้ง

Tasks:

- สร้าง `app/services/confirmation_service.py`
- เมื่อ OCR สำเร็จ ให้สร้าง pending confirmation
- Reply:
  - meter id
  - OCR value
  - วิธี confirm `OK`
  - วิธีแก้ `M1 12508`
- รองรับ `OK`
- รองรับ manual correction
- รองรับ `CANCEL`
- Expire pending confirmation หลังเวลาที่กำหนด

Done when:

- OCR อ่านค่าได้ แต่ยังไม่บันทึกทันที
- บันทึกเฉพาะหลัง user พิมพ์ `OK` หรือแก้ค่าเอง

## 10. Google Sheets Setup

Goal: เตรียม spreadsheet เป็น database ของ MVP

Tasks:

- สร้าง Google Cloud project
- Enable Google Sheets API
- สร้าง service account
- ดาวน์โหลด credential JSON
- สร้าง spreadsheet tabs:
  - `meters`
  - `readings`
  - `batches`
  - `settings`
  - `audit_log`
- Share sheet ให้ service account
- เพิ่ม `GOOGLE_APPLICATION_CREDENTIALS`
- เพิ่ม `GOOGLE_SHEETS_SPREADSHEET_ID`

Done when:

- Backend อ่าน tab `meters` ได้

## 11. Google Sheets Client

Goal: อ่าน/เขียนข้อมูลลง Google Sheets

Tasks:

- ติดตั้ง `gspread` และ `google-auth`
- สร้าง `app/sheets/client.py`
- สร้าง `app/sheets/repositories.py`
- Implement:
  - get active meters
  - get meter by id
  - get latest reading by meter id
  - append reading
  - get readings by batch id
  - update batch status

Done when:

- Backend append confirmed reading ลง `readings` ได้

## 12. Reading Calculation

Goal: คำนวณหน่วยผลิตและยอดเงิน

Tasks:

- สร้าง `app/services/meter_service.py`
- คำนวณ:
  - `last_value`
  - `produced_unit`
  - `rate`
  - `amount`
- Validate:
  - current value ต้องเป็นตัวเลข
  - current value ไม่ควรน้อยกว่า last value
  - duplicate meter ใน batch ต้องถามก่อน replace

Done when:

- บันทึก reading แล้วมีค่า `produced_unit` และ `amount` ถูกต้อง

## 13. Batch Management

Goal: รวม readings เป็นรอบรายสัปดาห์

Tasks:

- สร้าง `app/services/batch_service.py`
- Generate `batch_id` จาก ISO week และ LINE source
- Track expected meter count = 8
- Track confirmed meter count
- หา missing meters
- Reply progress หลังบันทึกแต่ละเครื่อง

Done when:

- Bot บอกได้ว่าเก็บแล้วกี่เครื่อง เช่น `3/8`
- Bot บอก missing meters ได้

## 14. Report Image Generator

Goal: สร้างรูป report หลังครบ 8 เครื่อง

Tasks:

- ติดตั้ง `pandas`, `matplotlib`, `pillow`
- สร้าง `app/report/generator.py`
- Generate report image ขนาดประมาณ `1200x1600`
- แสดง:
  - title
  - date/week
  - meter id/name
  - current value
  - last value
  - produced unit
  - rate
  - amount
  - total produced unit
  - total amount
- Save ลง `reports/`

Done when:

- สร้างไฟล์ PNG report จาก batch ได้

## 15. Send Report Back to LINE

Goal: ส่งรูป report กลับใน LINE

Tasks:

- ตัดสินใจวิธี host รูป:
  - MVP: static endpoint จาก backend
  - Production: Google Cloud Storage
- สร้าง public URL ของ report image
- ส่ง image message ผ่าน LINE
- Update batch status เป็น `reported`

Done when:

- หลังครบ 8 เครื่อง ผู้ใช้ได้รับรูป report ใน LINE

## 16. Status and Help Commands

Goal: ให้ผู้ใช้ตรวจสอบสถานะได้เอง

Tasks:

- Implement `STATUS`
- Implement `HELP`
- Implement `REPORT`
- Implement `CANCEL`
- ทำข้อความตอบกลับให้สั้นและอ่านง่าย

Done when:

- ผู้ใช้พิมพ์ `STATUS` แล้วเห็น progress ปัจจุบัน

## 17. Error Handling and Logging

Goal: ทำให้ debug ง่ายและไม่เสียข้อมูล

Tasks:

- สร้าง `app/services/audit_service.py`
- Log event สำคัญลง `audit_log`
- Handle errors:
  - LINE download failed
  - OCR failed
  - OCR unreadable
  - Google Sheets write failed
  - duplicate reading
  - invalid meter id
- Reply user ด้วยข้อความที่แก้ปัญหาได้

Done when:

- Error สำคัญมี log
- User ได้ข้อความชัดเจนว่าต้องทำอะไรต่อ

## 18. Deployment

Goal: เอาระบบขึ้น public URL ให้ LINE เรียกได้

Tasks:

- เลือก platform:
  - Google Cloud Run
  - Render
  - Railway
  - VPS
- ตั้ง environment variables
- ตั้ง webhook URL ใน LINE Console
- ตั้ง health check
- ตรวจสอบ log
- ทดสอบ full flow บน production URL

Done when:

- LINE webhook ยิงเข้า production backend ได้
- ส่งรูปจริงแล้วบันทึกลง Google Sheets ได้

## 19. End-to-End Testing

Goal: ทดสอบ flow ตั้งแต่ LINE ถึง report

Tasks:

- เตรียม meter `M1` ถึง `M8`
- ส่งรูปครบ 8 รูป
- ยืนยันค่า 8 ครั้ง
- ตรวจสอบ Google Sheets
- ตรวจสอบ report image
- ตรวจสอบ LINE ได้รับ report
- ทดสอบ OCR อ่านผิดและ manual correction
- ทดสอบ duplicate meter

Done when:

- MVP ใช้งาน field test ได้ครบหนึ่งรอบ

## 20. Production Hardening

Goal: ทำให้พร้อมใช้งานจริงมากขึ้น

Tasks:

- เปลี่ยน in-memory session เป็น Redis หรือ SQLite
- Add allowlist LINE user/group
- Add dead-letter queue สำหรับ OCR job ที่ fail
- Add backup/export Google Sheets
- Add monitoring/alert
- Add admin command สำหรับ regenerate report
- Add replace flow สำหรับ duplicate reading

Done when:

- ระบบ restart แล้ว state สำคัญไม่หาย
- ใช้งานรายสัปดาห์ได้เสถียร

## Recommended Build Order Summary

1. Project setup
2. LINE webhook
3. Text command handling
4. Session storage
5. Image download
6. OpenTyphoon OCR client
7. OCR rate limiter
8. Meter value parser
9. Confirmation flow
10. Google Sheets setup
11. Google Sheets client
12. Reading calculation
13. Batch management
14. Report image generator
15. Send report to LINE
16. Status/help commands
17. Error handling/logging
18. Deployment
19. End-to-end testing
20. Production hardening
