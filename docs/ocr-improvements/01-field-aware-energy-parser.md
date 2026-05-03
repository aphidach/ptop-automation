# Implement 01: Field-Aware Energy Parser

## Goal

Replace the current generic number picker with a parser that explicitly extracts meter energy readings from labels such as `E Del`, `Energy Delivered`, `Total Energy`, and `Total Energy kWh`.

## Why This Comes First

The latest report shows the OCR output often contains the correct energy value. The failure is mostly semantic parsing:

- `1.jpg`: OCR includes `E Del 58.196 MWh`, but parser returns `2791` from `Ptot 20.2791 kW`
- `2.jpg`: OCR includes `E Del 60.601 MWh`, but parser returns `216853` from `Ptot`
- `8.jpg`: OCR includes `E Del 84.352 MWh`, but parser returns `2626` from `P tot 11.2626`

## Scope

Add a new parser function without removing the old parser yet:

```python
def parse_energy_meter_value(raw_text: str) -> ParseResult:
    ...
```

Recommended location:

- `app/ocr/value_parser.py`

## Parsing Rules

Priority order:

1. `Total Energy kWh`
2. `Total Energy`
3. `Total Energy Consumed`
4. `Energy Delivered`
5. `E Del`
6. Existing fallback parser

Unit handling:

- `kWh`: keep value as-is
- `MWh`: multiply by `1000`
- missing unit: keep value, but mark lower confidence later

Important: `Ptot`, `P tot`, `kW`, `Vavg`, `Iavg`, dates, and model numbers must not win over energy labels.

## Implementation Notes

The OCR output may be Markdown, HTML table text, bullet text, or plain lines. The first implementation can use targeted regex patterns because the known failure cases are narrow.

Examples to support:

```text
E Del 58.196 MWh
<td>E Del</td><td>60.601</td><td>MWh</td>
Energy Delivered 61270 MWh
Comm Frequency Hz Total Energy kWh
50.0 135420.05
Total Energy Consumed: 250509 kWh
```

For HTML tables, a lightweight approach is acceptable first: normalize tags into spaces before applying field patterns. If this becomes brittle, switch to a structured parser.

## Tests

Add tests in:

- `tests/test_value_parser.py`

Required test cases:

- `E Del 58.196 MWh` -> `58196`
- `E Del 84.352 MWh` -> `84352`
- `Total Energy kWh 135420.05` -> `135420.05`
- `Total Energy Consumed: 250509 kWh` -> `250509`
- `Ptot 20.2791 kW\nE Del 58.196 MWh` -> `58196`
- fallback still supports plain manual value like `M1 12508`

## Verification

Run:

```bash
rtk uv run pytest tests/test_value_parser.py
rtk make ocr-test
```

Success criteria:

- Unit tests pass
- New OCR report reaches at least 6/8 exact accuracy on current `tmp/test-ocr`
- Failure rows show understandable reasons for remaining misses
