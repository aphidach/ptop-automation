from app.line.parser import (
    GEN,
    POSTBACK_UNKNOWN,
    POSTBACK_CONFIRM_READING,
    POSTBACK_FORCE_CONFIRM_READING,
    POSTBACK_HELP_FLOW,
    POSTBACK_HISTORY,
    POSTBACK_LATEST_REPORT,
    POSTBACK_SELECT_METER,
    POSTBACK_START_COLLECTION,
    REPORT,
    parse_command,
    parse_postback_action,
)


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


def test_parse_postback_query_string():
    parsed = parse_postback_action("action=start_collection")
    assert parsed.type == POSTBACK_START_COLLECTION
    assert parsed.raw == "action=start_collection"


def test_parse_postback_query_with_meter_and_week():
    parsed = parse_postback_action("action=select_meter&meter_id=m1&batch_id=2026-W19")
    assert parsed.type == POSTBACK_SELECT_METER
    assert parsed.meter_id == "M1"
    assert parsed.batch_id == "2026-W19"


def test_parse_postback_json_payload():
    parsed = parse_postback_action('{"action":"latest_report","batch_id":"2026-W20"}')
    assert parsed.type == POSTBACK_LATEST_REPORT
    assert parsed.batch_id == "2026-W20"


def test_parse_postback_colon_payload():
    parsed = parse_postback_action("history:M3")
    assert parsed.type == POSTBACK_HISTORY


def test_parse_postback_confirm_with_replace_flag():
    parsed = parse_postback_action("action=confirm_reading&replace=true")
    assert parsed.type == POSTBACK_CONFIRM_READING
    assert parsed.replace is True


def test_parse_settings_confirm_change_id():
    parsed = parse_postback_action("action=settings_confirm_change&change_id=chg_123")
    assert parsed.type == "settings_confirm_change"
    assert parsed.change_id == "chg_123"


def test_parse_force_confirm_postback():
    parsed = parse_postback_action("action=force_confirm_reading")
    assert parsed.type == POSTBACK_FORCE_CONFIRM_READING


def test_parse_help_flow_topic_postback():
    parsed = parse_postback_action("action=help_flow&topic=start_collection")

    assert parsed.type == POSTBACK_HELP_FLOW
    assert parsed.topic == "start_collection"


def test_parse_postback_unknown_payload():
    parsed = parse_postback_action("unknown_action")
    assert parsed.type == POSTBACK_UNKNOWN
