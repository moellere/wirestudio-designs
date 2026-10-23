"""Make a design's photos acceptable: shrink each to at most 2048 px on the
long side, drop every piece of metadata, and keep it under 1 MB.

    python scripts/strip_photos.py designs/<name>

Photos are rewritten in place as JPEG, renamed to the lowercase names
the checks accept (IMG_0042.HEIC.png becomes img-0042-heic.jpg). The
studio's Share does the same before it packs a design.
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalogue  # noqa: E402


def clean(data: bytes) -> bytes:
    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(data)) as img:
        # Apply the EXIF rotation before EXIF goes, or the photo ends up sideways.
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail((catalogue.PHOTO_PX, catalogue.PHOTO_PX))
        for quality in (85, 75, 65, 55):
            out = io.BytesIO()
            img.save(out, "JPEG", quality=quality, optimize=True)
            if out.tell() <= catalogue.PHOTO_BYTES:
                break
        return out.getvalue()


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    for p in catalogue.photos(Path(argv[0])):
        cleaned = clean(p.read_bytes())
        stem = re.sub(r"[^a-z0-9]+", "-", p.stem.lower()).strip("-")[:63] or "photo"
        target = p.with_name(f"{stem}.jpg")
        target.write_bytes(cleaned)
        if target != p:
            p.unlink()
        print(f"{target}: {len(cleaned) // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
