"""Gate the catalogue: every design and library entry must pass before it merges.

For each design directory:
  layout    only design.json, meta.yaml and README.md, each under its size cap
  meta      author, tags and attribution are well-formed
  secrets   no literal credential in design.json
  components  any components/*.yaml passes WireStudio's component gate, and is used
  board     a boards/<id>.yaml passes WireStudio's board gate, and is the design's board
  design    the document loads in WireStudio (migrated to the current schema)
  review    the studio's own validate checks: an error fails, a warning is noted
  esphome   the YAML WireStudio generates passes upstream `esphome config`

For each library entry (library/components/<id>, library/boards/<id>):
  layout    only the entry's YAML, meta.yaml and README.md, each under its size cap
  meta      author, tags, the datasheet it came from, and MIT
  gate      the component or board passes WireStudio's own gate, under its own id
  conflicts no design here ships a different file under the same id
  esphome   the gate's synthetic design passes upstream `esphome config`

Designs and components that run code the studio did not generate (a
lambda, external components, includes) are flagged for the reviewer, not
refused.

Usage:
    python scripts/check.py                       # everything
    python scripts/check.py my-design ...         # just these designs
    python scripts/check.py components/my_part    # or library entries
    python scripts/check.py --no-esphome          # skip the slow stage

Exit 0 when everything passes, 1 otherwise.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalogue  # noqa: E402
import library as lib_entries  # noqa: E402


def _report(label: str, file: str, errors: list[str], notes: list[str], annotate: bool) -> None:
    print(f"  {'PASS' if not errors else 'FAIL'}  {label}")
    for err in errors:
        print("        " + err.replace("\n", "\n        "))
        if annotate:
            first = err.splitlines()[0].replace("%", "%25")
            print(f"::error file={file}::{first}")
    for note in notes:
        print("        " + note)
        if annotate:
            print(f"::warning file={file}::{note.replace('%', '%25')}")


def esphome_config(slug: str, design, library, workdir: Path) -> str | None:
    """None when ESPHome accepts the generated YAML, else its output tail."""
    from wirestudio.generate.yaml_gen import render_yaml
    from wirestudio.validate import write_secrets_stub

    out = workdir / slug
    out.mkdir(parents=True, exist_ok=True)
    yaml_text = render_yaml(design, library)
    (out / f"{slug}.yaml").write_text(yaml_text)
    write_secrets_stub(yaml_text, out / "secrets.yaml")
    res = subprocess.run(["esphome", "config", f"{slug}.yaml"],
                         capture_output=True, text=True, cwd=out)
    if res.returncode == 0:
        return None
    return "\n".join((res.stdout + res.stderr).strip().splitlines()[-30:])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slugs", nargs="*",
                    help="designs, or components/<id> and boards/<id> library entries (default: all)")
    ap.add_argument("--no-esphome", action="store_true", help="skip `esphome config`")
    args = ap.parse_args(argv)

    from wirestudio.library import default_library

    library = default_library()
    known = catalogue.slugs()
    entries_known = [f"{kind}/{lid}" for kind in lib_entries.KINDS for lid in lib_entries.ids(kind)]
    wanted = args.slugs or known + entries_known
    missing = [s for s in wanted if s not in known and s not in entries_known]
    if missing:
        print(f"no such design(s) or library entries: {', '.join(missing)}", file=sys.stderr)
        return 2

    annotate = bool(os.environ.get("GITHUB_ACTIONS"))
    failed = 0
    stray = catalogue.stray_files()
    for name in stray:
        print(f"  FAIL  designs/{name}: a design goes in its own directory, "
              "designs/<slug>/design.json")
    lib_stray = lib_entries.stray_files()
    for name in lib_stray:
        print(f"  FAIL  library/{name}: an entry goes in its own directory, "
              "library/components/<id>/ or library/boards/<id>/")
    with tempfile.TemporaryDirectory() as tmp:
        for name in wanted:
            if name in known:
                entry = catalogue.load(name, library)
                design, elib, file, label = entry.design, entry.library, f"designs/{name}/design.json", name
            else:
                kind, lid = name.split("/", 1)
                entry = lib_entries.load(kind, lid, library)
                design = None if entry.errors else lib_entries.design_for(entry)
                elib, file, label = entry.library, f"{entry.where}/{entry.file}", entry.where
            if not entry.errors and not args.no_esphome and design is not None:
                try:
                    detail = esphome_config(name.replace("/", "-"), design, elib, Path(tmp))
                except Exception as e:  # a generator crash is a failed gate, not a crashed run
                    detail = f"WireStudio could not generate YAML: {e}"
                if detail:
                    entry.errors.append("esphome config rejected the generated YAML:\n" + detail)
            notes = [f"warning: {w}" for w in entry.warnings]
            if entry.custom_code:
                notes.append("runs custom code (" + ", ".join(entry.custom_code) + "): read it before approving")
            if name not in known and not entry.errors and design is None:
                notes.append("esphome config not run: the component hangs off a hub, as in the studio's own gate")
            _report(label, file, entry.errors, notes, annotate)
            failed += bool(entry.errors)

    print(f"\n{len(wanted) - failed} of {len(wanted)} pass")
    return 1 if failed or stray or lib_stray else 0


if __name__ == "__main__":
    sys.exit(main())
