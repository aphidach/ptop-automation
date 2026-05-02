from types import SimpleNamespace

from app.ocr.google_vision import GoogleVisionOcrClient


class FakeVisionClient:
    def __init__(self, response):
        self.response = response
        self.image = None

    def document_text_detection(self, image):
        self.image = image
        return self.response


def test_google_vision_reads_full_text_annotation(tmp_path, monkeypatch):
    image_path = tmp_path / "meter.jpg"
    image_path.write_bytes(b"image-bytes")
    response = SimpleNamespace(
        error=SimpleNamespace(message=""),
        full_text_annotation=SimpleNamespace(text="E Del 58.196 MWh"),
    )
    fake_client = FakeVisionClient(response)
    client = GoogleVisionOcrClient(client=fake_client)
    monkeypatch.setattr(client, "_make_image", lambda content: {"content": content})

    result = client.read_image(str(image_path))

    assert result.success is True
    assert result.raw_text == "E Del 58.196 MWh"
    assert result.model == "google-vision-document-text-detection"
    assert fake_client.image == {"content": b"image-bytes"}


def test_google_vision_response_error_returns_ocr_error(tmp_path, monkeypatch):
    image_path = tmp_path / "meter.jpg"
    image_path.write_bytes(b"image-bytes")
    response = SimpleNamespace(
        error=SimpleNamespace(message="quota exceeded"),
        full_text_annotation=SimpleNamespace(text="ignored"),
    )
    client = GoogleVisionOcrClient(client=FakeVisionClient(response))
    monkeypatch.setattr(client, "_make_image", lambda content: {"content": content})

    result = client.read_image(str(image_path))

    assert result.success is False
    assert result.error == "Google Vision error: quota exceeded"


def test_google_vision_appends_mpr45s_detail_crop(tmp_path, monkeypatch):
    image_path = tmp_path / "meter.jpg"
    image_path.write_bytes(b"image-bytes")
    responses = [
        SimpleNamespace(
            error=SimpleNamespace(message=""),
            full_text_annotation=SimpleNamespace(text="ENTES\nMPR-45S\n0250509 kWh"),
        ),
        SimpleNamespace(
            error=SimpleNamespace(message=""),
            full_text_annotation=SimpleNamespace(text="0250509. IkW h"),
        ),
    ]
    fake_client = FakeVisionClient(responses[0])

    def document_text_detection(image):
        return responses.pop(0)

    fake_client.document_text_detection = document_text_detection
    client = GoogleVisionOcrClient(client=fake_client)
    monkeypatch.setattr(client, "_make_image", lambda content: {"content": content})
    monkeypatch.setattr(
        "app.ocr.google_vision._make_mpr45s_detail_crop",
        lambda path: b"crop-bytes",
    )

    result = client.read_image(str(image_path))

    assert result.success is True
    assert "MPR-45S" in result.raw_text
    assert "[google_vision_mpr45s_detail]" in result.raw_text
    assert "0250509. IkW h" in result.raw_text
