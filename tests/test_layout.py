from pathlib import Path

import pytest

from bracketlab.build import BuildOptions, build_job
from bracketlab.dfm import DfmError, check
from bracketlab.layout import INCH_MM, FitError, choose_span, pattern_warnings, solve
from bracketlab.load import list_chipsets, load_chipset, load_cooler, load_material

ROOT = Path(__file__).resolve().parents[1]


def _presets():
    cooler = load_cooler(ROOT, "nh-l9i")
    material = load_material(ROOT)
    return cooler, material


def _solve(chipset: str, **overrides):
    cooler, material = _presets()
    chip = load_chipset(ROOT, chipset)
    holes = chip["holes_mm"]
    orthogonal = overrides.pop("orthogonal", float(cooler["orthogonal_pitch_mm"]))
    span = overrides.pop("span", None)
    if span is None:
        span = choose_span(holes, orthogonal)
    kwargs = dict(
        span_mm=span,
        center_spacing_mm=float(cooler["center_spacing_mm"]),
        orthogonal_pitch_mm=orthogonal,
        bend_angle_deg=float(cooler["bend_angle_deg"]),
        web_width_mm=float(cooler["web_width_mm"]),
        thickness_mm=float(material["thickness_in"]) * INCH_MM,
        inside_bend_radius_mm=float(material["inside_bend_radius_in"]) * INCH_MM,
        k_factor=float(material["k_factor"]),
        bend_clearance_mm=float(material["bend_clearance_in"]) * INCH_MM,
        center_hole_diameter_mm=float(cooler["center_hole_diameter_mm"]),
        countersink_major_diameter_mm=float(cooler["countersink_major_diameter_mm"]),
        countersink_angle_deg=float(cooler["countersink_angle_deg"]),
        ear_hole_diameter_mm=float(cooler["ear_hole_diameter_mm"]),
    )
    kwargs.update(overrides)
    return solve(**kwargs)


def test_center_spacing_is_preserved_for_every_fitting_preset_and_a_span_override():
    for name in list_chipsets(ROOT):
        chip = load_chipset(ROOT, name)
        orthogonal = float(load_cooler(ROOT, "nh-l9i")["orthogonal_pitch_mm"])
        try:
            choose_span(chip["holes_mm"], orthogonal)
        except FitError:
            continue
        layout = _solve(name)
        assert layout.center_spacing_mm == pytest.approx(23.0)
        centers = layout.holes_for("center")
        assert centers[1].plan_x_mm - centers[0].plan_x_mm == pytest.approx(23.0)

    forced = _solve("lga1700", span=78)
    assert forced.center_spacing_mm == pytest.approx(23.0)
    assert forced.span_mm == pytest.approx(78)


def test_gen8_shortens_each_arm_by_5_mm():
    stock = _solve("lga115x")
    gen8 = _solve("hp-microserver-gen8")

    assert stock.span_mm == pytest.approx(75)
    assert gen8.span_mm == pytest.approx(65)
    assert gen8.span_mm == pytest.approx(stock.span_mm - 10)
    assert stock.arm_mm == pytest.approx((75 - 23) / 2)
    assert gen8.arm_mm == pytest.approx(stock.arm_mm - 5)
    assert gen8.center_spacing_mm == pytest.approx(stock.center_spacing_mm)
    assert gen8.x_tangent_mm == pytest.approx(stock.x_tangent_mm - 5)
    assert gen8.flange_mm == pytest.approx(stock.flange_mm)

    stock_ears = stock.holes_for("ear")
    gen8_ears = gen8.holes_for("ear")
    assert stock_ears[1].plan_x_mm - stock_ears[0].plan_x_mm == pytest.approx(75)
    assert gen8_ears[1].plan_x_mm - gen8_ears[0].plan_x_mm == pytest.approx(65)


def test_flat_blank_is_longer_than_the_formed_span():
    layout = _solve("hp-microserver-gen8")
    flat_pitch = layout.holes_for("ear")[1].flat_x_mm - layout.holes_for("ear")[0].flat_x_mm
    assert flat_pitch > layout.span_mm


def test_patterns_that_miss_the_heatsink_spacing_need_an_override():
    orthogonal = 75.0
    for name in ("lga1700", "lga1851", "lga2011-square", "lga2011-narrow", "am4"):
        holes = load_chipset(ROOT, name)["holes_mm"]
        with pytest.raises(FitError, match=r"SPAN="):
            choose_span(holes, orthogonal)
        with pytest.raises(FitError, match=r"ORTHOGONAL="):
            choose_span(holes, orthogonal)

    assert choose_span((78, 78), 78) == pytest.approx(78)
    warnings = pattern_warnings((78, 78), 78, 75)
    assert warnings
    assert pattern_warnings((75, 65), 65, 75) == []


def test_gen8_bend_lines_clear_the_sendcutsend_die():
    cooler, material = _presets()
    layout = _solve("hp-microserver-gen8")
    report = check(
        layout,
        bend_clearance_mm=float(material["bend_clearance_in"]) * INCH_MM,
        min_feature_to_edge_mm=float(material["min_feature_to_edge_mm"]),
        countersink_depth_fraction=float(material["countersink_depth_fraction"]),
    )
    assert report.ok
    assert report.min_bend_gap_mm >= float(material["bend_clearance_in"]) * INCH_MM
    assert cooler["bend_angle_deg"] == 20


def test_thin_sheet_fails_the_countersink_depth_rule(tmp_path: Path):
    with pytest.raises(DfmError, match="countersink depth"):
        build_job(
            BuildOptions(
                chipset="lga115x",
                thickness=2.0,
                out=tmp_path,
                root=ROOT,
            )
        )
    assert not (tmp_path / "lga115x" / "bracket.step").exists()
