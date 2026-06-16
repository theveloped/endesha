"""One-off generator for the shared calibration-board glTF asset.

Run ONCE; the committed artifact is
``packages/core/src/wf/core/assets/calib_board.glb``. The board is a
0.300 x 0.200 x 0.005 m slab whose top face carries a checkerboard built from
per-square vertex-coloured quads (no texture image, so no Pillow dependency)
so the sim-camera renderer produces a ``cv2.findChessboardCorners``-detectable
target. Geometry/units match ``calib_board.yaml`` (metres) so render and
collision share one asset.

    pixi run python scripts/make_calib_board_glb.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

# Board outer dimensions (metres) — match calib_board.yaml's slab.
_BW, _BH, _BT = 0.300, 0.200, 0.005

# Checkerboard: 7 x 5 squares (inner-corner grid 6 x 4 for findChessboardCorners).
_NX, _NY = 7, 5
_BLACK = (0, 0, 0, 255)
_WHITE = (255, 255, 255, 255)
_GREY = (160, 160, 160, 255)


def _quad(x0, y0, x1, y1, z, color):
    """Two triangles spanning [x0,x1]x[y0,y1] at height z, with per-vertex color."""
    verts = np.array(
        [[x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z]], dtype=np.float64
    )
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
    m = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    m.visual.vertex_colors = np.tile(color, (4, 1))
    return m


def _top_face() -> list[trimesh.Trimesh]:
    """Checkerboard quads tiling the top face just above z=_BT.

    The pattern fills the central region; a one-square white quiet zone borders
    it (the corner detector needs the surrounding border). The quads sit a hair
    (0.5 mm) ABOVE the slab's top face so they always win the depth test — at
    exactly z=_BT they z-fight the grey body and the checkerboard is destroyed.
    """
    z = _BT + 0.0005
    cols, rows = _NX + 2, _NY + 2
    sx, sy = _BW / cols, _BH / rows
    hw, hh = _BW / 2.0, _BH / 2.0
    quads: list[trimesh.Trimesh] = []
    for jj in range(rows):
        for ii in range(cols):
            x0 = -hw + ii * sx
            y0 = -hh + jj * sy
            # Quiet zone (outer ring) is always white.
            inner = 0 < ii <= _NX and 0 < jj <= _NY
            if inner and ((ii - 1) + (jj - 1)) % 2 == 1:
                color = _BLACK
            else:
                color = _WHITE
            quads.append(_quad(x0, y0, x0 + sx, y0 + sy, z, color))
    return quads


def _board_body() -> trimesh.Trimesh:
    """The slab body (grey), centre at z=_BT/2 so the top face sits at z=_BT."""
    body = trimesh.creation.box(extents=(_BW, _BH, _BT))
    body.apply_translation((0.0, 0.0, _BT / 2.0))
    body.visual.vertex_colors = np.tile(_GREY, (len(body.vertices), 1))
    return body


def main() -> None:
    out = (
        Path(__file__).resolve().parent.parent
        / "packages/core/src/wf/core/assets/calib_board.glb"
    )
    scene = trimesh.Scene([_board_body(), *_top_face()])
    out.parent.mkdir(parents=True, exist_ok=True)
    scene.export(out)
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
