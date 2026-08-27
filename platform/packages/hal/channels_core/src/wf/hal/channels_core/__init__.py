"""Generic named-channel device core.

Both ``dio`` (pins) and ``tags`` (PLC variables) are "a table of named
values, some writable, all forceable, published on change + keepalive, writes
gated by the cell lease". :class:`ChannelsCore` implements that once; a
:class:`Schema` supplies the contract-specific parts (keys, channel
definitions, wire messages) and a :class:`ChannelsBackend` moves raw values.
"""

from .backend import ChannelsBackend
from .core import ChannelsCore, Schema, load_resource_params

__all__ = ["ChannelsBackend", "ChannelsCore", "Schema", "load_resource_params"]
