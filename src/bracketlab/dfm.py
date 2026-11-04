"""Shop rules for the default SendCutSend 0.125 in 5052 preset."""

from __future__ import annotations

import math
from dataclasses import dataclass

from bracketlab.layout import Layout


class DfmError(Exception):
    """The bar violates a shop limit and was not written."""


@dataclass(frozen=True)
class DfmReport:
    ok: bool
    errors: tuple[str, ...]
    min_bend_gap_mm: float
    countersink_depth_mm: float
    countersink_depth_limit_mm: float


def countersink_depth_mm(major_mm: float, minor_mm: float, angle_deg: float) -> float:
    half = math.radians(angle_deg) / 2
    return (major_mm - minor_mm) / 2 / math.tan(half)


def check(
    layout: Layout,
    *,
    bend_clearance_mm: float,
    min_feature_to_edge_mm: float,
    countersink_depth_fraction: float,
) -> DfmReport:
    errors: list[str] = []
    depth = countersink_depth_mm(
        layout.countersink_major_diameter_mm,
        layout.center_hole_diameter_mm,
        layout.countersink_angle_deg,
    )
    depth_limit = countersink_depth_fraction * layout.thickness_mm
    if depth > depth_limit + 1e-9:
        errors.append(
            f"M3 countersink depth is {depth:.3f} mm and the limit is "
            f"{countersink_depth_fraction:.0%} of the {layout.thickness_mm:.3f} mm sheet "
            f"({depth_limit:.3f} mm)."
        )

    gaps: list[float] = []
    bend_xs = (-layout.bend_flat_x_mm, layout.bend_flat_x_mm)
    for bend_x in bend_xs:
        for hole in layout.holes:
            if hole.operation == "countersink":
                feature_radius = layout.countersink_major_diameter_mm / 2
                feature = "countersink rim"
            else:
                feature_radius = hole.diameter_mm / 2
                feature = "tapped hole"
            gap = abs(hole.flat_x_mm - bend_x) - feature_radius
            gaps.append(gap)
            if gap < bend_clearance_mm - 1e-6:
                errors.append(
                    f"{hole.role} {hole.side} {feature} is {gap:.3f} mm from a bend line. "
                    f"The minimum is {bend_clearance_mm:.3f} mm."
                )

    half_width = layout.web_width_mm / 2
    edge_features = (
        ("countersink rim", layout.countersink_major_diameter_mm / 2),
        ("center hole", layout.center_hole_diameter_mm / 2),
        ("tapped hole", layout.ear_hole_diameter_mm / 2),
    )
    for name, radius in edge_features:
        margin = half_width - radius
        if margin < min_feature_to_edge_mm - 1e-9:
            errors.append(
                f"The {name} is {margin:.3f} mm from the edge of the {layout.web_width_mm:.3f} mm "
                f"blank. The minimum is {min_feature_to_edge_mm:.3f} mm."
            )

    if layout.x_tangent_mm <= 0:
        errors.append("The bend consumed the whole web. Increase the span or reduce the ear.")
    if abs(layout.bend_flat_x_mm) >= abs(layout.flat_hole_x_mm) - 1e-6:
        errors.append("A bend line sits on the rounded ear instead of the straight section.")
    if layout.flange_mm <= layout.ear_hole_diameter_mm / 2:
        errors.append("The tapped hole runs into the bend instead of sitting on the ear.")

    return DfmReport(
        ok=not errors,
        errors=tuple(errors),
        min_bend_gap_mm=min(gaps) if gaps else 0.0,
        countersink_depth_mm=depth,
        countersink_depth_limit_mm=depth_limit,
    )
