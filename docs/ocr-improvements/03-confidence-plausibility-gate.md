# Implement 03: Confidence and Plausibility Gate

## Goal

Prevent obviously risky OCR readings from being treated like normal readings. Low-confidence values should still be shown to the user, but the UI should encourage manual review or retake.

## Why This Is Needed

Even after field-aware parsing, some cases remain ambiguous:

- OCR may read `61.270 MWh` as `612.70 MWh`
- Decimal points may disappear
- `MWh` and `kWh` may be confused
- The energy field may be missing and fallback logic may choose a wrong number

The current LINE flow asks for confirmation, which is good. This implement makes the confirmation smarter.

## Proposed Confidence Levels

High confidence:

- Energy label matched
- Unit found
- Value is within plausible range compared with last reading
- No conflicting nearby energy candidates

Medium confidence:

- Energy label matched
- Unit missing or OCR text is messy
- Value is still plausible

Low confidence:

- Fallback parser used
- Value is lower than previous reading
- Value jumps far beyond expected production
- Multiple energy candidates conflict
- OCR text contains table corruption around the selected value

## Plausibility Checks

Use existing meter history:

- current value should usually be greater than or equal to last value
- produced unit should be within a configurable weekly/monthly range
- decimal/unit conversion should not produce an impossible jump

Suggested function:

```python
def score_ocr_reading(
    meter_id: str,
    parsed_value: Decimal,
    parse_reason: str,
    raw_text: str,
) -> ConfidenceResult:
    ...
```

Possible location:

- `app/services/meter_service.py`
- or `app/ocr/confidence.py` if the logic stays OCR-specific

## LINE Behavior

High confidence:

- show normal confirmation card

Medium confidence:

- show confirmation card with a caution line

Low confidence:

- ask user to type the value manually or retake photo
- do not make `OK` feel like the default safest path

## Tests

Add tests for:

- value lower than last reading -> warning
- huge jump from last reading -> low confidence
- field-aware parse with unit -> high confidence
- fallback generic parse -> low confidence

## Verification

Run:

```bash
rtk uv run pytest tests/test_meter_service.py tests/test_value_parser.py
rtk make ocr-test
```

Success criteria:

- Correct values still pass through
- Ambiguous values are not silently treated as normal
- Report includes confidence and reason fields
