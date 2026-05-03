import asyncio
from decimal import Decimal

from app.ocr.opentyphoon import OcrResult
from scripts import evaluate_ocr


def test_parse_engines_accepts_google_and_comparison_list():
    assert evaluate_ocr.parse_engines("") == [evaluate_ocr.ENGINE_GOOGLE]
    assert evaluate_ocr.parse_engines("google") == [evaluate_ocr.ENGINE_GOOGLE]
    assert evaluate_ocr.parse_engines("opentyphoon,google") == [
        evaluate_ocr.ENGINE_OPENTYPHOON,
        evaluate_ocr.ENGINE_GOOGLE,
    ]
    assert evaluate_ocr.ENGINE_GOOGLE in evaluate_ocr.parse_engines("all")


def test_evaluate_images_runs_google_through_shared_parser(monkeypatch, tmp_path):
    class FakeGoogleVisionOcrClient:
        def read_image(self, image_path):
            return OcrResult(
                raw_text="E Del 58.196 MWh",
                model="google-vision-document-text-detection",
                duration_ms=12,
            )

    monkeypatch.setattr(
        evaluate_ocr,
        "GoogleVisionOcrClient",
        FakeGoogleVisionOcrClient,
    )
    image_path = tmp_path / "1.jpg"
    image_path.write_bytes(b"image-bytes")

    rows = asyncio.run(
        evaluate_ocr.evaluate_images(
            images=[image_path],
            labels={
                "1.jpg": evaluate_ocr.ExpectedReading(
                    value=Decimal("58196"),
                    meter_id="M1",
                )
            },
            engines=[evaluate_ocr.ENGINE_GOOGLE],
            preprocess_enabled=False,
            use_crop_for_ocr=False,
            debug_dir=tmp_path / "debug",
        )
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.engine == evaluate_ocr.ENGINE_GOOGLE
    assert row.raw_text == "E Del 58.196 MWh"
    assert row.parsed_value == Decimal("58196")
    assert row.correct is True
    assert row.confidence_level == "high"
    assert row.duration_ms == 12
    assert row.error is None
