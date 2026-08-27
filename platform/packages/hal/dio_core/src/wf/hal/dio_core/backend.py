"""The ``DioBackend`` seam: raw pin values in/out (see channels_core)."""

from __future__ import annotations

from wf.hal.channels_core import ChannelsBackend


class DioBackend(ChannelsBackend):
    """A dio provider backend. ``points()`` returns ``[(kind, address), …]`` for
    every physical pin (di/do/ai/ao); ``read()`` raw values by channel name;
    ``write(channel, raw)`` for outputs. See :class:`ChannelsBackend`."""
