"""Load chipset, cooler, and shop presets from the repository."""

from __future__ import annotations

import os
from pathlib import Path

import yaml


def repo_root(start: Path | None = None) -> Path:
    env = os.environ.get("BRACKETLAB_ROOT")
    if env:
        return Path(env)
    cursor = start or Path.cwd()
    for candidate in [cursor, *cursor.parents]:
        if (candidate / "chipsets").is_dir() and (candidate / "coolers").is_dir():
            return candidate
    raise FileNotFoundError(
        "Could not find chipsets/ and coolers/. Run from the repository root."
    )


def _read_yaml(path: Path) -> dict:
    with path.open() as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a mapping.")
    return data


def list_chipsets(root: Path) -> list[str]:
    return sorted(path.stem for path in (root / "chipsets").glob("*.yaml"))


def load_chipset(root: Path, name: str) -> dict:
    path = root / "chipsets" / f"{name}.yaml"
    if not path.is_file():
        known = ", ".join(list_chipsets(root)) or "(none)"
        raise FileNotFoundError(f"Unknown chipset {name!r}. Known chipsets: {known}.")
    data = _read_yaml(path)
    if data.get("name") != name:
        raise ValueError(f"{path} name is {data.get('name')!r}; the file stem is {name!r}.")
    holes = data.get("holes_mm")
    if not isinstance(holes, list) or len(holes) != 2:
        raise ValueError(f"{path} needs holes_mm as two numbers.")
    data["holes_mm"] = (float(holes[0]), float(holes[1]))
    return data


def load_cooler(root: Path, name: str) -> dict:
    path = root / "coolers" / f"{name}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Unknown cooler {name!r} ({path}).")
    data = _read_yaml(path)
    if data.get("name") != name:
        raise ValueError(f"{path} name is {data.get('name')!r}; the file stem is {name!r}.")
    return data


def load_material(root: Path, name: str = "sendcutsend-5052-0125") -> dict:
    path = root / "materials" / f"{name}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Unknown material preset {name!r} ({path}).")
    return _read_yaml(path)
