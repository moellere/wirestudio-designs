"""The gates themselves: a check that passes everything protects nothing."""
from __future__ import annotations

import json
import sys
from importlib.resources import files
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import catalogue  # noqa: E402
import check  # noqa: E402


@pytest.fixture
def designs(tmp_path, monkeypatch):
    root = tmp_path / "designs"
    root.mkdir()
    monkeypatch.setattr(catalogue, "DESIGNS", root)
    return root


def _example(slug: str) -> dict:
    doc = json.loads(files("wirestudio.examples").joinpath("garage-motion.json").read_text())
    doc["id"] = slug
    return doc


def add(root: Path, slug: str, design=None, meta="author: octocat\ntags: [motion]\n", **extra):
    d = root / slug
    d.mkdir()
    if design is not None:
        (d / "design.json").write_text(json.dumps(design))
    if meta is not None:
        (d / "meta.yaml").write_text(meta)
    for name, text in extra.items():
        (d / name.replace("_", ".")).write_text(text)
    return d


def errors(slug: str) -> list[str]:
    return catalogue.load(slug).errors


def test_a_good_design_passes(designs):
    add(designs, "porch-motion", _example("porch-motion"), README_md="# Porch\n")
    assert errors("porch-motion") == []


def test_an_image_is_refused(designs):
    d = add(designs, "porch-motion", _example("porch-motion"))
    (d / "photo.jpg").write_bytes(b"\xff\xd8\xff")
    assert any("photo.jpg: not allowed" in e for e in errors("porch-motion"))


def test_a_literal_credential_is_refused(designs):
    doc = _example("porch-motion")
    doc["fleet"]["secrets_ref"]["wifi_password"] = "hunter22"
    doc["esphome_extras"] = {"ota": {"password": "letmein"}}
    add(designs, "porch-motion", doc)
    [err] = [e for e in errors("porch-motion") if "credentials" in e]
    assert "fleet.secrets_ref.wifi_password" in err and "esphome_extras.ota.password" in err


def test_secret_references_are_fine(designs):
    doc = _example("porch-motion")
    doc["esphome_extras"] = {"ota": {"password": "!secret ota_password"}}
    add(designs, "porch-motion", doc)
    assert errors("porch-motion") == []


def test_the_id_must_match_the_directory(designs):
    add(designs, "porch-motion", _example("something-else"))
    assert any("`id` must be 'porch-motion'" in e for e in errors("porch-motion"))


@pytest.mark.parametrize("meta, match", [
    (None, "meta.yaml is missing"),
    ("tags: [x]\n", "`author` must be your GitHub handle"),
    ("author: octocat\ntags: [Has Spaces]\n", "`tags`"),
    ("author: octocat\nlicense: MIT\n", "every design here is CC-BY-4.0"),
    ("author: octocat\nderived_from: nowhere\n", "not in the catalogue"),
    ("author: octocat\nsource: http://example.com\n", "https://"),
    ("author: octocat\nphoto: x.jpg\n", "unknown keys"),
])
def test_bad_meta_is_refused(designs, meta, match):
    add(designs, "porch-motion", _example("porch-motion"), meta=meta)
    assert any(match in e for e in errors("porch-motion"))


def test_derived_from_an_existing_design_is_fine(designs):
    add(designs, "porch-motion", _example("porch-motion"))
    add(designs, "porch-motion-v2", _example("porch-motion-v2"),
        meta="author: someone-else\nderived_from: porch-motion\n")
    assert errors("porch-motion-v2") == []


def test_a_document_wirestudio_cannot_load_is_refused(designs):
    doc = _example("porch-motion")
    doc["board"] = {"library_id": "esp32-devkitc-v4"}
    doc["surprise"] = True
    add(designs, "porch-motion", doc)
    assert any("does not load in WireStudio" in e for e in errors("porch-motion"))


def test_a_bad_directory_name_is_refused(designs):
    add(designs, "Porch_Motion", _example("Porch_Motion"))
    assert any("directory name" in e for e in errors("Porch_Motion"))


def test_a_file_outside_a_design_directory_fails_the_run(designs, capsys):
    (designs / "loose.json").write_text("{}")
    assert check.main(["--no-esphome"]) == 1
    assert "designs/loose.json" in capsys.readouterr().out


def test_an_empty_catalogue_passes(designs):
    assert check.main(["--no-esphome"]) == 0
