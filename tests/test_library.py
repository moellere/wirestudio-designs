"""Library entries: components and boards shared on their own, and boards
shipped with a design."""
from __future__ import annotations

import json
import sys
from importlib.resources import files
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_index  # noqa: E402
import catalogue  # noqa: E402
import check  # noqa: E402
import library  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
LED = (FIXTURES / "led_driver_npn.yaml").read_text()
S2 = (FIXTURES / "lolin-s2-mini.yaml").read_text()
META = "author: octocat\ntags: [esp32s2]\nsource: https://www.wemos.cc/en/latest/s2/s2_mini.html\n"


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(catalogue, "DESIGNS", tmp_path / "designs")
    monkeypatch.setattr(library, "LIBRARY", tmp_path / "library")
    (tmp_path / "designs").mkdir()
    return tmp_path


def add(root: Path, kind: str, lid: str, text: str, meta: str | None = META, **extra) -> Path:
    d = root / "library" / kind / lid
    d.mkdir(parents=True)
    (d / library.KINDS[kind]).write_text(text)
    if meta is not None:
        (d / "meta.yaml").write_text(meta)
    for name, body in extra.items():
        (d / name.replace("_", ".")).write_text(body)
    return d


def errors(kind: str, lid: str) -> list[str]:
    return library.load(kind, lid).errors


def test_a_good_board_and_component_pass(root):
    add(root, "boards", "lolin-s2-mini", S2, README_md="Pinout from the WEMOS docs.\n")
    add(root, "components", "led_driver_npn", LED)
    assert errors("boards", "lolin-s2-mini") == []
    assert errors("components", "led_driver_npn") == []
    assert library.design_for(library.load("boards", "lolin-s2-mini")).board.library_id == "lolin-s2-mini"


@pytest.mark.parametrize("meta, match", [
    (None, "meta.yaml is missing"),
    ("tags: [x]\nsource: https://x.example\n", "`author`"),
    ("author: octocat\n", "`source` must be the https://"),
    ("author: octocat\nsource: http://x.example\n", "`source` must be the https://"),
    ("author: octocat\nsource: https://x.example\nlicense: CC-BY-4.0\n", "every library entry here is MIT"),
    ("author: octocat\nsource: https://x.example\nderived_from: x\n", "unknown keys"),
])
def test_bad_meta_is_refused(root, meta, match):
    add(root, "boards", "lolin-s2-mini", S2, meta=meta)
    assert any(match in e for e in errors("boards", "lolin-s2-mini"))


def test_the_gate_runs_on_the_entry(root):
    add(root, "boards", "lolin-s2-mini", S2.replace("pin: GPIO15", "pin: GPIO14"))
    assert any("board.yaml: onboard_peripherals.led.pin: GPIO14" in e for e in errors("boards", "lolin-s2-mini"))


def test_the_directory_is_the_id(root):
    add(root, "boards", "s2-mini", S2)
    assert any("name the directory boards/lolin-s2-mini" in e for e in errors("boards", "s2-mini"))


def test_a_bundled_id_is_refused(root):
    add(root, "components", "bme280", LED.replace("id: led_driver_npn", "id: bme280", 1))
    assert any("bundled component" in e for e in errors("components", "bme280"))


def test_only_the_entry_files_are_allowed(root):
    d = add(root, "boards", "lolin-s2-mini", S2)
    (d / "photo.jpg").write_bytes(b"\xff\xd8")
    (d / "board.yaml").write_text(S2 + "#" * (33 * 1024))
    errs = " | ".join(errors("boards", "lolin-s2-mini"))
    assert "photo.jpg: not allowed" in errs and "board.yaml: over 32 KB" in errs


def test_a_different_file_under_an_id_a_design_ships_is_refused(root):
    add(root, "components", "led_driver_npn", LED)
    shipped = root / "designs" / "porch-led" / "components"
    shipped.mkdir(parents=True)
    (shipped / "led_driver_npn.yaml").write_text(LED)
    assert errors("components", "led_driver_npn") == []
    (shipped / "led_driver_npn.yaml").write_text(LED.replace("NPN low-side LED driver", "mine", 1))
    assert any("designs/porch-led/components/led_driver_npn.yaml is a different component" in e
               for e in errors("components", "led_driver_npn"))


