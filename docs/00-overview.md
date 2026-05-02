# Project Overview

## Goal

สร้าง LINE bot สำหรับบันทึกค่ามิเตอร์ Solar รายสัปดาห์จากรูปถ่าย 8 รูป แล้วคำนวณหน่วยผลิตและยอดเงิน พร้อมส่ง report กลับใน LINE

## Target Users

- เจ้าหน้าที่หน้างานที่ถ่ายรูปมิเตอร์ผ่าน LINE
- Admin หรือ owner ที่ต้องการดูยอดผลิตรายสัปดาห์
- Developer ที่ต้อง maintain backend, OCR, และ Google Sheets

## MVP Scope

MVP ต้องทำงานได้แบบ reliable มากกว่า fully automatic:

- รับข้อความและรูปผ่าน LINE webhook
- ใช้ meter id จากข้อความล่าสุดหรือ caption เช่น `M1`
- ดาวน์โหลดรูปจาก LINE content API
- ส่งรูปเข้า Google Vision OCR
- ดึงเลขมิเตอร์จาก OCR result
- ให้ผู้ใช้ยืนยันหรือแก้ไขก่อนบันทึก
- บันทึกข้อมูลลง Google Sheets
- คำนวณ `produced_unit = current_value - last_value`
- คำนวณ `amount = produced_unit * rate`
- ถ้าครบ 8 meter ใน batch เดียวกัน สร้างรูป report แล้วส่งกลับ LINE

## Non-Goals for MVP

- ไม่ให้ AI เดา meter id จากรูปเอง
- ไม่บันทึกค่า OCR อัตโนมัติโดยไม่มี confirmation
- ไม่ต้องมี web admin dashboard
- ไม่ต้องทำ multi-tenant หลายบริษัท
- ไม่ต้อง optimize OCR cost/latency แบบ production scale

## Success Criteria

- ผู้ใช้ส่งรูปหนึ่งเครื่องแล้วได้รับข้อความให้ยืนยันภายในเวลาที่เหมาะสม
- ผู้ใช้แก้ค่าผิดได้ด้วยข้อความ เช่น `M1 12508`
- Google Sheets มี row ที่ถูกต้องหลังยืนยัน
- ระบบอ่าน OCR ผ่าน Google Vision และยังให้ผู้ใช้ยืนยันก่อนบันทึกเสมอ
- เมื่อครบ 8 เครื่อง ระบบส่ง report image กลับ LINE ได้

## Core Data Concepts

- `meter`: เครื่องวัดแต่ละตัว เช่น `M1` ถึง `M8`
- `reading`: ค่าที่อ่านได้ในหนึ่งวันหรือหนึ่งรอบ
- `batch`: รอบการบันทึก เช่น weekly batch หนึ่งชุดมี 8 readings
- `pending_confirmation`: ค่า OCR ที่รอผู้ใช้ยืนยัน
- `report`: รูปสรุปผลผลิตเทียบกับรอบก่อน
