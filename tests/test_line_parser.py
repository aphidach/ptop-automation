from app.line.parser import GEN, parse_command


def test_parse_gen_command():
    cmd = parse_command("GEN")

    assert cmd.type == GEN
    assert cmd.raw == "GEN"


def test_parse_gen_command_case_insensitive():
    cmd = parse_command("gen")

    assert cmd.type == GEN
    assert cmd.raw == "gen"
