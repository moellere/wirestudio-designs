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


def _photo(path: Path, fmt="JPEG", size=(800, 600), exif=False):
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", size, (40, 120, 200))
    kwargs = {}
    if exif:
        e = Image.Exif()
        e[0x010F] = "PhoneMaker"  # Make
        kwargs["exif"] = e
    img.save(path, fmt, **kwargs)


def test_a_clean_photo_passes(designs):
    d = add(designs, "porch-motion", _example("porch-motion"))
    _photo(d / "photos" / "front.jpg")
    _photo(d / "photos" / "inside.png", fmt="PNG")
    assert errors("porch-motion") == []


@pytest.mark.parametrize("name, kwargs, match", [
    ("front.jpg", {"exif": True}, "carries metadata"),
    ("front.jpg", {"size": (3000, 2000)}, "at most 2048 px"),
    ("front.png", {"fmt": "JPEG"}, "not what its extension says"),
    ("Front.JPG", {}, "not allowed"),
    ("front.gif", {"fmt": "GIF"}, "not allowed"),
])
def test_a_bad_photo_is_refused(designs, name, kwargs, match):
    d = add(designs, "porch-motion", _example("porch-motion"))
    _photo(d / "photos" / name, **kwargs)
    assert any(match in e for e in errors("porch-motion"))


def test_a_corrupt_photo_is_refused(designs):
    d = add(designs, "porch-motion", _example("porch-motion"))
    (d / "photos").mkdir()
    (d / "photos" / "front.jpg").write_bytes(b"\xff\xd8\xff not really a jpeg")
    assert any("not a readable image" in e for e in errors("porch-motion"))


def test_at_most_four_photos(designs):
    d = add(designs, "porch-motion", _example("porch-motion"))
    for i in range(5):
        _photo(d / "photos" / f"p{i}.jpg", size=(64, 64))
    assert any("at most 4 photos" in e for e in errors("porch-motion"))


def test_strip_photos_makes_a_refused_photo_acceptable(designs):
    import strip_photos

    d = add(designs, "porch-motion", _example("porch-motion"))
    _photo(d / "photos" / "IMG_0042.png", fmt="PNG", size=(4000, 3000), exif=True)
    assert errors("porch-motion")
    assert strip_photos.main([str(d)]) == 0
    assert [p.name for p in catalogue.photos(d)] == ["img-0042.jpg"]
    assert errors("porch-motion") == []
