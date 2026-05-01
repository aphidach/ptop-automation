# LINE Bot Conversation Flow

## Main Happy Path

```text
User: M1
Bot: รับทราบ M1 ส่งรูปได้เลยครับ

User: [send image]
Bot: อ่านค่าได้:
     M1 = 12,500

     ยืนยันไหม?
     พิมพ์: OK
     หรือแก้เป็น: M1 12508

User: OK
Bot: บันทึกแล้วครับ
     M1: 12,500
     รอบก่อน: 12,000
     ผลิตได้: 500 units
     ยอดเงิน: 2,100.00 บาท
```

## Full Batch Flow

Expected meter ids:

```text
M1, M2, M3, M4, M5, M6, M7, M8
```

After each confirmation, bot should show progress:

```text
บันทึกแล้วครับ M3 = 9,820
ความคืบหน้า: 3/8
ยังขาด: M4, M5, M6, M7, M8
```

When complete:

```text
ครบ 8 เครื่องแล้วครับ กำลังสร้างรายงาน...
```

Then send report image.

## Manual Correction

If OCR value is wrong:

```text
User: M1 12508
Bot: บันทึกค่าแก้ไขแล้วครับ
     M1: 12,508
```

## Unknown Meter

```text
User: MX
Bot: ไม่พบ meter id "MX" ครับ
     meter ที่ใช้ได้: M1, M2, M3, M4, M5, M6, M7, M8
```

## Image Without Meter Context

```text
User: [send image]
Bot: รูปนี้เป็นของ meter ไหนครับ?
     กรุณาพิมพ์ meter id เช่น M1 แล้วส่งรูปอีกครั้ง
```

## OCR Unclear

```text
Bot: ผมอ่านเลขจากรูปนี้ไม่ชัดครับ
     กรุณาพิมพ์ค่าเอง เช่น:
     M1 12508
```

## Duplicate Reading

If `M1` already exists in the same batch:

```text
Bot: รอบนี้มีค่า M1 อยู่แล้ว:
     ค่าเดิม: 12,500
     ค่าใหม่: 12,508

     ต้องการแทนที่ไหม?
     พิมพ์: REPLACE M1
```

## Commands

| command | behavior |
| --- | --- |
| `M1` | Set current meter context |
| `OK` | Confirm latest pending OCR result |
| `M1 12508` | Manual value entry or correction |
| `STATUS` | Show current batch progress |
| `REPORT` | Generate current batch report if enough data exists |
| `CANCEL` | Cancel latest pending confirmation |
| `HELP` | Show short command help |

## Reply Message Style

Keep messages short. Field staff should not read long explanations in LINE.

Use this format for saved readings:

```text
บันทึกแล้วครับ
M1: 12,500
ผลิตได้: 500 units
ยอดเงิน: 2,100.00 บาท
ความคืบหน้า: 1/8
```

## Report Image Content

Minimum report fields:

- Report title
- Date and week
- Table: meter id, name, current, previous, produced unit, rate, amount
- Total produced unit
- Total amount
- Missing meters if any

Recommended dimensions:

```text
1200 x 1600 px
```

This size is readable in LINE and still reasonable for mobile screens.
