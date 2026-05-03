from datetime import date
from decimal import Decimal

from app.line.parser import parse_report_import_text


SAMPLE_REPORT_TEXT = """
ข้อมูลการผลิตไฟฟ้า Solar Cells On-Grid
วันที่ .....27.. /......เมษายน....../.....2569.....
ชุดที่ อ่านครั้งหลัง อ่านครั้งก่อน ผลิตได้ อัตรา/หน่วย คิดเป็นเงิน
1. (Solar 1) 11290 10550 740 4.2 3108
2. (Solar 2) 20850 20000 850 4.2 3570
3. (Solar 3) 30920 30000 920 4.2 3864
4. (Solar 4) 41000 40000 1000 4.2 4200
5. (Solar 5) 51100 50000 1100 4.2 4620
6. (Solar 6) 61300 60000 1300 4.2 5460
7. (Solar 7) 71500 70000 1500 4.2 6300
8. (Solar 8) 15246.9 13200 2046.9 3 6140.7
รวมเป็นเงิน (บาท) 37262.7
"""


def test_parse_report_import_reads_8_rows_week_and_total():
    parsed = parse_report_import_text(SAMPLE_REPORT_TEXT)

    assert parsed.success is True
    assert parsed.report_date == date(2026, 4, 27)
    assert parsed.week == "2026-W18"
    assert len(parsed.rows) == 8
    assert parsed.rows[0].meter_id == "M1"
    assert parsed.rows[-1].meter_id == "M8"
    assert parsed.total_amount == Decimal("37262.7")


def test_parse_report_import_fails_row_count_mismatch():
    parsed = parse_report_import_text(SAMPLE_REPORT_TEXT.replace(
        "8. (Solar 8) 15246.9 13200 2046.9 3 6140.7\n",
        "",
    ))

    assert parsed.success is False
    assert any("อ่านแถวได้ 7/8" in error for error in parsed.errors)
    assert any("ไม่พบแถวที่ 8" in error for error in parsed.errors)

def test_parse_report_import_fails_duplicate_and_missing_row_numbers():
    parsed = parse_report_import_text(SAMPLE_REPORT_TEXT.replace(
        "8. (Solar 8) 15246.9 13200 2046.9 3 6140.7",
        "7. (Solar 8) 15246.9 13200 2046.9 3 6140.7",
    ))

    assert parsed.success is False
    assert len(parsed.rows) == 8
    assert any("เลขแถวซ้ำ: 7" in error for error in parsed.errors)
    assert any("ไม่พบแถวที่ 8" in error for error in parsed.errors)


def test_parse_report_import_fails_produced_arithmetic_mismatch():
    parsed = parse_report_import_text(SAMPLE_REPORT_TEXT.replace(
        "1. (Solar 1) 11290 10550 740 4.2 3108",
        "1. (Solar 1) 11290 10550 741 4.2 3112.2",
    ))

    assert parsed.success is False
    assert any("ผลิตได้ไม่ตรง" in error for error in parsed.errors)


def test_parse_report_import_fails_amount_arithmetic_mismatch():
    parsed = parse_report_import_text(SAMPLE_REPORT_TEXT.replace(
        "1. (Solar 1) 11290 10550 740 4.2 3108",
        "1. (Solar 1) 11290 10550 740 4.2 3109",
    ))

    assert parsed.success is False
    assert any("ยอดเงินไม่ตรง" in error for error in parsed.errors)


def test_parse_report_import_fails_total_mismatch():
    parsed = parse_report_import_text(SAMPLE_REPORT_TEXT.replace("37262.7", "37264"))

    assert parsed.success is False
    assert any("ยอดรวมไม่ตรง" in error for error in parsed.errors)
