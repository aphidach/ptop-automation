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