@pytest.mark.parametrize("template, reasons", [
    ("sensor:\n  - platform: template\n    lambda: return 1;\n", ["lambda"]),
    ("external_components:\n  - source: github://x/y\n", ["external_components"]),
    ("binary_sensor:\n  - platform: gpio\n", []),
])
def test_template_code_is_flagged(template, reasons):
    import yaml

    text = yaml.safe_dump({"id": "x", "esphome": {"yaml_template": template}})
    assert library.template_code(text) == reasons


def test_stray_files_fail_the_run(root, capsys):
    (root / "library" / "boards").mkdir(parents=True)
    (root / "library" / "boards" / "loose.yaml").write_text(S2)
    (root / "library" / "LICENSE").write_text("MIT")
    assert check.main(["--no-esphome"]) == 1
    assert "library/boards/loose.yaml" in capsys.readouterr().out


def test_check_runs_named_library_entries(root, capsys):
    add(root, "boards", "lolin-s2-mini", S2)
    assert check.main(["--no-esphome", "boards/lolin-s2-mini"]) == 0
    assert "PASS  library/boards/lolin-s2-mini" in capsys.readouterr().out
    assert check.main(["--no-esphome", "boards/nope"]) == 2


def _s2_design(slug: str) -> dict:
    doc = json.loads(files("wirestudio.examples").joinpath("garage-motion.json").read_text())
    return {**doc, "id": slug, "board": {"library_id": "lolin-s2-mini", "mcu": "esp32"},
            "components": [{"id": "led", "library_id": "gpio_output", "label": "LED", "params": {}}],
            "buses": [],
            "connections": [{"component_id": "led", "pin_role": "OUT", "target": {"kind": "gpio", "pin": "GPIO15"}}]}


def _design_with_board(root: Path, slug: str, board_text: str = S2, board_id: str = "lolin-s2-mini") -> Path:
    d = root / "designs" / slug
    (d / "boards").mkdir(parents=True)
    (d / "design.json").write_text(json.dumps(_s2_design(slug)))
    (d / "meta.yaml").write_text("author: octocat\n")
    (d / "boards" / f"{board_id}.yaml").write_text(board_text)
    return d


def test_a_design_ships_the_board_it_is_on(root):
    _design_with_board(root, "s2-blink")
    entry = catalogue.load("s2-blink")
    assert entry.errors == [] and entry.user_board == "lolin-s2-mini"


def test_a_design_cannot_ship_a_board_it_is_not_on(root):
    d = _design_with_board(root, "s2-blink")
    other = S2.replace("id: lolin-s2-mini", "id: other-s2", 1)
    (d / "boards" / "other-s2.yaml").write_text(other)
    assert any("at most one" in e for e in catalogue.load("s2-blink").errors)
    (d / "boards" / "lolin-s2-mini.yaml").unlink()
    errs = catalogue.load("s2-blink").errors
    assert any("board 'lolin-s2-mini' is neither in WireStudio's library" in e for e in errs)


def test_the_index_lists_library_entries_and_design_boards(root, monkeypatch, capsys):
    monkeypatch.setattr(build_index, "_git_dates", lambda path: ("2026-10-24", "2026-10-24"))
    add(root, "boards", "lolin-s2-mini", S2)
    add(root, "components", "led_driver_npn", LED)
    _design_with_board(root, "s2-blink")
    assert build_index.main() == 0
    index = json.loads(capsys.readouterr().out)
    [board] = index["boards"]
    assert board["id"] == "lolin-s2-mini" and board["chip_variant"] == "esp32s2" and board["license"] == "MIT"
    assert board["url"].endswith("/main/library/boards/lolin-s2-mini/board.yaml")
    [comp] = index["components"]
    assert comp["id"] == "led_driver_npn" and comp["custom_code"] == [] and comp["author"] == "octocat"
    [design] = index["designs"]
    assert design["user_boards"] == [{"id": "lolin-s2-mini", "url": design["design_url"].replace(
        "design.json", "boards/lolin-s2-mini.yaml")}]
