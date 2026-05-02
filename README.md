# Solar Meter LINE Bot Documentation

เอกสารชุดนี้เป็น technical spec สำหรับระบบ:

```text
LINE -> Python Backend -> OpenTyphoon OCR -> Google Sheets -> Report image -> LINE
```

## Documents

- [Ordered Implementation Tasks](TASKS.md)
- [Project Overview](docs/00-overview.md)
- [System Architecture](docs/01-architecture.md)
- [Google Sheets Schema](docs/02-google-sheets-schema.md)
- [Backend API Spec](docs/03-backend-api.md)
- [OCR Model: OpenTyphoon](docs/04-ocr-opentyphoon.md)
- [LINE Bot Conversation Flow](docs/05-line-bot-flow.md)
- [Environment and Deployment](docs/06-env-and-deployment.md)
- [MVP Roadmap](docs/07-roadmap.md)
- [Version 2.0 LINE UX Design](docs/08-v2-line-ux-design.md)

## Recommended MVP

เริ่มจาก flow ที่ให้คนยืนยันก่อนบันทึก:

1. ผู้ใช้พิมพ์ `M1`
2. ผู้ใช้ส่งรูปมิเตอร์
3. Backend ดาวน์โหลดรูปจาก LINE
4. OpenTyphoon OCR อ่านตัวเลข
5. Bot ตอบกลับให้ยืนยัน เช่น `อ่านได้ M1 = 12500 พิมพ์ OK หรือแก้เป็น M1 12508`
6. เมื่อยืนยันแล้ว append ลง Google Sheets
7. เมื่อครบ 8 เครื่องใน batch เดียวกัน สร้าง report image แล้วส่งกลับ LINE

## Main External References

- LINE Messaging API: https://developers.line.biz/en/docs/messaging-api/
- Google Sheets API Python quickstart: https://developers.google.com/workspace/sheets/api/quickstart/python
- OpenTyphoon OCR docs: https://docs.opentyphoon.ai/en/ocr/
- OpenTyphoon rate limits: https://docs.opentyphoon.ai/en/rate-limits/
# ptop-automation
