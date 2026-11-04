"""Hole layout for one NH-L9i fastening bar.

The center holes stay on the heatsink. The end holes move with the motherboard
pitch the bar spans. A single bend on each side lifts the ear, and the flat
blank is longer than the formed span by the bend allowance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

INCH_MM = 25.4
FIT_TOLERANCE_MM = 0.05
# Extra flat distance past the shop's bend-to-hole minimum so a preset is not
# sitting on the die line.
FLANGE_MARGIN_MM = 0.5


class FitError(Exception):
    """The heatsink spacing does not match either side of the hole pattern."""


@dataclass(frozen=True)
class Hole:
    role: str
    side: str
    plan_x_mm: float
    plan_z_mm: float
    flat_x_mm: float
    diameter_mm: float
    operation: str


@dataclass(frozen=True)
class Layout:
    span_mm: float
    center_spacing_mm: float
    orthogonal_pitch_mm: float
    arm_mm: float
    thickness_mm: float
    web_width_mm: float
    bend_angle_deg: float
    inside_bend_radius_mm: float
    k_factor: float
    bend_allowance_mm: float
    x_tangent_mm: float
    flange_mm: float
    ear_height_mm: float
    center_hole_diameter_mm: float
    countersink_major_diameter_mm: float
    countersink_angle_deg: float
    ear_hole_diameter_mm: float
    holes: tuple[Hole, ...]

    @property
    def neutral_radius_mm(self) -> float:
        return self.inside_bend_radius_mm + self.thickness_mm / 2

    @property
    def flat_hole_x_mm(self) -> float:
        return self.x_tangent_mm + self.bend_allowance_mm + self.flange_mm

    @property
    def flat_length_mm(self) -> float:
        return 2 * (self.flat_hole_x_mm + self.web_width_mm / 2)

    @property
    def flat_width_mm(self) -> float:
        return self.web_width_mm

    @property
    def bend_flat_x_mm(self) -> float:
        """Distance from the blank center to a bend-center line."""
        return self.x_tangent_mm + self.bend_allowance_mm / 2

    def holes_for(self, role: str) -> tuple[Hole, ...]:
        return tuple(hole for hole in self.holes if hole.role == role)


def choose_span(holes_mm: tuple[float, float], orthogonal_mm: float) -> float:
    """Pick the pitch the bar spans.

    One side of the pattern has to equal the distance the heatsink already
    holds the two bars apart. The bar is cut to the other side.
    """
    left, right = holes_mm
    left_matches = abs(left - orthogonal_mm) <= FIT_TOLERANCE_MM
    right_matches = abs(right - orthogonal_mm) <= FIT_TOLERANCE_MM
    if left_matches and right_matches:
        return left
    if left_matches:
        return right
    if right_matches:
        return left
    raise FitError(
        f"Neither {left:g} mm nor {right:g} mm matches the heatsink spacing of "
        f"{orthogonal_mm:g} mm. The bar spans one pitch and the heatsink sets "
        f"the distance between the two bars. Re-run with SPAN=<mm> to force "
        f"the spanned pitch, or ORTHOGONAL=<mm> if the cooler holds the bars "
        f"a different distance apart."
    )


def pattern_warnings(
    holes_mm: tuple[float, float],
    span_mm: float,
    orthogonal_mm: float,
) -> list[str]:
    left, right = holes_mm

    def near(value: float, target: float) -> bool:
        return abs(value - target) <= FIT_TOLERANCE_MM

    warnings: list[str] = []
    if not any(near(hole, span_mm) for hole in holes_mm):
        warnings.append(
            f"The bar span {span_mm:g} mm is not a pitch of this hole pattern "
            f"({left:g} x {right:g} mm)."
        )
    if not any(near(hole, orthogonal_mm) for hole in holes_mm):
        warnings.append(
            f"The heatsink holds the two bars {orthogonal_mm:g} mm apart, and "
            f"neither pitch of {left:g} x {right:g} mm matches that distance."
        )
    uncovered = [hole for hole in holes_mm if not near(hole, span_mm) and not near(hole, orthogonal_mm)]
    if uncovered:
        listed = " and ".join(f"{hole:g} mm" for hole in uncovered)
        warnings.append(
            f"Pitch {listed} is not covered by the bar span or the heatsink spacing."
        )
    if abs(left - right) > FIT_TOLERANCE_MM and near(span_mm, orthogonal_mm):
        warnings.append(
            "The bar span and the heatsink spacing are the same, so the other "
            "side of this rectangular pattern is uncovered."
        )
    return warnings


def _minimum_flange_mm(
    *,
    bend_allowance_mm: float,
    bend_clearance_mm: float,
    ear_hole_diameter_mm: float,
) -> float:
    ear_radius = ear_hole_diameter_mm / 2
    # Flat distance from the bend center to the hole edge is BA/2 + L - radius.
    clearance_limit = (
        bend_clearance_mm + FLANGE_MARGIN_MM + ear_radius - bend_allowance_mm / 2
    )
    return max(clearance_limit, ear_radius)


def solve(
    *,
    span_mm: float,
    center_spacing_mm: float,
    orthogonal_pitch_mm: float,
    bend_angle_deg: float,
    web_width_mm: float,
    thickness_mm: float,
    inside_bend_radius_mm: float,
    k_factor: float,
    bend_clearance_mm: float,
    center_hole_diameter_mm: float,
    countersink_major_diameter_mm: float,
    countersink_angle_deg: float,
    ear_hole_diameter_mm: float,
    ear_height_mm: float | None = None,
) -> Layout:
    if span_mm <= 0 or center_spacing_mm <= 0:
        raise ValueError("Span and center spacing must be positive.")
    if center_spacing_mm >= span_mm:
        raise ValueError(
            "Center spacing must stay smaller than the spanned pitch so each arm has length."
        )
    if not 0 < bend_angle_deg < 90:
        raise ValueError("Bend angle must be between 0 and 90 degrees.")
    if min(thickness_mm, web_width_mm, inside_bend_radius_mm) <= 0:
        raise ValueError("Thickness, width, and bend radius must be positive.")
    if k_factor <= 0 or k_factor >= 1:
        raise ValueError("K-factor must be between 0 and 1.")

    angle = math.radians(bend_angle_deg)
    radius = inside_bend_radius_mm
    neutral = radius + thickness_mm / 2
    allowance = angle * (radius + k_factor * thickness_mm)
    minimum_flange = _minimum_flange_mm(
        bend_allowance_mm=allowance,
        bend_clearance_mm=bend_clearance_mm,
        ear_hole_diameter_mm=ear_hole_diameter_mm,
    )
    arc_rise = neutral * (1 - math.cos(angle))
    if ear_height_mm is None:
        flange = minimum_flange
        ear_height = arc_rise + flange * math.sin(angle)
    else:
        if ear_height_mm < arc_rise - 1e-9:
            raise ValueError(
                "Ear height is lower than the rise of the bend arc. "
                f"The arc alone rises {arc_rise:.3f} mm."
            )
        flange = (ear_height_mm - arc_rise) / math.sin(angle)
        ear_height = ear_height_mm

    # Formed hole X = tangent + horizontal projection of the arc and the flange.
    x_tangent = (
        span_mm / 2
        - neutral * math.sin(angle)
        - flange * math.cos(angle)
    )
    half_center = center_spacing_mm / 2
    half_span = span_mm / 2
    flat_hole = x_tangent + allowance + flange
    web_z = thickness_mm / 2
    ear_z = web_z + ear_height

    holes = (
        Hole("center", "left", -half_center, web_z, -half_center, center_hole_diameter_mm, "countersink"),
        Hole("center", "right", half_center, web_z, half_center, center_hole_diameter_mm, "countersink"),
        Hole("ear", "left", -half_span, ear_z, -flat_hole, ear_hole_diameter_mm, "tap"),
        Hole("ear", "right", half_span, ear_z, flat_hole, ear_hole_diameter_mm, "tap"),
    )
    return Layout(
        span_mm=span_mm,
        center_spacing_mm=center_spacing_mm,
        orthogonal_pitch_mm=orthogonal_pitch_mm,
        arm_mm=(span_mm - center_spacing_mm) / 2,
        thickness_mm=thickness_mm,
        web_width_mm=web_width_mm,
        bend_angle_deg=bend_angle_deg,
        inside_bend_radius_mm=radius,
        k_factor=k_factor,
        bend_allowance_mm=allowance,
        x_tangent_mm=x_tangent,
        flange_mm=flange,
        ear_height_mm=ear_height,
        center_hole_diameter_mm=center_hole_diameter_mm,
        countersink_major_diameter_mm=countersink_major_diameter_mm,
        countersink_angle_deg=countersink_angle_deg,
        ear_hole_diameter_mm=ear_hole_diameter_mm,
        holes=holes,
    )
