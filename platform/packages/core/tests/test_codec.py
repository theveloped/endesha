"""CBOR codec roundtrip tests."""

from wf.core.codec import decode, encode


def test_roundtrip_nested():
    obj = {
        "t": 1718000000000000000,
        "pose": {"frame": "arm/r1/base", "xyz": [0.1, -0.2, 0.3], "quat": [0, 0, 0, 1]},
        "blob": b"\x00\x01\xff",
        "flags": [True, False, None],
        "n": -42,
    }
    assert decode(encode(obj)) == obj


def test_roundtrip_large_ints_and_floats():
    obj = {"ns": 2**62, "neg": -(2**40), "f": 3.141592653589793}
    out = decode(encode(obj))
    assert out["ns"] == obj["ns"]
    assert out["neg"] == obj["neg"]
    assert out["f"] == obj["f"]


def test_decode_accepts_buffer_types():
    data = encode({"a": 1})
    assert decode(bytearray(data)) == {"a": 1}
    assert decode(memoryview(data)) == {"a": 1}
