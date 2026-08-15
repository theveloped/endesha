"""The `control` contract key space (program-layer RFC §2.4).

One lease per cell, so keys carry no resource id::

    {realm}/control/cmd/acquire     queryable {client_id, user} -> ControlAck
    {realm}/control/cmd/release     queryable {client_id}       -> ControlAck
    {realm}/control/state/owner     pub latest-wins + queryable ControlOwnerState
    {realm}/control/alive           liveliness token of the authority
"""

from __future__ import annotations

from wf.core.keys import key, realm_prefix


def prefix(realm: str) -> str:
    return key(realm_prefix(realm), "control")


def cmd_acquire(realm: str) -> str:
    return key(prefix(realm), "cmd", "acquire")


def cmd_release(realm: str) -> str:
    return key(prefix(realm), "cmd", "release")


def state_owner(realm: str) -> str:
    return key(prefix(realm), "state", "owner")


def alive(realm: str) -> str:
    return key(prefix(realm), "alive")
