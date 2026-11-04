"""Command line for `make bracket CHIPSET=...`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bracketlab.build import BuildOptions, build_job
from bracketlab.dfm import DfmError
from bracketlab.layout import FitError


def _mm(value: float) -> str:
    return f"{value:.3f}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bracketlab", description="Generate an NH-L9i fastening bar.")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="Write shop files for one chipset")
    build.add_argument("--chipset", required=True)
    build.add_argument("--cooler", default="nh-l9i")
    build.add_argument("--center", type=float)
    build.add_argument("--span", type=float)
    build.add_argument("--span-x", type=float)
    build.add_argument("--span-y", type=float)
    build.add_argument("--orthogonal", type=float)
    build.add_argument("--thickness", type=float)
    build.add_argument("--out", type=Path, default=Path("build"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "build":
        return 2
    options = BuildOptions(
        chipset=args.chipset,
        cooler=args.cooler,
        center=args.center,
        span=args.span,
        span_x=args.span_x,
        span_y=args.span_y,
        orthogonal=args.orthogonal,
        thickness=args.thickness,
        out=args.out,
    )
    try:
        result = build_job(options)
    except FitError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (DfmError, ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    layout = result.layout
    print(f"chipset: {options.chipset}")
    print(f"span: {_mm(layout.span_mm)} mm")
    print(f"center spacing: {_mm(layout.center_spacing_mm)} mm")
    print(f"arm: {_mm(layout.arm_mm)} mm")
    print(f"orthogonal pitch: {_mm(layout.orthogonal_pitch_mm)} mm")
    print(f"ear height: {_mm(layout.ear_height_mm)} mm")
    print(f"order_ready: {'yes' if result.order_ready else 'no'}")
    if result.unverified:
        print("unverified: " + ", ".join(result.unverified))
    for warning in result.warnings:
        print(f"warning: {warning}")
    print(f"wrote {result.directory}/")
    return 0
