import hashlib
import json
from pathlib import Path

from PIL import Image

from app.line.parser import (
    POSTBACK_HELP,
    POSTBACK_HISTORY,
    POSTBACK_LATEST_REPORT,
    POSTBACK_SETTINGS,
    POSTBACK_START_COLLECTION,
    POSTBACK_WEEKLY_SUMMARY,
)
from app.line.richmenu import (
    RICHMENU_IMAGE_NAME,
    RICHMENU_MAX_IMAGE_BYTES,
    RICHMENU_SPEC_NAME,
    compose_richmenu_image,
)


def _md5_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _compose(output_dir: Path) -> tuple[Path, Path]:
    repo_root = Path(__file__).resolve().parents[1]
    return compose_richmenu_image(
        output_dir=output_dir,
        source_dir=repo_root / "Richmenu image",
    )


def test_richmenu_composition_is_deterministic_and_schema_complete(tmp_path):
    image_path, spec_path = _compose(tmp_path / "run1")
    image_hash_a = _md5_bytes(image_path)

    image_path_b, spec_path_b = _compose(tmp_path / "run2")
    image_hash_b = _md5_bytes(image_path_b)

    assert image_path.exists()
    assert spec_path.exists()
    assert image_path.name == RICHMENU_IMAGE_NAME
    assert image_path.stat().st_size <= RICHMENU_MAX_IMAGE_BYTES
    assert spec_path.name == RICHMENU_SPEC_NAME
    assert image_hash_a == image_hash_b

    with Image.open(image_path) as image:
        assert image.size == (2500, 1500)

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    assert spec["size"] == {"width": 2500, "height": 1500}
    assert len(spec["areas"]) == 6
    assert all(set(area) == {"bounds", "action"} for area in spec["areas"])

    spec2 = json.loads(spec_path_b.read_text(encoding="utf-8"))
    assert spec == spec2

    actions = [area["action"]["data"] for area in spec["areas"]]
    expected = [
        f"action={POSTBACK_START_COLLECTION}",
        f"action={POSTBACK_WEEKLY_SUMMARY}",
        f"action={POSTBACK_LATEST_REPORT}",
        f"action={POSTBACK_HISTORY}",
        f"action={POSTBACK_SETTINGS}",
        f"action={POSTBACK_HELP}",
    ]
    assert actions == expected

    first = spec["areas"][0]
    assert first["bounds"] == {"x": 0, "y": 0, "width": 1503, "height": 1127}
    assert spec["areas"][1]["bounds"] == {"x": 1530, "y": 0, "width": 465, "height": 543}
    assert spec["areas"][5]["bounds"] == {"x": 0, "y": 1170, "width": 2500, "height": 330}
