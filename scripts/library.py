"""Reading and checking the library: components and boards shared on their own.

    library/components/<id>/component.yaml   a WireStudio component (required)
    library/boards/<id>/board.yaml           a WireStudio board (required)
    library/<kind>/<id>/meta.yaml            author, tags, source (required)
    library/<kind>/<id>/README.md            longer notes (optional)

Entries are MIT, not CC-BY like designs, so a maintainer can promote one
into WireStudio's bundled library with its author credited. Each passes
the gate the studio's library editor runs, and its id may not differ in
meaning from the same id shipped inside a design here.
"""
from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml

import catalogue

LIBRARY = catalogue.ROOT / "library"
KINDS = {"components": "component.yaml", "boards": "board.yaml"}
ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
LICENSE = "MIT"
ENTRY_BYTES = 32 * 1024
FILE_BYTES = {"meta.yaml": 4 * 1024, "README.md": 64 * 1024}
META_KEYS = {"author", "tags", "license", "source"}
# Text in a component's ESPHome template that compiles or fetches code the
# studio did not write, the template-side counterpart of catalogue.custom_code.
_TEMPLATE_CODE = {"lambda": re.compile(r"\blambda\b"),
                  "external_components": re.compile(r"\bexternal_components\b"),
                  "includes": re.compile(r"^\s*includes\s*:", re.MULTILINE),
                  "libraries": re.compile(r"^\s*libraries\s*:", re.MULTILINE)}


@dataclass
class LibraryEntry:
    kind: str
    id: str
    path: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    text: str = ""
    item: object = None
    library: object = None
    custom_code: list[str] = field(default_factory=list)

    @property
    def where(self) -> str:
        return f"library/{self.kind}/{self.id}"

    @property
    def file(self) -> str:
        return KINDS[self.kind]


def ids(kind: str) -> list[str]:
    d = LIBRARY / kind
    return sorted(p.name for p in d.iterdir() if p.is_dir()) if d.is_dir() else []


def stray_files() -> list[str]:
    """Files under library/ outside any entry directory."""
    if not LIBRARY.is_dir():
        return []
    out = [p.name for p in LIBRARY.iterdir()
           if (p.is_file() and p.name not in ("README.md", "LICENSE")) or (p.is_dir() and p.name not in KINDS)]
    for kind in KINDS:
        d = LIBRARY / kind
        if d.is_dir():
            out += [f"{kind}/{p.name}" for p in d.iterdir() if p.is_file()]
    return sorted(out)


def template_code(text: str) -> list[str]:
    """Why a reviewer should read a component's template, as sorted reasons."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return []
    esphome = data.get("esphome") if isinstance(data, dict) else None
    template = str((esphome or {}).get("yaml_template") or "") if isinstance(esphome, dict) else ""
    return sorted(k for k, rx in _TEMPLATE_CODE.items() if rx.search(template))


def _check_meta(meta) -> list[str]:
    if not isinstance(meta, dict):
        return ["meta.yaml must be a mapping"]
    errors = []
    unknown = sorted(set(meta) - META_KEYS)
    if unknown:
        errors.append(f"meta.yaml: unknown keys {unknown}; allowed: {sorted(META_KEYS)}")
    author = meta.get("author")
    if not isinstance(author, str) or not catalogue.HANDLE.match(author):
        errors.append("meta.yaml: `author` must be your GitHub handle")
    tags = meta.get("tags", [])
    if not isinstance(tags, list) or len(tags) > catalogue.MAX_TAGS or not all(
            isinstance(t, str) and catalogue.TAG.match(t) for t in tags):
        errors.append(f"meta.yaml: `tags` must be a list of at most {catalogue.MAX_TAGS} "
                      "lowercase words (a-z, 0-9, -)")
    if meta.get("license", LICENSE) != LICENSE:
        errors.append(f"meta.yaml: every library entry here is {LICENSE}; drop `license` or set it to that")
    source = meta.get("source")
    if not (isinstance(source, str) and source.startswith("https://")):
        errors.append("meta.yaml: `source` must be the https:// datasheet or product page "
                      "the entry was written from")
    return errors


def shipped_elsewhere(kind: str, lid: str) -> dict[str, str]:
    """The same id shipped inside designs: {slug: text}."""
    out = {}
    for slug in catalogue.slugs():
        p = catalogue.DESIGNS / slug / kind / f"{lid}.yaml"
        if p.is_file():
            out[slug] = p.read_text()
    return out


def load(kind: str, lid: str, library=None) -> LibraryEntry:
    """Read and check one entry. Errors are collected, never raised."""
    from wirestudio.library import Library, default_library
    from wirestudio.library.board_check import create_board
    from wirestudio.library.check import create_component

    path = LIBRARY / kind / lid
    entry = LibraryEntry(kind, lid, path)
    if not ID.match(lid):
        entry.errors.append("directory name must be the entry's id: lowercase a-z, 0-9, '_' and '-', "
                            "starting with a letter or digit, at most 64 characters")

    caps = {entry.file: ENTRY_BYTES, **FILE_BYTES}
    for p in sorted(path.rglob("*")):
        if p.is_dir():
            continue
        rel = p.relative_to(path).as_posix()
        if rel not in caps:
            entry.errors.append(f"{rel}: not allowed; an entry holds {sorted(caps)}")
        elif p.stat().st_size > caps[rel]:
            entry.errors.append(f"{rel}: over {caps[rel] // 1024} KB")

    meta_path = path / "meta.yaml"
    if not meta_path.is_file():
        entry.errors.append("meta.yaml is missing")
    else:
        try:
            entry.meta = yaml.safe_load(meta_path.read_text()) or {}
        except yaml.YAMLError as e:
            entry.errors.append(f"meta.yaml: {e}")
        else:
            entry.errors += _check_meta(entry.meta)

    src = path / entry.file
    if not src.is_file():
        entry.errors.append(f"{entry.file} is missing")
        return entry
    entry.text = src.read_text()
    if kind == "components":
        entry.custom_code = template_code(entry.text)

    base = library or default_library()
    entry.library = Library(base.root, Path(tempfile.mkdtemp(prefix=f"{lid}-lib-")))
    create = create_board if kind == "boards" else create_component
    report = create(entry.text, entry.library)
    if not report.ok:
        entry.errors += [f"{entry.file}: {e}" for e in report.errors]
        return entry
    if report.library_id != lid:
        entry.errors.append(f"{entry.file}: its id is '{report.library_id}'; "
                            f"name the directory {kind}/{report.library_id}")
        return entry
    entry.warnings += report.warnings
    entry.item = entry.library.board(lid) if kind == "boards" else entry.library.component(lid)
    for slug, text in shipped_elsewhere(kind, lid).items():
        if text != entry.text:
            entry.errors.append(f"designs/{slug}/{kind}/{lid}.yaml is a different {kind[:-1]} with this id; "
                                "the studio cannot install both. Make them the same file, or rename one")
    return entry


def design_for(entry: LibraryEntry):
    """The design `esphome config` is run on: the component on the gate's
    synthetic design, or the board with its onboard peripherals seeded.
    None for a component that hangs off a hub, which the gate cannot
    place on its own either."""
    if entry.kind == "boards":
        from wirestudio.library.board_check import seeded_design

        return seeded_design(entry.item, entry.library)[0]
    from wirestudio.library.check import synthetic_design

    if any(p.kind == "hub_ref" for p in entry.item.electrical.pins):
        return None
    return synthetic_design(entry.item, entry.library, on_buses=True)
