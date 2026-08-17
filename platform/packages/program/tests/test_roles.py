"""Roles view: role attributes + cell helpers, no bus needed."""

from __future__ import annotations

import pytest

from wf.program.errors import ProgramError
from wf.program.machine import Machine, Roles


class _NoBusMachine(Machine):
    def __init__(self):
        # Skip the zenoh-touching parts of Machine; keep the pieces Roles uses.
        self.devices = {"r1": {"id": "r1", "contract": "arm"}, "io0": {"id": "io0", "contract": "dio"}}
        self._proxies = {}
        self.poses = {"home": [0.0] * 6}
        self._pose_resolver = lambda name: self.poses[name]

    def device(self, rid):
        if rid not in self.devices:
            raise ProgramError(f"unknown_device:{rid}")
        return f"proxy:{rid}"


def test_roles_attributes_and_helpers():
    m = _NoBusMachine()
    roles = Roles(m, {"arm": "r1", "io": "io0"})
    assert roles.arm == "proxy:r1" and roles["io"] == "proxy:io0"
    assert roles.bindings == {"arm": "r1", "io": "io0"}
    assert roles.rid("io") == "io0"
    assert roles.pose("home") == [0.0] * 6
    assert roles.device("r1") == "proxy:r1"
    assert roles.ids("dio") == ["io0"] and set(roles.ids()) == {"r1", "io0"}
    assert roles.machine is m
    with pytest.raises(ProgramError, match="unbound_role:cam"):
        _ = roles.cam
    with pytest.raises(AttributeError):
        _ = roles._private


def test_bind_resolves_defaults_and_rejects_ambiguity():
    m = _NoBusMachine()
    assert m.resolve_bindings({"arm": "arm", "io": "dio"}, {}) == {"arm": "r1", "io": "io0"}
    with pytest.raises(ProgramError, match="contract_mismatch"):
        m.resolve_bindings({"arm": "arm"}, {"arm": "io0"})
    m.devices["io1"] = {"id": "io1", "contract": "dio"}
    with pytest.raises(ProgramError, match="ambiguous"):
        m.resolve_bindings({"io": "dio"}, {})
    with pytest.raises(ProgramError, match="no_device_of_contract"):
        m.resolve_bindings({"cam": "camera2d"}, {})
