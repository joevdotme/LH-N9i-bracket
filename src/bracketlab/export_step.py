"""Formed sheet solid with plain holes. Threads and countersinks stay in the quote."""

from __future__ import annotations

import math
from pathlib import Path

from build123d import Box, Cylinder, Plane, Polygon, Pos, Rot, SlotOverall, extrude, export_step, mirror

from bracketlab.layout import Layout
from bracketlab.stamp import EXPORT_TIMESTAMP

# A hair of overlap lets the web, bend, and ear fuse into one solid.
_OVERLAP_MM = 0.05
_BEND_STEPS = 32


def write_step(layout: Layout, path: Path) -> None:
    solid = formed_solid(layout)
    if len(solid.solids()) != 1:
        raise RuntimeError(f"Expected one solid, got {len(solid.solids())}.")
    path.parent.mkdir(parents=True, exist_ok=True)
    export_step(solid, path, timestamp=EXPORT_TIMESTAMP)


def formed_solid(layout: Layout):
    thickness = layout.thickness_mm
    width = layout.web_width_mm
    radius = layout.inside_bend_radius_mm
    tangent = layout.x_tangent_mm
    flange = layout.flange_mm
    angle = layout.bend_angle_deg

    web = Pos(0, 0, thickness / 2) * Box(2 * (tangent + _OVERLAP_MM), width, thickness)
    bend = _bend_solid(layout)
    ear = _ear_solid(layout)
    pivot = (tangent, 0.0, thickness + radius)
    ear = _about(pivot, angle, ear)
    part = web + bend + mirror(bend, about=Plane.YZ) + ear + mirror(ear, about=Plane.YZ)
    for hole in layout.holes_for("center"):
        part = part - (
            Pos(hole.plan_x_mm, 0, thickness / 2) * Cylinder(hole.diameter_mm / 2, thickness + 4)
        )
    return part


def _ear_solid(layout: Layout):
    """Straight flange, still in the flat, with the tap hole already cut."""
    thickness = layout.thickness_mm
    width = layout.web_width_mm
    tangent = layout.x_tangent_mm
    flange = layout.flange_mm
    overall = 2 * (tangent + flange) + width
    blank = extrude(SlotOverall(overall, width), amount=thickness)
    cutter_end = tangent - _OVERLAP_MM
    cutter = Pos(cutter_end - 500, 0, thickness / 2) * Box(1000, width * 4, thickness + 20)
    ear = blank - cutter
    hole_x = tangent + flange
    hole = Pos(hole_x, 0, thickness / 2) * Cylinder(layout.ear_hole_diameter_mm / 2, thickness + 4)
    return ear - hole


def _bend_solid(layout: Layout):
    """Annular sector extruded across the blank, then stood up in Z."""
    radius = layout.inside_bend_radius_mm
    thickness = layout.thickness_mm
    tangent = layout.x_tangent_mm
    angle = layout.bend_angle_deg
    center_z = thickness + radius
    outer = _arc_points(tangent, center_z, radius + thickness, -90, -90 + angle, _BEND_STEPS)
    inner = _arc_points(tangent, center_z, radius, -90 + angle, -90, _BEND_STEPS)
    # Polygon lives in XY. Y here is the sheet thickness before the axis swap.
    face = Polygon(*[(x, z) for x, z in outer + inner])
    bend = extrude(face, amount=layout.web_width_mm / 2, both=True)
    return Rot(90, 0, 0) * bend


def _arc_points(cx: float, cz: float, radius: float, start_deg: float, end_deg: float, steps: int):
    points = []
    for step in range(steps + 1):
        angle = math.radians(start_deg + (end_deg - start_deg) * step / steps)
        points.append((cx + radius * math.cos(angle), cz + radius * math.sin(angle)))
    return points


def _about(pivot: tuple[float, float, float], angle_deg: float, shape):
    return Pos(*pivot) * Rot(0, -angle_deg, 0) * Pos(-pivot[0], -pivot[1], -pivot[2]) * shape
