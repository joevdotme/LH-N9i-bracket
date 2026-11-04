"""Paste-ready quote notes for SendCutSend and PCBWay."""

from __future__ import annotations

from bracketlab.dfm import DfmReport
from bracketlab.layout import Layout


def _mm(value: float) -> str:
    return f"{value:.3f}"


def _header(layout: Layout, *, chipset: str, order_ready: bool, unverified: list[str]) -> list[str]:
    ready = "yes" if order_ready else "NO"
    lines = [
        f"Part: NH-L9i fastening bar, one of a pair. Chipset {chipset}.",
        "Quantity: 2 (the two bars are identical).",
        f"Order ready: {ready}.",
    ]
    if unverified:
        lines.append("Unverified dimensions: " + ", ".join(unverified) + ".")
        lines.append("Measure those on the stock bar, update the cooler YAML, and rebuild before ordering.")
    lines.extend(
        [
            f"Formed end-hole span: {_mm(layout.span_mm)} mm. This is the motherboard pitch the bar spans.",
            f"Center-hole spacing: {_mm(layout.center_spacing_mm)} mm. This bolts to the heatsink and does not change.",
            f"Flat blank: {_mm(layout.flat_length_mm)} x {_mm(layout.flat_width_mm)} mm.",
            "The flat hole distance is longer than the formed span because of the bend allowance.",
            f"Bend: 2 (one each side), {_mm(layout.bend_angle_deg)} deg, ears up.",
            f"Inside bend radius modeled: {_mm(layout.inside_bend_radius_mm)} mm. K-factor {_mm(layout.k_factor)}.",
            f"Ear-hole axis is perpendicular to the ear, {_mm(layout.bend_angle_deg)} deg from vertical.",
            f"Sheet thickness {_mm(layout.thickness_mm)} mm is thicker than the stock stamping. "
            "Check NH-L9i NM-IBT4 screw engagement before ordering.",
        ]
    )
    return lines


def sendcutsend_quote(
    layout: Layout,
    *,
    chipset: str,
    dfm: DfmReport,
    order_ready: bool,
    unverified: list[str],
    countersink_side: str,
    warnings: list[str],
) -> str:
    lines = ["SendCutSend quote", ""]
    lines.extend(_header(layout, chipset=chipset, order_ready=order_ready, unverified=unverified))
    lines.extend(
        [
            "",
            "Material: 5052-H32 aluminum",
            f"Thickness: {_mm(layout.thickness_mm)} mm"
            + (" (0.125 in catalog thickness)" if abs(layout.thickness_mm - 3.175) < 1e-3 else ""),
            "Preferred upload: bracket-flat.dxf",
            "Alternate upload: bracket.step",
            "Units: millimeters",
            "Dashed lines in the DXF are bend centers. Confirm 2 bends, ears up, in the 3D preview.",
            "If the catalog bend radius for 5052 H32 at 0.125 in differs from the modeled radius, "
            "update materials/sendcutsend-5052-0125.yaml and rebuild.",
            "",
            "Holes in the file are plain through-holes. Select the services below; do not expect threads or countersinks in the CAD.",
            f"Inner pair, {_mm(layout.center_spacing_mm)} mm apart: 90 degree countersink for M3.",
            f"  Drawn minor: {_mm(layout.center_hole_diameter_mm)} mm.",
            f"  Major: {_mm(layout.countersink_major_diameter_mm)} mm (do not draw it).",
            f"  Depth: {_mm(dfm.countersink_depth_mm)} mm.",
            f"  Side: {countersink_side.strip()}",
            f"Outer pair, {_mm(layout.span_mm)} mm apart in the formed part: tap M3 x 0.5, through.",
            f"  Drawn diameter: {_mm(layout.ear_hole_diameter_mm)} mm. The tap service may resize this to the M3 tap drill.",
            "",
            "Services: bending, countersinking (inner pair), tapping (outer pair).",
        ]
    )
    if warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines) + "\n"


def pcbway_quote(
    layout: Layout,
    *,
    chipset: str,
    dfm: DfmReport,
    order_ready: bool,
    unverified: list[str],
    countersink_side: str,
    warnings: list[str],
) -> str:
    lines = ["PCBWay sheet-metal quote", ""]
    lines.extend(_header(layout, chipset=chipset, order_ready=order_ready, unverified=unverified))
    lines.extend(
        [
            "",
            "Process: sheet metal",
            "Material: mild steel (change this on the form if you want stainless or aluminum)",
            f"Thickness: {_mm(layout.thickness_mm)} mm",
            "Files: bracket.step (one formed solid, plain holes), bracket-flat.dxf, bracket-drawing.pdf",
            "The STEP was modeled with the SendCutSend 5052 0.125 in bend radius. "
            "Accept the shop radius or rebuild after editing the material preset.",
            "",
            "Do your parts need threads? Yes.",
            f"  2 x M3 x 0.5 through tap on the outer holes (formed span {_mm(layout.span_mm)} mm).",
            f"  Pilot drawn in the CAD: {_mm(layout.ear_hole_diameter_mm)} mm.",
            "",
            "Countersink:",
            f"  2 holes, the inner pair at {_mm(layout.center_spacing_mm)} mm.",
            f"  Pilot diameter: {_mm(layout.center_hole_diameter_mm)} mm.",
            f"  Countersink diameter: {_mm(layout.countersink_major_diameter_mm)} mm.",
            "  Angle: 90 deg.",
            f"  Depth: {_mm(dfm.countersink_depth_mm)} mm.",
            f"  Side: {countersink_side.strip()}",
            "",
            f"Bends: 2 x {_mm(layout.bend_angle_deg)} deg, inside radius {_mm(layout.inside_bend_radius_mm)} mm, ears up.",
        ]
    )
    if warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines) + "\n"
