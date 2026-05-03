from PIL import Image, ImageDraw

from app.ocr.preprocess import prepare_meter_display_image


def test_prepare_meter_display_image_creates_debug_crop(tmp_path):
    image_path = tmp_path / "meter.jpg"
    image = Image.new("RGB", (600, 800), "#d8d6ca")
    draw = ImageDraw.Draw(image)
    draw.rectangle((150, 300, 470, 620), fill="#111111")
    draw.rectangle((200, 350, 420, 520), fill="#7ea6d9")
    draw.text((220, 450), "E Del 58.196 MWh", fill="#101010")
    image.save(image_path)

    result = prepare_meter_display_image(image_path, tmp_path / "debug")

    assert result.success is True
    assert result.used_crop is True
    assert result.crop_path is not None
    assert result.crop_path.exists()
    assert result.ocr_image_path == result.crop_path
    assert result.crop_size[0] >= 1000 or result.crop_size[1] >= 1000


def test_prepare_meter_display_image_falls_back_when_no_display_found(tmp_path):
    image_path = tmp_path / "wall.jpg"
    Image.new("RGB", (600, 800), "#d8d6ca").save(image_path)

    result = prepare_meter_display_image(image_path, tmp_path / "debug")

    assert result.success is False
    assert result.used_crop is False
    assert result.ocr_image_path == image_path
    assert result.crop_path is None
