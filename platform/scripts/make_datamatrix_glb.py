"""One-off generator for the demo DataMatrix-part glTF asset.

Run ONCE; the committed artifact is
``packages/core/src/wf/core/assets/datamatrix_part.glb``. A flat planar board
whose top face carries the DataMatrix encoding ``WF-PART-0042`` built from
per-module vertex-coloured quads (no texture image, so no Pillow dependency) so
the sim-camera pyrender renderer produces a ``zxingcpp``-decodable target under
flat ambient light. Mirrors ``make_calib_board_glb.py``: white quiet-zone
border, modules z-lifted 0.5 mm above the slab so they win the depth test.

    pixi run python scripts/make_datamatrix_glb.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh
import zxingcpp

_PAYLOAD = "WF-PART-0042"

# Physical board footprint (metres). ~0.12 m square reads crisply from the
# ~0.45 m demo poses (modules well above the ~4 px floor at fx=900).
_BOARD_M = 0.12
_QUIET_MODULES = 2  # white quiet-zone ring (modules) around the symbol
_BT = 0.005  # slab thickness
_ZLIFT = 0.0005  # 0.5 mm so module quads beat the slab body in the depth test

_BLACK = (0, 0, 0, 255)
_WHITE = (255, 255, 255, 255)
_GREY = (160, 160, 160, 255)


def _module_matrix() -> np.ndarray:
    """Boolean module matrix of the DataMatrix symbol (True = black module)."""
    barcode = zxingcpp.create_barcode(_PAYLOAD, zxingcpp.BarcodeFormat.DataMatrix)
    img = np.asarray(barcode.to_image(scale=1))  # 1 px per module, 0=black 255=white
    if img.ndim == 3:
        img = img[:, :, 0]
    return img < 128


def _quad(x0, y0, x1, y1, z, color) -> trimesh.Trimesh:
    verts = np.array(
        [[x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z]], dtype=np.float64
    )
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
    m = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    m.visual.vertex_colors = np.tile(color, (4, 1))
    return m


def _top_face() -> list[trimesh.Trimesh]:
    sym = _module_matrix()
    sh, sw = sym.shape
    cols = sw + 2 * _QUIET_MODULES
    rows = sh + 2 * _QUIET_MODULES
    step = _BOARD_M / max(cols, rows)
    hw = (cols * step) / 2.0
    hh = (rows * step) / 2.0
    z = _BT + _ZLIFT
    quads: list[trimesh.Trimesh] = []
    for jj in range(rows):
        for ii in range(cols):
            x0 = -hw + ii * step
            y0 = -hh + jj * step
            si = ii - _QUIET_MODULES
            # Flip rows: image row 0 is the top, +Y is up in the board plane.
            sj = (rows - 1 - jj) - _QUIET_MODULES
            black = 0 <= si < sw and 0 <= sj < sh and bool(sym[sj, si])
            color = _BLACK if black else _WHITE
            quads.append(_quad(x0, y0, x0 + step, y0 + step, z, color))
    return quads


def _board_body() -> trimesh.Trimesh:
    body = trimesh.creation.box(extents=(_BOARD_M, _BOARD_M, _BT))
    body.apply_translation((0.0, 0.0, _BT / 2.0))
    body.visual.vertex_colors = np.tile(_GREY, (len(body.vertices), 1))
    return body


def main() -> None:
    out = (
        Path(__file__).resolve().parent.parent
        / "packages/core/src/wf/core/assets/datamatrix_part.glb"
    )
    scene = trimesh.Scene([_board_body(), *_top_face()])
    out.parent.mkdir(parents=True, exist_ok=True)
    scene.export(out)
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
