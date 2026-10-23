"""Reading and checking the catalogue: one directory per design under designs/.

    designs/<slug>/design.json   the WireStudio design document (required)
    designs/<slug>/meta.yaml     author, tags, attribution (required)
    designs/<slug>/README.md     longer notes (optional)

Nothing else is accepted in a design directory, which is also what keeps
images out until there is a way to screen them.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DESIGNS = ROOT / "designs"

SLUG = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
HANDLE = re.compile(r"^[A-Za-z0-9](?:-?[A-Za-z0-9]){0,38}$")
TAG = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
MAX_TAGS = 8
LICENSE = "CC-BY-4.0"

# Per-file size caps. A design.json is a few KB; anything near these is
# not a design.
ALLOWED_FILES = {"design.json": 256 * 1024, "meta.yaml": 4 * 1024, "README.md": 64 * 1024}
META_KEYS = {"author", "tags", "license", "derived_from", "source"}

# Keys whose string values are credentials. WireStudio keeps them as
# `!secret name` references; a literal value here is a leaked secret.
SECRET_KEY = re.compile(r"pass(word|phrase)?|secret|token|api_?key|app_?key|nwk_?key|psk|encryption",
                        re.IGNORECASE)


@dataclass
class Entry:
    slug: str
    path: Path
    errors: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)
    design: object = None


def slugs() -> list[str]:
    if not DESIGNS.is_dir():
        return []
    return sorted(p.name for p in DESIGNS.iterdir() if p.is_dir())


def stray_files() -> list[str]:
    """Files directly under designs/, outside any design directory."""
    if not DESIGNS.is_dir():
        return []
    return sorted(p.name for p in DESIGNS.iterdir() if p.is_file() and p.name != "README.md")


def _leaked_secrets(node, where: str = "") -> list[str]:
    found = []
    if isinstance(node, dict):
        for k, v in node.items():
            at = f"{where}.{k}" if where else str(k)
            if isinstance(v, str) and v and SECRET_KEY.search(str(k)) and not v.startswith("!secret "):
                found.append(at)
            else:
                found += _leaked_secrets(v, at)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            found += _leaked_secrets(v, f"{where}[{i}]")
    return found


def _check_meta(meta, slugs_known: set[str]) -> list[str]:
    if not isinstance(meta, dict):
        return ["meta.yaml must be a mapping"]
    errors = []
    unknown = sorted(set(meta) - META_KEYS)
    if unknown:
        errors.append(f"meta.yaml: unknown keys {unknown}; allowed: {sorted(META_KEYS)}")
    author = meta.get("author")
    if not isinstance(author, str) or not HANDLE.match(author):
        errors.append("meta.yaml: `author` must be your GitHub handle")
    tags = meta.get("tags", [])
    if not isinstance(tags, list) or len(tags) > MAX_TAGS or not all(
            isinstance(t, str) and TAG.match(t) for t in tags):
        errors.append(f"meta.yaml: `tags` must be a list of at most {MAX_TAGS} "
                      "lowercase words (a-z, 0-9, -)")
    if meta.get("license", LICENSE) != LICENSE:
        errors.append(f"meta.yaml: every design here is {LICENSE}; drop `license` or set it to that")
    derived = meta.get("derived_from")
    if derived is not None and derived not in slugs_known:
        errors.append(f"meta.yaml: `derived_from` names '{derived}', which is not in the catalogue")
    source = meta.get("source")
    if source is not None and not (isinstance(source, str) and source.startswith("https://")):
        errors.append("meta.yaml: `source` must be an https:// URL")
    return errors


def load(slug: str, library=None) -> Entry:
    """Read and check one design. Errors are collected, never raised."""
    from wirestudio.migrate import load_design

    path = DESIGNS / slug
    entry = Entry(slug, path)
    if not SLUG.match(slug):
        entry.errors.append("directory name must be lowercase a-z, 0-9 and -, "
                            "start and end with a letter or digit, at most 64 characters")

    for p in sorted(path.rglob("*")):
        rel = p.relative_to(path).as_posix()
        if p.is_dir():
            continue
        if rel not in ALLOWED_FILES:
            entry.errors.append(f"{rel}: not allowed; a design holds only {sorted(ALLOWED_FILES)}")
        elif p.stat().st_size > ALLOWED_FILES[rel]:
            entry.errors.append(f"{rel}: over {ALLOWED_FILES[rel] // 1024} KB")

    meta_path = path / "meta.yaml"
    if not meta_path.is_file():
        entry.errors.append("meta.yaml is missing")
    else:
        try:
            entry.meta = yaml.safe_load(meta_path.read_text()) or {}
        except yaml.YAMLError as e:
            entry.errors.append(f"meta.yaml: {e}")
        else:
            entry.errors += _check_meta(entry.meta, set(slugs()) - {slug})

    design_path = path / "design.json"
    if not design_path.is_file():
        entry.errors.append("design.json is missing")
        return entry
    try:
        entry.raw = json.loads(design_path.read_text())
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        entry.errors.append(f"design.json: not JSON: {e}")
        return entry
    leaked = _leaked_secrets(entry.raw)
    if leaked:
        entry.errors.append("design.json: literal credentials at " + ", ".join(leaked)
                            + " -- use `!secret name` references")
    if isinstance(entry.raw, dict) and entry.raw.get("id") != slug:
        entry.errors.append(f"design.json: `id` must be '{slug}', the directory name")
    try:
        entry.design = load_design(entry.raw, library)
    except Exception as e:  # MigrationError or pydantic's ValidationError
        entry.errors.append(f"design.json: does not load in WireStudio: {e}")
    return entry
