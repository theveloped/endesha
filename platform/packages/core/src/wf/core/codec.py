"""CBOR codec for everything structured on the bus (design §6).

Wire-name mapping (e.g. python ``do_`` <-> wire ``"do"``) lives in the message
classes' ``to_wire``/``from_wire``, not here.
"""

from __future__ import annotations

import cbor2


def encode(obj: dict) -> bytes:
    """Encode a wire dict to CBOR bytes."""
    return cbor2.dumps(obj, canonical=False)


def decode(data) -> dict:
    """Decode CBOR bytes (or a zenoh ZBytes) to a dict."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        data = data.to_bytes()
    return cbor2.loads(data)
