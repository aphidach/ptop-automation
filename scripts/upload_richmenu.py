from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from pathlib import Path
from typing import Any

import httpx
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.config import settings
from app.line.richmenu import RICHMENU_MAX_IMAGE_BYTES, compose_richmenu_image

API_BASE_URL = "https://api.line.me/v2/bot"
DATA_BASE_URL = "https://api-data.line.me/v2/bot"


def main() -> None:
    args = _parse_args()
    image_path, spec_path = _resolve_assets(args)
    spec = _load_json(spec_path)

    _validate_local_assets(image_path, spec)
    print(f"image: {image_path} ({image_path.stat().st_size:,} bytes)")
    print(f"spec:  {spec_path}")

    if args.local_only:
        if args.apply:
            raise SystemExit("--local-only cannot be used with --apply")
        print("local validation passed")
        return

    token = settings.LINE_CHANNEL_ACCESS_TOKEN
    if not token:
        raise SystemExit("LINE_CHANNEL_ACCESS_TOKEN is missing in .env")

    with httpx.Client(timeout=30.0) as client:
        _validate_with_line(client, token, spec)
        if not args.apply:
            print("dry-run complete: add --apply to create and upload the rich menu")
            return

        rich_menu_id = _create_richmenu(client, token, spec)
        try:
            _upload_richmenu_image(client, token, rich_menu_id, image_path)
            if args.set_default:
                _set_default_richmenu(client, token, rich_menu_id)
        except Exception:
            print(f"created richMenuId before failure: {rich_menu_id}", file=sys.stderr)
            raise

    (Path(args.id_output)).write_text(f"{rich_menu_id}\n", encoding="utf-8")
    print(f"richMenuId: {rich_menu_id}")
    print(f"saved id:    {args.id_output}")
    if args.set_default:
        print("default rich menu updated")
    else:
        print("uploaded only: add --set-default next time if you want it bound to all users")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create, upload, and optionally bind the LINE rich menu.")
    parser.add_argument("--apply", action="store_true", help="Actually create/upload the LINE rich menu.")
    parser.add_argument("--local-only", action="store_true", help="Validate generated local files without calling LINE API.")
    parser.add_argument("--set-default", action="store_true", help="Set the uploaded rich menu as default for all users.")
    parser.add_argument("--no-compose", action="store_true", help="Use existing --image/--spec files without regenerating.")
    parser.add_argument("--image", default="", help="Rich menu image path. Defaults to generated tmp/richmenu image.")
    parser.add_argument("--spec", default="", help="Rich menu JSON spec path. Defaults to generated tmp/richmenu JSON.")
    parser.add_argument("--id-output", default="tmp/richmenu/richmenu-v2-line.id", help="Where to save the created richMenuId.")
    return parser.parse_args()


def _resolve_assets(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.no_compose:
        if not args.image or not args.spec:
            raise SystemExit("--no-compose requires both --image and --spec")
        return Path(args.image), Path(args.spec)

    image_path, spec_path = compose_richmenu_image()
    if args.image or args.spec:
        return Path(args.image or image_path), Path(args.spec or spec_path)
    return image_path, spec_path


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)
    if not isinstance(payload, dict):
        raise ValueError("Rich menu spec must be a JSON object")
    return payload


def _validate_local_assets(image_path: Path, spec: dict[str, Any]) -> None:
    if not image_path.exists():
        raise FileNotFoundError(image_path)
    if image_path.stat().st_size > RICHMENU_MAX_IMAGE_BYTES:
        raise ValueError("Rich menu image must be <= 1 MB")

    with Image.open(image_path) as image:
        image_format = image.format
        width, height = image.size

    if image_format not in {"PNG", "JPEG"}:
        raise ValueError("Rich menu image must be PNG or JPEG")
    if width < 800 or width > 2500:
        raise ValueError("Rich menu image width must be 800-2500 px")
    if height < 250:
        raise ValueError("Rich menu image height must be at least 250 px")
    if width / height < 1.45:
        raise ValueError("Rich menu image aspect ratio must be at least 1.45")

    size = spec.get("size", {})
    if size != {"width": width, "height": height}:
        raise ValueError(f"Spec size {size} does not match image size {(width, height)}")

    areas = spec.get("areas", [])
    if not isinstance(areas, list) or not 1 <= len(areas) <= 20:
        raise ValueError("Rich menu spec must contain 1-20 areas")

    for index, area in enumerate(areas):
        if set(area) != {"bounds", "action"}:
            raise ValueError(f"Area {index} must contain only bounds and action")
        bounds = area["bounds"]
        x = int(bounds["x"])
        y = int(bounds["y"])
        area_width = int(bounds["width"])
        area_height = int(bounds["height"])
        if x < 0 or y < 0 or area_width <= 0 or area_height <= 0:
            raise ValueError(f"Area {index} has invalid bounds")
        if x + area_width > width or y + area_height > height:
            raise ValueError(f"Area {index} is outside the image bounds")


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _validate_with_line(client: httpx.Client, token: str, spec: dict[str, Any]) -> None:
    response = client.post(
        f"{API_BASE_URL}/richmenu/validate",
        headers={**_headers(token), "Content-Type": "application/json"},
        json=spec,
    )
    _raise_for_line(response, "validate rich menu")
    print("LINE validation passed")


def _create_richmenu(client: httpx.Client, token: str, spec: dict[str, Any]) -> str:
    response = client.post(
        f"{API_BASE_URL}/richmenu",
        headers={**_headers(token), "Content-Type": "application/json"},
        json=spec,
    )
    _raise_for_line(response, "create rich menu")
    rich_menu_id = response.json().get("richMenuId")
    if not rich_menu_id:
        raise RuntimeError(f"Missing richMenuId in response: {response.text}")
    print("created rich menu")
    return rich_menu_id


def _upload_richmenu_image(client: httpx.Client, token: str, rich_menu_id: str, image_path: Path) -> None:
    content_type = mimetypes.guess_type(str(image_path))[0] or "image/png"
    if content_type == "image/jpg":
        content_type = "image/jpeg"

    response = client.post(
        f"{DATA_BASE_URL}/richmenu/{rich_menu_id}/content",
        headers={**_headers(token), "Content-Type": content_type},
        content=image_path.read_bytes(),
    )
    _raise_for_line(response, "upload rich menu image")
    print("uploaded rich menu image")


def _set_default_richmenu(client: httpx.Client, token: str, rich_menu_id: str) -> None:
    response = client.post(
        f"{API_BASE_URL}/user/all/richmenu/{rich_menu_id}",
        headers=_headers(token),
    )
    _raise_for_line(response, "set default rich menu")


def _raise_for_line(response: httpx.Response, action: str) -> None:
    if response.status_code < 400:
        return
    try:
        detail = response.json()
    except ValueError:
        detail = response.text
    raise RuntimeError(f"Failed to {action}: HTTP {response.status_code}: {detail}")


if __name__ == "__main__":
    main()
