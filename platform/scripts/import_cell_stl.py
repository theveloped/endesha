"""One-off importer: CAD cell ``*.stl`` + ``*.txt`` pose pairs -> shared assets.

Five robot-cell meshes were exported from CAD as millimetre ``*.stl`` files
authored in CAD WORLD coordinates, each paired with a ``*.txt`` that lists one
or more component placements (translation in mm + the three rotation basis
vectors). This tool translates every pair into the platform's "share the asset,
not the renderer" form so the Coal collision engine, the pyrender sim camera,
and the three.js web twin all consume the SAME geometry:

- a metre-scale ``packages/core/src/wf/core/assets/<basename>.glb`` (re-origined
  to its component-0 local frame, so the GLB carries no CAD-world offset), and
- one ``config/scene/cell/<basename>[/<i>]`` entry per placement in
  ``deploy/config/store.yaml``, posed in the WORLD frame (CAD world coords,
  metres), and
- ``config/frames/arm/r1/base`` = ``T_R``, the robot base pose in that same
  world (from ``aubo_i10.txt``, which has no STL — it anchors the robot only).

The world frame is the CAD world origin, kept SEPARATE from the robot base so
multiple arms / fixed cameras share one world (design: world != robot base).
``coal``/``pyrender`` take no scale argument, so metre scale is baked into the
GLB; scene poses are ``T_cad_obj`` directly, and collision/render resolve each
object relative to the robot via the frame tree (``arm/r1/base`` -> ``world``).

    pixi run python scripts/import_cell_stl.py            # generate + self-check
    pixi run python scripts/import_cell_stl.py --check    # validate only, no writes
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import trimesh
import yaml

from wf.core.frames import make_transform, transform_to_xyz_quat

# `5775-7230-27.stl` ships with no matching `5775-7230-27.txt`; its pose is in
# `5775-2730-27.txt` (filename digit transposition). That txt is byte-identical
# to the robot base pose, so the pedestal lands directly under the robot.
_TXT_FALLBACK = {"5775-7230-27": "5775-2730-27"}

# The robot base anchor: a pose file with no STL, never emitted as an object.
_ANCHOR = "aubo_i10"

# End-of-arm tools: an STL with no CAD ``*.txt`` (no world pose). It is rigidly
# mounted on the flange via a tool changer, so it is posed in the dynamic flange
# frame at the tool-changer mount transform (identity here: the STL origin sits
# at the mount interface). Consumers recognise ``frame == _FLANGE_FRAME`` and
# attach it to the LIVE flange (collision: flange joint, twin: flange overlay).
_FLANGE_TOOLS = {"1723-4811-76"}
_FLANGE_FRAME = "arm/r1/flange"

_MM_TO_M = 0.001


@dataclass
class Component:
    """One imported STL: its metre-scale, re-origined mesh + scene entries."""

    basename: str
    mesh: trimesh.Trimesh
    scene: list[tuple[str, dict]]  # (scene_key, store value)


def parse_components(txt_path: Path) -> list[tuple[np.ndarray, np.ndarray]]:
    """Parse a CAD pose ``*.txt`` into ``[(R 3x3, t_mm 3), ...]``.

    The file holds one or more ``Component Translations:`` blocks; each carries
    ``Delta X/Y/Z`` (mm) and the three ``*-axis Vector`` rows (printed twice —
    the first is used). ``R = [Xvec | Yvec | Zvec]`` (basis vectors are the
    COLUMNS). Raises ``ValueError`` (named) when no block parses.
    """
    text = txt_path.read_text()
    components: list[tuple[np.ndarray, np.ndarray]] = []
    for raw in text.split("Component Translations:")[1:]:
        delta: dict[str, float] = {}
        axes: dict[str, list[float]] = {}
        for line in raw.splitlines():
            toks = line.split()
            if len(toks) >= 3 and toks[0] == "Delta":
                delta[toks[1]] = float(toks[2])
            elif len(toks) >= 5 and toks[0].endswith("-axis") and toks[1] == "Vector":
                axes[toks[0][0]] = [float(toks[2]), float(toks[3]), float(toks[4])]
        if {"X", "Y", "Z"} <= delta.keys() and {"X", "Y", "Z"} <= axes.keys():
            t = np.array([delta["X"], delta["Y"], delta["Z"]], dtype=np.float64)
            R = np.column_stack([axes["X"], axes["Y"], axes["Z"]])
            components.append((R, t))
    if not components:
        raise ValueError(f"no parseable component blocks in {txt_path.name}")
    return components


def _scene_value(
    basename: str, xyz: list[float], quat: list[float], *, collision: bool = True
) -> dict:
    """The ``config/scene/**`` value mirroring the existing ``table`` shape.

    ``collision=False`` keeps the object in render + twin but excludes it from
    collision preflight (the robot mount coincides with ``base_link``)."""
    meta = {"object": basename, "source": "cad_import"}
    if not collision:
        meta["collision"] = False
    return {
        "frame": "world",
        "geometry": {"type": "mesh", "uri": f"asset://wf/{basename}.glb"},
        "meta": meta,
        "pose": {"xyz": xyz, "quat": quat},
    }


def _tool_scene_value(basename: str) -> dict:
    """``config/scene/tool/**`` value: a mesh posed in the dynamic flange frame.

    Same wire shape as :func:`_scene_value`, but ``frame`` is the flange (not
    ``world``) and ``pose`` is the tool-changer mount transform (identity: the
    STL origin is the mount interface). Collision attaches it to the flange
    joint and the twin renders it at the live flange pose; the sim eye-in-hand
    camera skips a tool mounted on its own flange."""
    return {
        "frame": _FLANGE_FRAME,
        "geometry": {"type": "mesh", "uri": f"asset://wf/{basename}.glb"},
        "meta": {"object": basename, "source": "cad_import"},
        "pose": {"xyz": [0.0, 0.0, 0.0], "quat": [0.0, 0.0, 0.0, 1.0]},
    }


def _flange_tool_component(stl: Path, basename: str) -> Component:
    """A flange-mounted tool: mm -> m scaled, NO re-origin (the STL origin is
    the tool-changer mount interface), one ``tool/{basename}`` scene entry."""
    mesh = trimesh.load(stl, force="mesh")
    mesh.vertices = mesh.vertices * _MM_TO_M
    return Component(basename, mesh, [(f"tool/{basename}", _tool_scene_value(basename))])


def build(src: Path) -> tuple[list[Component], dict]:
    """Translate every ``src/*.stl`` (+ paired txt) into a :class:`Component`.

    Re-origins each mesh into its component-0 local frame and scales to metres,
    and computes one WORLD-frame scene pose per placement (CAD world coords).
    Also returns the robot-base frame value (``aubo_i10.txt`` -> ``T_R``) so the
    robot is anchored into the same world (world != robot base). No file writes.
    """
    R_R, t_R_mm = parse_components(src / f"{_ANCHOR}.txt")[0]
    T_R = make_transform(R_R, t_R_mm * _MM_TO_M)
    base_xyz, base_quat = transform_to_xyz_quat(T_R)
    base_value = {
        "parent": "world",
        "xyz": base_xyz,
        "quat": base_quat,
        "source": "cad_import",
        "meta": {"object": _ANCHOR},
    }

    components: list[Component] = []
    for stl in sorted(src.glob("*.stl")):
        basename = stl.stem
        if basename in _FLANGE_TOOLS:
            components.append(_flange_tool_component(stl, basename))
            continue
        txt = src / f"{_TXT_FALLBACK.get(basename, basename)}.txt"
        placements = parse_components(txt)

        mesh = trimesh.load(stl, force="mesh")
        R0, t0_mm = placements[0]
        # Re-origin into the component-0 local frame, then mm -> m.
        mesh.vertices = ((R0.T @ (mesh.vertices - t0_mm).T).T) * _MM_TO_M

        single = len(placements) == 1
        scene: list[tuple[str, dict]] = []
        for i, (Ri, ti_mm) in enumerate(placements):
            T_i = make_transform(Ri, ti_mm * _MM_TO_M)
            xyz, quat = transform_to_xyz_quat(T_i)
            key = f"cell/{basename}" if single else f"cell/{basename}/{i}"
            # Geometry coincident with the robot base is the robot's MOUNT (it
            # sits under base_link by construction); render it but exclude it
            # from collision so preflight never reports a permanent contact.
            is_mount = bool(np.allclose(T_i, T_R, atol=1e-9))
            scene.append(
                (key, _scene_value(basename, xyz, quat, collision=not is_mount))
            )
        components.append(Component(basename, mesh, scene))
    return components, base_value


def self_check(components: list[Component], base_value: dict) -> None:
    """Assert metre scale (bbox < 12 m) and the world-anchored placement.

    ``cell/5775-7230-27`` is the pedestal at the robot base (``T_cad == T_R``),
    so its WORLD pose must equal the robot-base frame pose — proving the robot
    is anchored into the same world as the cell geometry.
    """
    for comp in components:
        ext = comp.mesh.extents
        assert ext.max() < 12.0, f"{comp.basename} bbox {ext} m not metre-scale"

    pedestal = next(
        (v for c in components for (k, v) in c.scene if k == "cell/5775-7230-27"),
        None,
    )
    assert pedestal is not None, "pedestal cell/5775-7230-27 missing"
    ped_xyz = np.asarray(pedestal["pose"]["xyz"], dtype=np.float64)
    ped_quat = np.asarray(pedestal["pose"]["quat"], dtype=np.float64)
    base_xyz = np.asarray(base_value["xyz"], dtype=np.float64)
    base_quat = np.asarray(base_value["quat"], dtype=np.float64)
    assert np.allclose(ped_xyz, base_xyz, atol=1e-6), f"pedestal xyz {ped_xyz} != base {base_xyz}"
    assert np.allclose(ped_quat, base_quat, atol=1e-6), f"pedestal quat {ped_quat} != base {base_quat}"
    assert pedestal["meta"].get("collision") is False, (
        "the mount pedestal must be excluded from collision"
    )

    for comp in components:
        for key, val in comp.scene:
            if val["frame"] != _FLANGE_FRAME:
                continue
            assert val["pose"]["xyz"] == [0.0, 0.0, 0.0], f"{key} mount xyz not identity"
            assert val["pose"]["quat"] == [0.0, 0.0, 0.0, 1.0], f"{key} mount quat not identity"
            assert comp.mesh.extents.max() < 0.5, f"{key} bbox {comp.mesh.extents} not tool-scale"


def seed_store(store_path: Path, components: list[Component], base_value: dict) -> None:
    """Merge the robot-base frame + ``config/scene/cell/**`` into ``store.yaml``,
    preserving all other keys. The config service loads this verbatim on startup."""
    store = yaml.safe_load(store_path.read_text()) or {}
    store["config/frames/arm/r1/base"] = {"revision": 1, "t": 0, "value": base_value}
    for comp in components:
        for key, value in comp.scene:
            store[f"config/scene/{key}"] = {"revision": 1, "t": 0, "value": value}
    store_path.write_text(yaml.safe_dump(store, sort_keys=True))


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    platform = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, default=root, help="dir holding *.stl/*.txt")
    ap.add_argument(
        "--store",
        type=Path,
        default=platform / "deploy/config/store.yaml",
        help="config store seeded with config/scene/cell/** entries",
    )
    ap.add_argument(
        "--assets",
        type=Path,
        default=platform / "packages/core/src/wf/core/assets",
        help="dir the *.glb assets are written into",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="validate the conversion math only; write no GLBs and no store",
    )
    args = ap.parse_args()

    components, base_value = build(args.src)
    self_check(components, base_value)

    if args.check:
        print(
            f"check ok: {len(components)} components, "
            f"{sum(len(c.scene) for c in components)} scene entries, "
            f"robot base at {base_value['xyz']}"
        )
        return

    args.assets.mkdir(parents=True, exist_ok=True)
    for comp in components:
        glb = args.assets / f"{comp.basename}.glb"
        trimesh.Scene([comp.mesh]).export(glb)
        keys = ", ".join(k for k, _ in comp.scene)
        print(f"wrote {glb.name} ({glb.stat().st_size} bytes) -> {keys}")

    seed_store(args.store, components, base_value)
    print(
        f"seeded {args.store}: config/frames/arm/r1/base + "
        f"{sum(len(c.scene) for c in components)} config/scene/cell/** entries"
    )


if __name__ == "__main__":
    main()
