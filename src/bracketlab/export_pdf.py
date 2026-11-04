"""One-page hole table for the shop drawing."""

from __future__ import annotations

import math
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from bracketlab.dfm import DfmReport
from bracketlab.layout import Layout


def _mm(value: float) -> str:
    return f"{value:.3f}"


def write_pdf(
    layout: Layout,
    path: Path,
    *,
    title: str,
    dfm: DfmReport,
    order_ready: bool,
    unverified: list[str],
    countersink_side: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # invariant=1 freezes the PDF timestamp and file id so a rebuild matches.
    drawing = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    width, height = letter
    y = height - 48

    drawing.setFont("Helvetica-Bold", 14)
    drawing.drawString(48, y, title)
    y -= 18
    drawing.setFont("Helvetica", 10)
    ready = "yes" if order_ready else "no — confirm the unverified dimensions before ordering"
    drawing.drawString(48, y, f"Order ready: {ready}")
    y -= 28

    drawing.setFont("Helvetica-Bold", 11)
    drawing.drawString(48, y, "Formed bar")
    y -= 14
    drawing.setFont("Helvetica", 9)
    formed = [
        f"End-hole span (motherboard): {_mm(layout.span_mm)} mm",
        f"Center-hole spacing (heatsink): {_mm(layout.center_spacing_mm)} mm",
        f"Arm, center hole to end hole: {_mm(layout.arm_mm)} mm",
        f"Distance between the two bars, set by the heatsink: {_mm(layout.orthogonal_pitch_mm)} mm",
        f"Thickness: {_mm(layout.thickness_mm)} mm",
        f"Width: {_mm(layout.web_width_mm)} mm",
        f"Bend: {_mm(layout.bend_angle_deg)} deg up, inside radius {_mm(layout.inside_bend_radius_mm)} mm",
        f"Ear height, web midplane to ear-hole midplane: {_mm(layout.ear_height_mm)} mm",
        f"Flat blank: {_mm(layout.flat_length_mm)} x {_mm(layout.flat_width_mm)} mm",
        "Upload files use plain through-holes. Countersinks and threads are services.",
    ]
    for line in formed:
        drawing.drawString(48, y, line)
        y -= 12

    y -= 8
    drawing.setFont("Helvetica-Bold", 11)
    drawing.drawString(48, y, "Hole table")
    y -= 14
    drawing.setFont("Helvetica", 9)
    drawing.drawString(48, y, "Role")
    drawing.drawString(140, y, "Flat X (mm)")
    drawing.drawString(230, y, "Drawn dia (mm)")
    drawing.drawString(330, y, "Shop operation")
    y -= 12
    for hole in layout.holes:
        if hole.operation == "countersink":
            operation = (
                f"90 deg M3 countersink, major {_mm(layout.countersink_major_diameter_mm)} mm, "
                f"depth {_mm(dfm.countersink_depth_mm)} mm"
            )
        else:
            operation = "M3x0.5 through tap"
        drawing.drawString(48, y, f"{hole.role} {hole.side}")
        drawing.drawString(140, y, _mm(hole.flat_x_mm))
        drawing.drawString(230, y, _mm(hole.diameter_mm))
        drawing.setFont("Helvetica", 8)
        drawing.drawString(330, y, operation)
        drawing.setFont("Helvetica", 9)
        y -= 12

    y -= 8
    drawing.drawString(48, y, f"Countersink side: {countersink_side.strip()}")
    y -= 12
    drawing.drawString(
        48,
        y,
        "The tapped hole is perpendicular to the ear, so its axis is tilted by the bend angle.",
    )
    y -= 20

    _draw_flat(drawing, layout, left=48, top=y, box_width=width - 96, box_height=120)
    y -= 140
    drawing.setFont("Helvetica", 8)
    if unverified:
        drawing.drawString(48, y, "Unverified: " + ", ".join(unverified))
    drawing.showPage()
    drawing.save()


def _draw_flat(drawing: canvas.Canvas, layout: Layout, left: float, top: float, box_width: float, box_height: float) -> None:
    length = layout.flat_length_mm
    width = layout.flat_width_mm
    scale = min((box_width - 20) / length, (box_height - 28) / width)
    drawn_length = length * scale
    drawn_width = width * scale
    origin_x = left + (box_width - drawn_length) / 2
    origin_y = top - box_height + (box_height - drawn_width) / 2

    def px(x_mm: float, y_mm: float) -> tuple[float, float]:
        return (origin_x + (x_mm + length / 2) * scale, origin_y + (y_mm + width / 2) * scale)

    half_hole = layout.flat_hole_x_mm
    radius = layout.web_width_mm / 2
    path = drawing.beginPath()
    start = px(-half_hole, radius)
    path.moveTo(*start)
    path.lineTo(*px(half_hole, radius))
    # Right cap, clockwise through the outer point when viewed in PDF y-up.
    _arc(path, px, half_hole, radius, start_deg=90, sweep_deg=-180)
    path.lineTo(*px(-half_hole, -radius))
    _arc(path, px, -half_hole, radius, start_deg=270, sweep_deg=-180)
    path.close()
    drawing.setStrokeColorRGB(0, 0, 0)
    drawing.setLineWidth(0.8)
    drawing.drawPath(path, stroke=1, fill=0)

    drawing.setLineWidth(0.4)
    for hole in layout.holes:
        cx, cy = px(hole.flat_x_mm, 0)
        drawing.circle(cx, cy, hole.diameter_mm / 2 * scale, stroke=1, fill=0)

    drawing.setDash(3, 2)
    for bend_x in (-layout.bend_flat_x_mm, layout.bend_flat_x_mm):
        x1, y1 = px(bend_x, -radius)
        x2, y2 = px(bend_x, radius)
        drawing.line(x1, y1, x2, y2)
    drawing.setDash()
    drawing.setFont("Helvetica", 8)
    drawing.drawString(left, top - box_height + 4, "Flat pattern. Dashed lines are bend centers. Holes are plain diameters.")


def _arc(path, px, center_x: float, radius: float, start_deg: float, sweep_deg: float) -> None:
    steps = 16
    for step in range(1, steps + 1):
        angle = math.radians(start_deg + sweep_deg * step / steps)
        path.lineTo(*px(center_x + radius * math.cos(angle), radius * math.sin(angle)))
