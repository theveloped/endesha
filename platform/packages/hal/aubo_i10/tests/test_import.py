"""Lazy-import guarantee: the HAL package imports without pyaubo_sdk loaded.

pyaubo_sdk may be installed in this venv; the guarantee under test is that
importing the HAL modules does not import it at module scope.
"""

import sys


def test_hal_imports_without_pyaubo_sdk(monkeypatch):
    for mod in list(sys.modules):
        if mod.startswith("wf.hal.aubo_i10") or mod == "pyaubo_sdk":
            monkeypatch.delitem(sys.modules, mod, raising=False)
    # Make any import of pyaubo_sdk fail loudly.
    monkeypatch.setitem(sys.modules, "pyaubo_sdk", None)

    import wf.hal.aubo_i10.config  # noqa: F401
    import wf.hal.aubo_i10.rtde  # noqa: F401
    import wf.hal.aubo_i10.sdk  # noqa: F401
    import wf.hal.aubo_i10.timesync  # noqa: F401

    session = wf.hal.aubo_i10.sdk.AuboSession("127.0.0.1")
    assert session.rpc is None  # constructed fine without the SDK
