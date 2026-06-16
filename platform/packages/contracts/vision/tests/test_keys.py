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


def test_invalid_realm_raises():
    with pytest.raises(ValueError):
        keys.image("bogus", "gray")
