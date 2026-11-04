import filecmp
import json
import os
import subprocess
import sys
from pathlib import Path

import ezdxf
import pytest

from bracketlab.build import BuildOptions, build_job

ROOT = Path(__file__).resolve().parents[1]


def _build(tmp_path: Path, chipset: str, **kwargs):
    return build_job(BuildOptions(chipset=chipset, out=tmp_path, root=ROOT, **kwargs))


def test_shop_files_for_the_stock_and_gen8_bars(tmp_path: Path):
    for chipset, span in (("lga115x", 75), ("hp-microserver-gen8", 65)):
        result = _build(tmp_path, chipset)
        assert result.layout.span_mm == pytest.approx(span)
        assert result.layout.center_spacing_mm == pytest.approx(23)
        assert result.order_ready is False
        directory = tmp_path / chipset
        for name in (
            "bracket.step",
            "bracket-flat.dxf",
            "bracket-drawing.pdf",
            "quote-sendcutsend.txt",
            "quote-pcbway.txt",
            "manifest.json",
        ):
            assert (directory / name).stat().st_size > 0

        manifest = json.loads((directory / "manifest.json").read_text())
        assert manifest["order_ready"] is False
        assert manifest["span_mm"] == pytest.approx(span)
        assert "center_spacing_mm" in manifest["unverified"]
        assert "web_width_mm" in manifest["unverified"]
        assert "ear_height_mm" in manifest["unverified"]

        dxf = ezdxf.readfile(directory / "bracket-flat.dxf")
        model = dxf.modelspace()
        bends = [entity for entity in model if entity.dxftype() == "LINE"]
        circles = [entity for entity in model if entity.dxftype() == "CIRCLE"]
        assert len(bends) == 2
        assert all(entity.dxf.linetype == "BEND" for entity in bends)
        assert len(circles) == 4
        drawn = sorted(round(circle.dxf.center.x, 3) for circle in circles)
        expected = sorted(round(hole.flat_x_mm, 3) for hole in result.layout.holes)
        assert drawn == expected
        assert (directory / "bracket-drawing.pdf").read_bytes().startswith(b"%PDF")

        sendcutsend = (directory / "quote-sendcutsend.txt").read_text()
        pcbway = (directory / "quote-pcbway.txt").read_text()
        for quote in (sendcutsend, pcbway):
            assert "Quantity: 2" in quote
            assert "M3" in quote
            assert "90" in quote
            assert f"{span:.3f}" in quote
        assert "5052-H32" in sendcutsend
        assert "0.125 in" in sendcutsend
        assert "bracket-flat.dxf" in sendcutsend
        assert "mild steel" in pcbway
        assert "bracket.step" in pcbway
        assert "Do your parts need threads? Yes." in pcbway


def test_step_is_one_solid_with_the_formed_holes(tmp_path: Path):
    pytest.importorskip("build123d")
    from build123d import import_step

    result = _build(tmp_path, "hp-microserver-gen8")
    solid = import_step(tmp_path / "hp-microserver-gen8" / "bracket.step")
    assert len(solid.solids()) == 1
    layout = result.layout
    assert solid.is_inside((0, 0, layout.thickness_mm / 2))
    center = layout.holes_for("center")[1]
    ear = layout.holes_for("ear")[1]
    assert solid.is_inside((center.plan_x_mm, 0, center.plan_z_mm)) is False
    assert solid.is_inside((ear.plan_x_mm, 0, ear.plan_z_mm)) is False
    assert solid.is_inside((ear.plan_x_mm, 3, ear.plan_z_mm))
    assert solid.is_inside((layout.x_tangent_mm + 0.2, 0, layout.thickness_mm / 2))
    assert solid.is_inside((layout.x_tangent_mm + 0.2, layout.web_width_mm / 2 + 1, layout.thickness_mm / 2)) is False


def test_lga1700_refuses_until_span_or_orthogonal_is_set(tmp_path: Path):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    refused = subprocess.run(
        [sys.executable, "-m", "bracketlab", "build", "--chipset", "lga1700", "--out", str(tmp_path)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert refused.returncode == 2
    assert "SPAN=" in refused.stderr
    assert "ORTHOGONAL=" in refused.stderr


def test_checked_in_shop_files_match_a_rebuild(tmp_path: Path):
    names = (
        "bracket.step",
        "bracket-flat.dxf",
        "bracket-drawing.pdf",
        "quote-sendcutsend.txt",
        "quote-pcbway.txt",
        "manifest.json",
    )
    for chipset in ("lga115x", "hp-microserver-gen8"):
        _build(tmp_path, chipset)
        for name in names:
            fresh = tmp_path / chipset / name
            checked_in = ROOT / "build" / chipset / name
            assert checked_in.is_file(), checked_in
            assert filecmp.cmp(fresh, checked_in, shallow=False), f"{chipset}/{name}"


def test_lga1700_span_override_still_builds(tmp_path: Path):
    forced = _build(tmp_path, "lga1700", span=78)
    assert forced.layout.span_mm == pytest.approx(78)
    assert forced.layout.center_spacing_mm == pytest.approx(23)
    assert forced.warnings

    matched = _build(tmp_path, "lga1700", orthogonal=78)
    assert matched.layout.span_mm == pytest.approx(78)
    assert matched.warnings == ()
