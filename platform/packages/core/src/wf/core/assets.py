"""Shared `asset://` resolver for scene meshes (design §5.10).

ONE asset, two consumers: the sim-camera pyrender renderer and the Coal
collision engine both resolve a mesh ``uri`` through :func:`resolve_asset`
("share the asset, not the renderer"). An ``asset://<root>/<relpath>`` uri
names a registered root directory; the ``wf`` root holds shared scene meshes
authored once and shipped in the ``wf-core`` wheel (``src/wf/core/assets/``).

A bare path (no ``asset://`` scheme) is returned VERBATIM, preserving coal's
existing relative/absolute mesh-path convention.
"""

from __future__ import annotations

from pathlib import Path

_ASSET_SCHEME = "asset://"
# Shared scene meshes authored once and loaded by pyrender (render) AND coal
# (collision). Ships in the wf-core wheel.
_WF_ROOT = Path(__file__).parent / "assets"
_ROOTS: dict[str, Path] = {"wf": _WF_ROOT}


class AssetError(ValueError):
    """Raised when an ``asset://`` uri names an unknown root or escapes it.

    A ``ValueError`` subclass so coal's ``except Exception`` mesh-load guard
    skips a bad asset without blocking acceptance.
    """


def resolve_asset(uri: str) -> str:
    """Resolve an ``asset://<root>/<relpath>`` uri to an absolute filesystem path.

    A uri WITHOUT the ``asset://`` scheme is returned unchanged (back-compat
    with coal's verbatim relative/absolute mesh paths). Raises :class:`AssetError`
    on an unknown root, an empty relative path, or a path that escapes its root.
    """
    if not uri.startswith(_ASSET_SCHEME):
        return uri
    rest = uri[len(_ASSET_SCHEME):]
    root_name, _, rel = rest.partition("/")
    root = _ROOTS.get(root_name)
    if root is None:
        raise AssetError(f"unknown_asset_root:{root_name!r} in {uri!r}")
    if not rel:
        raise AssetError(f"empty_asset_path:{uri!r}")
    root_abs = root.resolve()
    resolved = (root / rel).resolve()
    if root_abs != resolved and root_abs not in resolved.parents:
        raise AssetError(f"asset_path_escape:{uri!r}")
    return str(resolved)
