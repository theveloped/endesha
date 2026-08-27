"""Wire round-trips for the control contract messages."""

from __future__ import annotations

import pytest

from wf.contracts.control import keys
from wf.contracts.control.messages import (
    AcquireControl,
    ControlAck,
    ControlOwner,
    ControlOwnerState,
    ReleaseControl,
)

OWNER = ControlOwner(client_id="c1", user="me", granted_at=10, expires_at=40)


@pytest.mark.parametrize(
    "msg",
    [
        AcquireControl(client_id="c1", user="me"),
        ReleaseControl(client_id="c1"),
        ControlAck(ok=True, owner=OWNER, error=None),
        ControlAck(ok=False, owner=None, error="held_by:bob"),
        ControlOwnerState(t=7, owner=OWNER),
        ControlOwnerState(t=8, owner=None),
    ],
)
def test_round_trip(msg):
    assert type(msg).from_wire(msg.to_wire()) == msg


def test_keys_carry_no_resource_id():
    assert keys.cmd_acquire("cell") == "cell/control/cmd/acquire"
    assert keys.cmd_release("cell") == "cell/control/cmd/release"
    assert keys.state_owner("cell") == "cell/control/state/owner"
    assert keys.alive("cell") == "cell/control/alive"
