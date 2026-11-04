"""Resolve presets and write one chipset directory."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from bracketlab.dfm import DfmError, DfmReport, check
from bracketlab.export_dxf import write_dxf
from bracketlab.export_pdf import write_pdf
from bracketlab.export_step import write_step
from bracketlab.layout import INCH_MM, Layout, choose_span, pattern_warnings, solve
from bracketlab.load import load_chipset, load_cooler, load_material, repo_root
from bracketlab.quotes import pcbway_quote, sendcutsend_quote

_VERIFIED = {"measured", "known"}


@dataclass(frozen=True)
class BuildOptions:
    chipset: str
    cooler: str = "nh-l9i"
    center: float | None = None
    span: float | None = None
    span_x: float | None = None
    span_y: float | None = None
    orthogonal: float | None = None
    thickness: float | None = None
    out: Path = Path("build")
    root: Path | None = None


@dataclass(frozen=True)
class BuildResult:
    layout: Layout
    dfm: DfmReport
    directory: Path
    order_ready: bool
    unverified: tuple[str, ...]
    warnings: tuple[str, ...]


def _status(source: dict, key: str, default: str) -> str:
    return str(source.get(key, default))


def _unverified(
    *,
    center_status: str,
    width_status: str,
    angle_status: str,
    ear_status: str,
    radius_status: str,
) -> list[str]:
    fields = [
        ("center_spacing_mm", center_status),
        ("web_width_mm", width_status),
        ("ear_diameter_mm", width_status),
        ("bend_angle_deg", angle_status),
        ("ear_height_mm", ear_status),
        ("inside_bend_radius_mm", radius_status),
    ]
    return [name for name, status in fields if status not in _VERIFIED]


def build_job(options: BuildOptions) -> BuildResult:
    root = options.root or repo_root()
    chipset = load_chipset(root, options.chipset)
    cooler = load_cooler(root, options.cooler)
    material = load_material(root)

    if (options.span_x is None) ^ (options.span_y is None):
        raise ValueError("SPAN_X and SPAN_Y must be set together.")
    holes = (
        (options.span_x, options.span_y)
        if options.span_x is not None and options.span_y is not None
        else chipset["holes_mm"]
    )
    orthogonal = options.orthogonal if options.orthogonal is not None else float(cooler["orthogonal_pitch_mm"])
    if options.span is None:
        span = choose_span(holes, orthogonal)
    else:
        span = options.span

    center_status = "override" if options.center is not None else _status(cooler, "center_spacing_status", "assumed")
    center = options.center if options.center is not None else float(cooler["center_spacing_mm"])
    preset_thickness = float(material["thickness_in"]) * INCH_MM
    thickness = options.thickness if options.thickness is not None else preset_thickness
    if cooler.get("ear_height_mm") is None:
        ear_height = None
        ear_status = "derived"
    else:
        ear_height = float(cooler["ear_height_mm"])
        ear_status = _status(cooler, "ear_height_status", "assumed")

    layout = solve(
        span_mm=span,
        center_spacing_mm=center,
        orthogonal_pitch_mm=orthogonal,
        bend_angle_deg=float(cooler["bend_angle_deg"]),
        web_width_mm=float(cooler["web_width_mm"]),
        thickness_mm=thickness,
        inside_bend_radius_mm=float(material["inside_bend_radius_in"]) * INCH_MM,
        k_factor=float(material["k_factor"]),
        bend_clearance_mm=float(material["bend_clearance_in"]) * INCH_MM,
        center_hole_diameter_mm=float(cooler["center_hole_diameter_mm"]),
        countersink_major_diameter_mm=float(cooler["countersink_major_diameter_mm"]),
        countersink_angle_deg=float(cooler["countersink_angle_deg"]),
        ear_hole_diameter_mm=float(cooler["ear_hole_diameter_mm"]),
        ear_height_mm=ear_height,
    )
    warnings = pattern_warnings(holes, layout.span_mm, layout.orthogonal_pitch_mm)
    if options.thickness is not None and abs(options.thickness - preset_thickness) > 1e-6:
        warnings.append(
            "Thickness was overridden. Bend clearance and the SendCutSend tap chart "
            "were checked against the 0.125 in preset and may not apply at this thickness."
        )
    unverified = _unverified(
        center_status=center_status,
        width_status=_status(cooler, "web_width_status", "assumed"),
        angle_status=_status(cooler, "bend_angle_status", "assumed"),
        ear_status=ear_status,
        radius_status=_status(material, "inside_bend_radius_status", "assumed"),
    )
    dfm = check(
        layout,
        bend_clearance_mm=float(material["bend_clearance_in"]) * INCH_MM,
        min_feature_to_edge_mm=float(material["min_feature_to_edge_mm"]),
        countersink_depth_fraction=float(material["countersink_depth_fraction"]),
    )
    if not dfm.ok:
        raise DfmError("\n".join(dfm.errors))

    directory = options.out / options.chipset
    directory.mkdir(parents=True, exist_ok=True)
    order_ready = not unverified
    countersink_side = str(cooler.get("countersink_side", "Top face of the web."))
    title = f"NH-L9i bar — {options.chipset}"
    write_dxf(layout, directory / "bracket-flat.dxf")
    write_step(layout, directory / "bracket.step")
    write_pdf(
        layout,
        directory / "bracket-drawing.pdf",
        title=title,
        dfm=dfm,
        order_ready=order_ready,
        unverified=unverified,
        countersink_side=countersink_side,
    )
    quote_args = dict(
        chipset=options.chipset,
        dfm=dfm,
        order_ready=order_ready,
        unverified=unverified,
        countersink_side=countersink_side,
        warnings=warnings,
    )
    (directory / "quote-sendcutsend.txt").write_text(sendcutsend_quote(layout, **quote_args))
    (directory / "quote-pcbway.txt").write_text(pcbway_quote(layout, **quote_args))
    manifest = _manifest(
        options=options,
        layout=layout,
        dfm=dfm,
        holes=holes,
        order_ready=order_ready,
        unverified=unverified,
        warnings=warnings,
        material=material,
        cooler=cooler,
    )
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return BuildResult(
        layout=layout,
        dfm=dfm,
        directory=directory,
        order_ready=order_ready,
        unverified=tuple(unverified),
        warnings=tuple(warnings),
    )


def _round(value: float) -> float:
    return round(value, 4)


def _manifest(
    *,
    options: BuildOptions,
    layout: Layout,
    dfm: DfmReport,
    holes: tuple[float, float],
    order_ready: bool,
    unverified: list[str],
    warnings: list[str],
    material: dict,
    cooler: dict,
) -> dict:
    return {
        "chipset": options.chipset,
        "cooler": options.cooler,
        "order_ready": order_ready,
        "unverified": unverified,
        "warnings": warnings,
        "notes": [
            "Ears use the shop sheet thickness, which is thicker than the stock NH-L9i stamping. Check NM-IBT4 screw engagement.",
            "One bend per side tilts the tapped hole by the bend angle from vertical.",
            "Quantity is 2. Both bars are identical and span the same pitch.",
        ],
        "pattern_mm": [_round(holes[0]), _round(holes[1])],
        "span_mm": _round(layout.span_mm),
        "center_spacing_mm": _round(layout.center_spacing_mm),
        "arm_mm": _round(layout.arm_mm),
        "orthogonal_pitch_mm": _round(layout.orthogonal_pitch_mm),
        "ear_height_mm": _round(layout.ear_height_mm),
        "flat_length_mm": _round(layout.flat_length_mm),
        "flat_width_mm": _round(layout.flat_width_mm),
        "thickness_mm": _round(layout.thickness_mm),
        "bend_angle_deg": _round(layout.bend_angle_deg),
        "inside_bend_radius_mm": _round(layout.inside_bend_radius_mm),
        "k_factor": layout.k_factor,
        "k_factor_status": material.get("k_factor_status", "assumed"),
        "bend_flat_x_mm": _round(layout.bend_flat_x_mm),
        "x_tangent_mm": _round(layout.x_tangent_mm),
        "flange_mm": _round(layout.flange_mm),
        "web_width_mm": _round(layout.web_width_mm),
        "ear_diameter_mm": _round(layout.web_width_mm),
        "holes": [
            {
                "role": hole.role,
                "side": hole.side,
                "plan_x_mm": _round(hole.plan_x_mm),
                "plan_z_mm": _round(hole.plan_z_mm),
                "flat_x_mm": _round(hole.flat_x_mm),
                "diameter_mm": _round(hole.diameter_mm),
                "operation": hole.operation,
            }
            for hole in layout.holes
        ],
        "dfm": {
            "ok": dfm.ok,
            "min_bend_gap_mm": _round(dfm.min_bend_gap_mm),
            "countersink_depth_mm": _round(dfm.countersink_depth_mm),
            "countersink_depth_limit_mm": _round(dfm.countersink_depth_limit_mm),
            "bend_clearance_mm": _round(float(material["bend_clearance_in"]) * INCH_MM),
        },
        "material": material.get("name"),
        "tap": cooler.get("tap"),
        "files": [
            "bracket.step",
            "bracket-flat.dxf",
            "bracket-drawing.pdf",
            "quote-sendcutsend.txt",
            "quote-pcbway.txt",
            "manifest.json",
        ],
    }
