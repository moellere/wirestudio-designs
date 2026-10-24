"""Write index.json: what the studio's browse view lists.

Run on main after a merge; the workflow publishes the file to the `index`
branch, where the studio reads it from raw.githubusercontent.com. Designs
that fail their checks are left out rather than failing the build -- main
only holds designs that passed, so a gap here means the pinned WireStudio
changed under one, which `check.py` reports.

    python scripts/build_index.py > index.json
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalogue  # noqa: E402

REPO = "moellere/wirestudio-designs"


def _git_dates(path: Path) -> tuple[str | None, str | None]:
    """(first added, last changed) as ISO dates, from history."""
    out = subprocess.run(["git", "log", "--format=%cI", "--", str(path)],
                         capture_output=True, text=True, cwd=catalogue.ROOT).stdout.split()
    return (out[-1], out[0]) if out else (None, None)


def entry_json(entry: catalogue.Entry) -> dict:
    design = entry.design
    added, updated = _git_dates(entry.path)
    return {
        "slug": entry.slug,
        "name": design.name,
        "description": design.description or "",
        "author": entry.meta["author"],
        "tags": entry.meta.get("tags", []),
        "license": catalogue.LICENSE,
        "derived_from": entry.meta.get("derived_from"),
        "source": entry.meta.get("source"),
        "board": design.board.library_id,
        "mcu": design.board.mcu,
        "components": sorted({c.library_id for c in design.components}),
        "schema_version": entry.raw.get("schema_version"),
        "has_readme": (entry.path / "README.md").is_file(),
        "custom_code": entry.custom_code,
        "user_components": [
            {"id": cid, "url": f"https://raw.githubusercontent.com/{REPO}/main/designs/{entry.slug}/components/{cid}.yaml"}
            for cid in entry.user_components
        ],
        "photos": [f"https://raw.githubusercontent.com/{REPO}/main/designs/{entry.slug}/photos/{p.name}"
                   for p in catalogue.photos(entry.path)],
        "added": added,
        "updated": updated,
        "design_url": f"https://raw.githubusercontent.com/{REPO}/main/designs/{entry.slug}/design.json",
        "page_url": f"https://github.com/{REPO}/tree/main/designs/{entry.slug}",
    }


def main() -> int:
    from wirestudio import __version__
    from wirestudio.library import default_library

    library = default_library()
    designs, skipped = [], []
    for slug in catalogue.slugs():
        entry = catalogue.load(slug, library)
        if entry.errors:
            skipped.append(slug)
            continue
        designs.append(entry_json(entry))
    for slug in skipped:
        print(f"left out {slug}: fails its checks", file=sys.stderr)
    json.dump({
        "version": 1,
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "wirestudio": __version__,
        "designs": designs,
    }, sys.stdout, indent=1)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
