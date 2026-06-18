"""vision contract key-space tests."""

from __future__ import annotations

import pytest

from wf.contracts.vision import keys


def test_image_key():
    assert keys.image("sim", "gray") == "sim/vision/gray/image"


def test_alive_key():
    assert keys.alive("sim", "gray") == "sim/vision/gray/alive"


def test_prefix_key():
    assert keys.prefix("sim", "crop") == "sim/vision/crop"


def test_cell_realm_ok():
    # The namespace no longer encodes the backend: any single-segment token is
    # valid (the operating namespace is "cell"); "bogus" is just another token.
    assert keys.image("cell", "gray") == "cell/vision/gray/image"


def test_invalid_realm_raises():
    # Only empty or embedded-"/" tokens (that aren't replay/<id>) are invalid.
    with pytest.raises(ValueError):
        keys.image("a/b", "gray")
