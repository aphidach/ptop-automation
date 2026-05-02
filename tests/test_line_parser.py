from app.line.parser import GEN, REPORT, parse_command


def test_parse_gen_command():
    cmd = parse_command("GEN")

    assert cmd.type == GEN
    assert cmd.raw == "GEN"


def test_parse_gen_command_case_insensitive():
    cmd = parse_command("gen")

    assert cmd.type == GEN
    assert cmd.raw == "gen"

def test_parse_gen_command_with_week_ref():
    cmd = parse_command("Gen 2026-w18")

    assert cmd.type == GEN
    assert cmd.batch_id == "2026-w18"
    assert cmd.raw == "Gen 2026-w18"

def test_parse_gen_command_with_batch_id():
    cmd = parse_command("GEN 2026-W18-U08585bd3f4116f311ae320cab4e9e1b6")

    assert cmd.type == GEN
    assert cmd.batch_id == "2026-W18-U08585bd3f4116f311ae320cab4e9e1b6"

def test_parse_report_command():
    cmd = parse_command("REPORT")

    assert cmd.type == REPORT
    assert cmd.raw == "REPORT"

def test_parse_report_command_case_insensitive():
    cmd = parse_command("report")

    assert cmd.type == REPORT
    assert cmd.raw == "report"

def test_parse_report_command_with_batch_id():
    cmd = parse_command("REPORT 2026-W18-U08585bd3f4116f311ae320cab4e9e1b6")

    assert cmd.type == REPORT
    assert cmd.batch_id == "2026-W18-U08585bd3f4116f311ae320cab4e9e1b6"
    assert cmd.raw == "REPORT 2026-W18-U08585bd3f4116f311ae320cab4e9e1b6"

def test_parse_report_command_with_batch_id_preserves_case():
    cmd = parse_command("Report 2026-W18-UabcDef")

    assert cmd.type == REPORT
    assert cmd.batch_id == "2026-W18-UabcDef"
