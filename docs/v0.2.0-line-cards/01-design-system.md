# LINE Card Design System

## Theme

แนวทางหลักคือ Eco-Tech Clean Energy สำหรับระบบ solar meter ที่ใช้งานจริงใน LINE chat ต้องดูสะอาด อ่านเร็ว กดง่าย และน่าเชื่อถือ โดยใช้สีเขียวเป็น brand identity หลัก

## Color Tokens

| Token | Hex | Use |
| --- | --- | --- |
| Primary Green | `#4CAF50` | primary CTA, success action, active state |
| Dark Green | `#2E7D32` | title, section header, emphasis |
| Light Green | `#E8F5E9` | card highlight, soft background, success panel |
| Energy Yellow | `#FFC107` | warning, energy highlight, attention badge |
| Data Blue | `#64B5F6` | reports, charts, analytics, informational action |
| Neutral Gray | `#9E9E9E` | secondary text, settings, disabled state |
| Page Background | `#F5F7F5` | design board and soft chat background |
| White | `#FFFFFF` | card surface |

Use gradient `#66BB6A -> #2E7D32` only for key sections such as start collection hero, completion state, or large primary card area. Do not use the gradient on every card.

## Typography

- ใช้ sans-serif ที่อ่านภาษาไทยชัด เช่น LINE default/system sans-serif
- หัวข้อ card ใช้ขนาดใกล้ `lg` หรือ `xl`
- metric สำคัญ เช่น `12,508 kWh` ใช้ `xxl` เฉพาะใน card ที่มีข้อมูลหลักเดียว
- body text ต้องสั้น ไม่เกิน 2-4 บรรทัดต่อ section
- button label ต้องสั้นมาก เพราะ LINE quick reply label มี limit ในโค้ดที่ `20` characters
- หลีกเลี่ยง paragraph ยาวใน Flex Message ให้ย้ายคำอธิบายยาวไป Help Flow image แทน

## Card Anatomy

ทุก card ควรประกอบจากส่วนมาตรฐานเหล่านี้:

| Area | Purpose | Rule |
| --- | --- | --- |
| Header | ชื่อ card และ context เช่น week/meter | ใช้ dark green, short title |
| Status badge | role, warning, progress, success | ใช้สีตาม state |
| Body | metric, short explanation, status list | scan ได้ใน 3-5 วินาที |
| Visual cue | icon, mini chart, meter grid | ใช้เพื่อช่วยจำ ไม่ใช้ตกแต่งเกินจำเป็น |
| Footer actions | primary and secondary actions | primary ไม่เกิน 1 ปุ่มต่อ card |
| Quick replies | navigation หรือ fallback action | ใช้กับตัวเลือกหลายทาง เช่น M1-M8 |

## Action Hierarchy

| Action type | Style | Examples |
| --- | --- | --- |
| Primary | green filled button | `เริ่มบันทึก`, `ยืนยัน`, `บันทึกต่อ` |
| Secondary | white or outline button | `ดูสถานะ`, `กลับประวัติ`, `กลับตั้งค่า` |
| Informational | blue accent | `ดูรายละเอียด`, `รายงานล่าสุด` |
| Warning | yellow panel or badge | `ตรวจสอบก่อนบันทึก`, `ค่าต่ำกว่าครั้งก่อน` |
| Destructive/cancel | gray text or outline | `ยกเลิก`, `ถ่ายใหม่` |

ถ้า card มี action เกิน 3 ปุ่ม ให้ใช้ primary button 1 ปุ่ม และย้ายตัวเลือกที่เหลือไป Quick Reply หรือ compact secondary rows

## Icon Rules

ใช้ icon แบบ flat-modern หรือ soft 3D ขนาดเล็กเท่านั้น:

- solar panel สำหรับ brand/start/help
- camera สำหรับรอถ่ายรูปหรือ retake
- check circle สำหรับ success/confirmed
- clock สำหรับ waiting/pending
- alert triangle สำหรับ warning
- bar chart สำหรับ report/analytics
- gear สำหรับ settings
- lock สำหรับ admin-only
- upload/photo สำหรับ import report

ไม่ควรใช้ icon ที่ไม่มีหน้าที่ และไม่ควรให้ mascot หรือ illustration แย่งความสำคัญจาก data/action

## Layout Rules for LINE

- card width ต้องรองรับ mobile LINE เป็นหลัก
- ใช้ corner radius นุ่ม แต่ไม่กลมจนเป็น playful app เกินไป
- ใช้ subtle shadow เฉพาะ surface หลัก
- meter grid M1-M8 ต้องมี stable dimensions เพื่อไม่ shift เมื่อ status เปลี่ยน
- table ใน LINE ต้อง compact มาก ถ้าข้อมูลยาวให้ส่ง report image แทน
- alt text ของ Flex Message ต้องอธิบาย action สำคัญได้ เช่น `ยืนยันค่ามิเตอร์ M2`
- card ต้องมี fallback action เสมอ เช่น `Help`, `ดูสถานะ`, `กลับเมนูหลัก`

## Status Language

ใช้คำสั้นและ consistent:

| State | Thai label | Color |
| --- | --- | --- |
| confirmed | `บันทึกแล้ว` | Primary Green |
| waiting | `รอบันทึก` | Energy Yellow |
| warning | `ตรวจสอบ` | Energy Yellow |
| missing | `ยังไม่มีข้อมูล` | Neutral Gray |
| processing | `กำลังทำงาน` | Data Blue |
| admin only | `Admin` | Dark Green |

## Copy Tone

- สุภาพ สั้น และตรง action
- หลีกเลี่ยงคำอธิบายเชิงเทคนิคใน card หลัก
- ใช้คำว่า `ครับ` ในข้อความสนทนาได้ แต่ button label ไม่ต้องใส่
- Error ต้องบอกทางออก เช่น `พิมพ์ M2 12508` หรือ `ถ่ายใหม่`

## Visual QA Checklist

- Text ไม่ล้น card หรือ button
- Primary action เห็นทันที
- สี warning ไม่ดูเหมือน success
- ข้อมูล kWh และบาทมี hierarchy ชัด
- มีทางกลับหรือแก้ไขในทุก flow สำคัญ
- ภาพ report/help ต้องใช้ HTTPS URL เมื่อส่งจริงใน LINE
