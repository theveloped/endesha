"""Tests for the shared ``asset://`` resolver (``wf.core.assets``)."""

from __future__ import annotations

import os

import pytest

from wf.core.assets import AssetError, resolve_asset


def test_non_scheme_uri_passthrough():
    # Coal's existing relative/absolute mesh paths must round-trip verbatim.
    assert resolve_asset("aubo_description/meshes/table.glb") == (
        "aubo_description/meshes/table.glb"
    )
    assert resolve_asset("/abs/path/x.glb") == "/abs/path/x.glb"


def test_wf_root_resolves_to_existing_file():
    path = resolve_asset("asset://wf/calib_board.glb")
    assert os.path.isabs(path)
    assert os.path.exists(path)


def test_unknown_root_raises():
    with pytest.raises(AssetError, match="^unknown_asset_root:"):
        resolve_asset("asset://nope/x.glb")


def test_empty_path_raises():
    with pytest.raises(AssetError, match="^empty_asset_path:"):
        resolve_asset("asset://wf/")


def test_path_escape_raises():
    with pytest.raises(AssetError, match="^asset_path_escape:"):
        resolve_asset("asset://wf/../escape.glb")
