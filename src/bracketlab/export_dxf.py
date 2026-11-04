"""Flat DXF with a closed outline, plain holes, and dashed bend-center lines."""

from __future__ import annotations

from pathlib import Path

import ezdxf

from bracketlab.layout import Layout


def write_dxf(layout: Layout, path: Path) -> None:
    # Freeze header dates, GUIDs, and the ezdxf version stamp so a rebuild matches.
    # The flag has to be set before the document is created. The created-by stamp
    # is written at that moment, and save only refreshes the written-by stamp.
    ezdxf.options.write_fixed_meta_data_for_testing = True
    try:
        _write_dxf(layout, path)
    finally:
        ezdxf.options.write_fixed_meta_data_for_testing = False


def _write_dxf(layout: Layout, path: Path) -> None:
    document = ezdxf.new("R2010", setup=True)
    document.units = ezdxf.units.MM
    if "BEND" not in document.linetypes:
        document.linetypes.add(
            "BEND",
            pattern=[3.5, 2.5, -1.0],
            description="Bend center __ __ __",
        )
    model = document.modelspace()

    half_hole = layout.flat_hole_x_mm
    half_width = layout.web_width_mm / 2
    # Bulge -1 is a clockwise semicircle, so the caps fall outside the web.
    model.add_lwpolyline(
        [
            (-half_hole, half_width, 0),
            (half_hole, half_width, -1),
            (half_hole, -half_width, 0),
            (-half_hole, -half_width, -1),
        ],
        format="xyb",
        close=True,
        dxfattribs={"layer": "0"},
    )
    for hole in layout.holes:
        model.add_circle(
            (hole.flat_x_mm, 0.0),
            hole.diameter_mm / 2,
            dxfattribs={"layer": "0"},
        )
    for bend_x in (-layout.bend_flat_x_mm, layout.bend_flat_x_mm):
        model.add_line(
            (bend_x, -half_width),
            (bend_x, half_width),
            dxfattribs={"layer": "0", "linetype": "BEND"},
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    document.saveas(path)
