"""Gate the catalogue: every design must pass before it merges.

For each design directory:
  layout    only design.json, meta.yaml and README.md, each under its size cap
  meta      author, tags and attribution are well-formed
  secrets   no literal credential in design.json
  components  any components/*.yaml passes WireStudio's component gate, and is used
  design    the document loads in WireStudio (migrated to the current schema)
  review    the studio's own validate checks: an error fails, a warning is noted
  esphome   the YAML WireStudio generates passes upstream `esphome config`

Designs that run code the studio did not generate (a lambda, external
components, includes) are flagged for the reviewer, not refused.

Usage:
    python scripts/check.py                 # every design
    python scripts/check.py my-design ...   # just these
    python scripts/check.py --no-esphome    # skip the slow stage

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
    ap.add_argument("slugs", nargs="*", help="design directories to check (default: all)")
    ap.add_argument("--no-esphome", action="store_true", help="skip `esphome config`")
    args = ap.parse_args(argv)

    from wirestudio.library import default_library

    library = default_library()
    known = catalogue.slugs()
    targets = args.slugs or known
    missing = [s for s in targets if s not in known]
    if missing:
        print(f"no such design(s): {', '.join(missing)}", file=sys.stderr)
        return 2

    annotate = bool(os.environ.get("GITHUB_ACTIONS"))
    failed = 0
    stray = catalogue.stray_files()
    for name in stray:
        print(f"  FAIL  designs/{name}: a design goes in its own directory, "
              "designs/<slug>/design.json")
    with tempfile.TemporaryDirectory() as tmp:
        for slug in targets:
            entry = catalogue.load(slug, library)
            if not entry.errors and not args.no_esphome:
                try:
                    detail = esphome_config(slug, entry.design, entry.library, Path(tmp))
                except Exception as e:  # a generator crash is a failed gate, not a crashed run
                    detail = f"WireStudio could not generate YAML: {e}"
                if detail:
                    entry.errors.append("esphome config rejected the generated YAML:\n" + detail)
            print(f"  {'PASS' if not entry.errors else 'FAIL'}  {slug}")
            for err in entry.errors:
                print("        " + err.replace("\n", "\n        "))
                if annotate:
                    first = err.splitlines()[0].replace("%", "%25")
                    print(f"::error file=designs/{slug}/design.json::{first}")
            notes = [f"warning: {w}" for w in entry.warnings]
            if entry.custom_code:
                notes.append("runs custom code (" + ", ".join(entry.custom_code) + "): read it before approving")
            for note in notes:
                print("        " + note)
                if annotate:
                    print(f"::warning file=designs/{slug}/design.json::{note.replace('%', '%25')}")
            failed += bool(entry.errors)

    print(f"\n{len(targets) - failed} of {len(targets)} designs pass")
    return 1 if failed or stray else 0


if __name__ == "__main__":
    sys.exit(main())
