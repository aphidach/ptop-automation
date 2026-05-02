# Implement 04: ROI Display Preprocessing

## Goal

Crop and enhance the meter display area before OCR so the model sees less irrelevant text and fewer distracting numbers.

## Research Basis

AMR research commonly separates display/counter localization from recognition:

- Copel-AMR labels the counter corners so the counter region can be rectified before recognition.
- The Dryad 2026 water meter dataset separates detection/segmentation images from recognition crops.
- PaddleOCR includes optional orientation and unwarping modules before text detection and recognition.

## Why It Helps This Project

The full LINE photo includes:

- buttons and indicator lights
- wall/panel background
- model labels
- handwritten meter index
- safety stickers
- multiple non-energy values on screen

OpenTyphoon can read the whole image, but the parser then has to fight extra text. Cropping to the display region reduces that burden.

## First Implementation

Start with deterministic preprocessing, not model training:

1. Detect likely display rectangle using image processing.
2. Crop display with padding.
3. Upscale crop.
4. Improve contrast.
5. Save debug crop next to each OCR report or in `tmp/ocr-debug/`.
6. Send crop to OCR instead of full image.

Possible file:

- `app/ocr/preprocess.py`

Suggested API:

```python
def prepare_meter_display_image(image_path: str) -> PreprocessResult:
    ...
```

## Debug Output

For every evaluated image, report:

- original image path
- crop image path
- crop dimensions
- whether preprocessing succeeded
- whether OCR used crop or full image fallback

## Fallback Rule

If no confident display crop is found, use the original image. Do not fail the OCR run just because preprocessing fails.

## Later Upgrade

If deterministic crop is not reliable, train or use a lightweight detector:

- display bounding box detector
- screen/counter corner detector
- semantic segmentation model for display area

This matches the direction used by AMR research but should wait until the parser fix is measured.

## Verification

Run:

```bash
rtk make ocr-test
```

Success criteria:

- Debug crops are visible and useful
- OCR report shows whether each image used crop or full image
- Accuracy improves or at least raw OCR becomes cleaner around energy rows
